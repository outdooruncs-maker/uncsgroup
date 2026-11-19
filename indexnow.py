#!/usr/bin/env python3
"""Tell search engines which pages changed, using IndexNow.

Run by .github/workflows/indexnow.yml after every push to main. It compares
the sitemap of the commit that was just pushed with the sitemap of the commit
before it, waits until Cloudflare has the new pages live, then sends the new,
changed and removed addresses to IndexNow in one request. Bing, Yandex, Naver,
Seznam and the other IndexNow engines share what is sent. Google does not use
IndexNow; it keeps reading sitemap.xml.

  python3 indexnow.py --before <sha>     pages that changed since <sha>
  python3 indexnow.py --all              every page in the sitemap
  python3 indexnow.py --all --dry-run    list them, send nothing

Settings are in indexnow.json: "host", "key", and "sitemap" (the path of a
committed sitemap.xml, or null when the site is built with build.py). The key
is not a secret: it is published at https://<host>/<key>.txt so the engines
can check the request came from the site.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://api.indexnow.org/indexnow"
UA = "UncsGroup-IndexNow/1.0 (+https://www.uncsgroup.com/)"
ROOT = Path(__file__).resolve().parent


def parse_sitemap(xml):
    """{address: lastmod or ""} for every <url> in a sitemap."""
    out = {}
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>\s*(.*?)\s*</loc>", block, re.S)
        if not loc:
            continue
        mod = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", block, re.S)
        url = loc.group(1).replace("&amp;", "&")
        out[url] = mod.group(1) if mod else ""
    return out


def tree_sitemap(root, cfg):
    """The sitemap a checkout produces: read it if committed, else build the site."""
    if cfg.get("sitemap"):
        return parse_sitemap((root / cfg["sitemap"]).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, "build.py", "--out", tmp], cwd=root, check=True,
                       stdout=subprocess.DEVNULL)
        return parse_sitemap((Path(tmp) / "sitemap.xml").read_text(encoding="utf-8"))


def before_sitemap(sha):
    """The sitemap at an earlier commit, or None if that commit can't be read or built."""
    if not sha or set(sha) == {"0"}:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "before"
        try:
            subprocess.run(["git", "fetch", "-q", "--depth=1", "origin", sha], cwd=ROOT, check=False)
            subprocess.run(["git", "worktree", "add", "-q", "--detach", str(tree), sha], cwd=ROOT, check=True)
        except subprocess.CalledProcessError:
            return None
        try:
            old_cfg = tree / "indexnow.json"
            if not old_cfg.exists():
                return None          # IndexNow was not set up yet at that commit: send everything
            return tree_sitemap(tree, json.loads(old_cfg.read_text()))
        except (subprocess.CalledProcessError, OSError, ValueError):
            return None
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=ROOT, check=False)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def live_state(base, key):
    """(sitemap of the live site, whether the key file is live). Raises if the site can't be read."""
    stamp = int(time.time())
    key_ok = fetch(f"{base}/{key}.txt?t={stamp}").strip() == key
    return parse_sitemap(fetch(f"{base}/sitemap.xml?t={stamp}")), key_ok


def wait_until_live(base, key, new, changed, removed, wait):
    """Wait for the deploy. Returns the addresses confirmed live (changed) and gone (removed)."""
    deadline, blocked = time.time() + wait, 0
    while True:
        try:
            live, key_ok = live_state(base, key)
            blocked = 0
            up = [u for u in changed if live.get(u, None) == new[u]]
            gone = [u for u in removed if u not in live]
            if key_ok and len(up) == len(changed) and len(gone) == len(removed):
                return up, gone
            print(f"  waiting for the deploy: key file {'live' if key_ok else 'not live yet'}, "
                  f"{len(up)}/{len(changed)} changed pages live, {len(gone)}/{len(removed)} removed pages gone")
        except (urllib.error.URLError, OSError) as e:
            blocked += 1
            live, key_ok, up, gone = {}, False, [], []
            print(f"  could not read the live site ({e})")
        if time.time() >= deadline:
            if blocked >= 3:
                # The site refuses this runner (a firewall rule, most likely), so the deploy
                # can't be confirmed. The wait itself is longer than a deploy takes: send.
                print("  the live site can't be read from here; sending without confirmation")
                return list(changed), list(removed)
            if not key_ok:
                sys.exit(f"The key file {base}/{key}.txt is not live, so IndexNow would reject the request.")
            return up, gone
        time.sleep(20)


def submit(host, key, urls):
    for i in range(0, len(urls), 10000):
        body = json.dumps({"host": host, "key": key, "keyLocation": f"https://{host}/{key}.txt",
                           "urlList": urls[i:i + 10000]}).encode()
        req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
            "Content-Type": "application/json; charset=utf-8", "User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            sys.exit(f"IndexNow refused the request: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:300]}")
        print(f"  sent {len(urls[i:i + 10000])} addresses: HTTP {code}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--before", default="", help="commit to compare with (the push's previous commit)")
    ap.add_argument("--all", action="store_true", help="send every address in the sitemap")
    ap.add_argument("--dry-run", action="store_true", help="list the addresses, send nothing")
    ap.add_argument("--wait", type=int, default=900, help="seconds to wait for the deploy (default 900)")
    a = ap.parse_args()

    cfg = json.loads((ROOT / "indexnow.json").read_text())
    host, key = cfg["host"], cfg["key"]
    base = f"https://{host}"
    new = tree_sitemap(ROOT, cfg)
    old = None if a.all else before_sitemap(a.before)
    if old is None:
        changed, removed = sorted(new), []
        print(f"{host}: sending every page ({len(changed)})")
    else:
        changed = sorted(u for u in new if u not in old or new[u] != old[u])
        removed = sorted(u for u in old if u not in new)
        if cfg.get("always"):
            changed = sorted(set(changed) | set(cfg["always"]))
        print(f"{host}: {len(changed)} new or changed, {len(removed)} removed")
    if not changed and not removed:
        print("Nothing to send.")
        return
    if a.dry_run:
        print("\n".join(changed + [f"{u} (removed)" for u in removed]))
        return
    up, gone = wait_until_live(base, key, new, changed, removed, a.wait)
    if len(up) < len(changed) or len(gone) < len(removed):
        print(f"  the deploy did not finish in time; sending the {len(up) + len(gone)} confirmed addresses only")
    if not up and not gone:
        sys.exit("No changed page was live when the wait ran out.")
    submit(host, key, up + gone)


if __name__ == "__main__":
    main()
