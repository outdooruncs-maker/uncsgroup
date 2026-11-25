"""Instagram posts for @uncs_group, plus the link-in-bio page at uncsgroup.com/ig.

Each day:
  1. Pick one story per paper from its latest edition JSON (content/editions/).
  2. Edit DATE and POSTS below: the story id, three stats and the caption.
  3. Run:  python make_posts.py
     (needs Pillow and resvg-py:  pip install pillow resvg-py)

It writes, inside this repo:
  public/ig/<date>-<paper>.jpg    1080x1350 post images (the same files the page shows)
  public/ig/posts.json            every post so far, newest first (the page is built from it)
  public/ig/index.html            the link-in-bio page
  captions/<date>.md              the captions, ready to paste into Instagram

The six paper repos must sit next to this one (../outdoor-unc, ../fununc, ...).
Only stories with a photo are allowed: a story whose only picture is a creator's
video (YouTube etc.) is refused, and the photo credit is always printed on the image.
Running it again for the same date replaces that day's posts.
"""
import html
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
import resvg_py

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent
FONTS = HERE / "tools" / "fonts"
OUT = HERE / "public" / "ig"
CAPTIONS = HERE / "captions"

W, H = 1080, 1350
PHOTO_H = 600
PAD = 64

# --------------------------------------------------------------------- papers
# Colours match the paper cards on www.uncsgroup.com (public/index.html).
PAPERS = {
    "outdoor": {"name": "Outdoor Unc", "repo": "outdoor-unc", "url": "https://www.outdoorunc.com",
                "logo": "uncsgroup/public/assets/outdoorunc-logo.svg",
                "card": "#fbfaf6", "edge": "#e6e2d8", "accent": "#d24a0b", "ink": "#17150f", "meta": "#5e584c"},
    "fun": {"name": "Fun Unc", "repo": "fununc", "url": "https://www.fununc.com",
            "logo": "fununc/public/assets/brand/logo-inline.svg",
            "card": "#f9fcfb", "edge": "#d6e6e3", "accent": "#0f766e", "ink": "#1f1a1c", "meta": "#5a5052"},
    "sports": {"name": "Sports Unc", "repo": "sportsunc", "url": "https://www.sportsunc.com",
               "logo": "uncsgroup/public/assets/sportsunc-logo.svg",
               "card": "#fdfcfb", "edge": "#ead9d6", "accent": "#b3261e", "ink": "#16181b", "meta": "#55504d"},
    "finance": {"name": "Finance Unc", "repo": "financeunc", "url": "https://www.financeunc.com",
                "logo": "uncsgroup/public/assets/financeunc-logo.svg",
                "card": "#fdfdfb", "edge": "#dfe3ea", "accent": "#1d4e89", "ink": "#16181b", "meta": "#4f5560"},
    "news": {"name": "News Unc", "repo": "newsunc", "url": "https://www.newsunc.com",
             "logo": "uncsgroup/public/assets/newsunc-logo.svg",
             "card": "#fbf6f4", "edge": "#e7d8d3", "accent": "#7a1f3d", "ink": "#2a1a20", "meta": "#62525a"},
    "game": {"name": "Game Unc", "repo": "gameunc", "url": "https://www.gameunc.com",
             "logo": "gameunc/public/assets/brand/logo-inline.svg",
             "card": "#fbfafd", "edge": "#e2ddee", "accent": "#5b3fd1", "ink": "#1f1a1c", "meta": "#5a5052"},
}

# ---------------------------------------------------------------------- today
DATE = "2026-11-25"

# One entry per paper, in the order you'll post them (the page shows the last one first).
# "story" is the id in that paper's edition file.
# Optional: "kicker" / "headline" to override the story's own, "focus" (x, y from
# 0 to 1) to choose which part of the photo survives the crop, "edition" to pick a
# file other than content/editions/<DATE>-<paper>.json or <DATE>.json.
POSTS = [
    {
        "paper": "outdoor",
        "story": "s-shenandoah-wildfire-closes-skyline-drive-appalachian-trail-nov-24",
        "kicker": "Wildfire",
        "stats": [
            ("25 mi", "Of Skyline Drive closed, mile 79.5 to Rockfish Gap"),
            ("4.2 mi", "Of the Appalachian Trail shut, Sawmill Run to Beagle Gap"),
            ("Nov. 21", "Parkwide fire ban in force since, for very dry conditions"),
        ],
        "caption": (
            "A wildfire has closed the south end of Skyline Drive in Shenandoah National Park, from the "
            "Loft Mountain gate to Rockfish Gap, plus about four miles of the Appalachian Trail. "
            "No reopening date yet.\n\n"
            "The rest of the drive is open; heading south, leave the park at Swift Run Gap (U.S. 33). "
            "A parkwide fire ban is in force, and you can get closure alerts by texting SHENALERTS to 888777.\n\n"
            "Full story from Outdoor Unc: link in bio.\n\n"
            "#shenandoah #skylinedrive #appalachiantrail #wildfire #outdoorunc"
        ),
    },
    {
        "paper": "fun",
        "story": "s-macys-parade-100th-balloons-wind-decision-thursday",
        "kicker": "Macy's Parade",
        "focus": (0.5, 0.4),
        "stats": [
            ("100", "Inflatables, a record, for the parade's 100th"),
            ("34 mph", "Gusts above this keep the big balloons low or grounded"),
            ("8:30 a.m.", "Thursday start, Eastern; the wind call comes that morning"),
        ],
        "caption": (
            "The Macy's Thanksgiving Day Parade turns 100 tomorrow with a record 100 inflatables, "
            "including a new Bluey and Sorcerer's Apprentice Mickey. The catch: forecast gusts are right "
            "around the 34 mph line that keeps the big balloons low or on the ground.\n\n"
            "Macy's makes the call Thursday morning. In New York today? Balloon inflation is free, 1 to 6 p.m., "
            "entry at West 72nd and Columbus.\n\n"
            "Full story from Fun Unc: link in bio.\n\n"
            "#macysparade #thanksgiving #nyc #macysthanksgivingdayparade #fununc"
        ),
    },
    {
        "paper": "sports",
        "story": "s-steelers-bench-aaron-rodgers-mason-rudolph-broncos",
        "kicker": "NFL",
        "stats": [
            ("43", "Rodgers' age next week, in his 22nd and final season"),
            ("86.6", "His passer rating this year, the lowest of his career"),
            ("9–9–1", "Mason Rudolph's record as a starter"),
        ],
        "caption": (
            "The Steelers have benched Aaron Rodgers. Mason Rudolph starts Friday against Denver, and "
            "Rodgers, who has said this is his last season, will be inactive.\n\n"
            "Pittsburgh (6–4) has lost two straight, and Rodgers was sacked five times Sunday. "
            "The team hasn't said how long Rudolph will start. Denver will be without J.K. Dobbins, "
            "suspended one game.\n\n"
            "Full story from Sports Unc: link in bio.\n\n"
            "#steelers #aaronrodgers #NFL #broncos #sportsunc"
        ),
    },
    {
        "paper": "news",
        "story": "s-thanksgiving-coastal-storm-east-coast-wpc",
        "kicker": "Weather",
        "stats": [
            ("50+ mph", "Gusts forecast along the coast; outages possible"),
            ("1–4 in", "Rain in the Carolinas and the Mid-Atlantic"),
            ("GA to NE", "Coastal flooding risk, Georgia up to the Northeast"),
        ],
        "caption": (
            "A strong coastal storm is set to run up the East Coast through Thanksgiving Day. Forecasters "
            "warn of coastal flooding from Georgia to the Northeast, gusts over 50 mph, 1 to 4 inches of "
            "rain and possible power outages, with snow on the storm's western side.\n\n"
            "Traveling or near the coast? Plan for delays and outages and follow local officials.\n\n"
            "Full story from News Unc: link in bio.\n\n"
            "#thanksgiving #weather #eastcoast #storm #newsunc"
        ),
    },
    {
        "paper": "game",
        "story": "s-console-price-cuts-2028-sp-global-dram",
        "kicker": "Consoles",
        "stats": [
            ("2028", "Earliest console price cuts, per S&P Global"),
            ("184K", "DRAM wafers of capacity added by the end of this year"),
            ("819K", "Added by the end of 2028, as AI buys up memory"),
        ],
        "caption": (
            "Waiting for a console price cut? Don't hold your breath. An S&P Global analyst says not before "
            "2028, because AI data centers are buying up the memory chips consoles need.\n\n"
            "Our read: today's prices are probably as good as the next year gets, so if a Black Friday bundle "
            "has been tempting you, that's worth knowing. It's one forecast, not a promise from Sony, "
            "Microsoft or Nintendo.\n\n"
            "Full story from Game Unc: link in bio.\n\n"
            "#PS5 #Xbox #NintendoSwitch2 #blackfriday #gameunc"
        ),
    },
    {
        "paper": "finance",
        "story": "s-fhfa-approves-fico-10t-fannie-freddie",
        "kicker": "Credit scores",
        "stats": [
            ("10T", "The newer FICO model Fannie and Freddie will accept"),
            ("Sept. 9", "When lenders could start using VantageScore 4.0"),
            ("3", "Credit bureaus lenders must pull now; MBA wants that to end"),
        ],
        "caption": (
            "Fannie Mae and Freddie Mac will accept FICO 10T, a newer credit score, on the mortgages they buy, "
            "their regulator said Tuesday. No dates yet; it follows the rollout used for VantageScore 4.0.\n\n"
            "For borrowers, nothing changes yet. Lenders pick which approved score to use, and your score can "
            "differ by model. Check your reports free at AnnualCreditReport.com.\n\n"
            "Full story from Finance Unc: link in bio.\n\n"
            "#creditscore #mortgage #FICO #homebuying #financeunc"
        ),
    },
]


# ------------------------------------------------------------------- helpers
def slugify(text, maxlen=72):
    """Same as the papers' build.py, so the links match the story pages."""
    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(text) > maxlen:
        cut = text[:maxlen].rsplit("-", 1)[0]
        text = cut or text[:maxlen]
    return text or "untitled"


def font(name, size, weight=None):
    f = ImageFont.truetype(str(FONTS / name), size)
    if weight is not None:
        f.set_variation_by_axes([weight, min(60, max(8, size * 0.75))])
    return f


def barlow(size, weight="ExtraBold"):
    return font(f"BarlowCondensed-{weight}.ttf", size)


def serif(size, weight=400):
    return font("SourceSerif4-Variable.ttf", size, weight)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def wrap(text, f, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if f.getlength(trial) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def find_edition(paper):
    p = PAPERS[paper]
    if p.get("_edition"):
        return p["_edition"]
    d = WORKSPACE / p["repo"] / "content" / "editions"
    for name in (f"{DATE}-{paper}.json", f"{DATE}.json"):
        if (d / name).exists():
            return d / name
    sys.exit(f"{paper}: no edition for {DATE} in {d}")


def load_story(post):
    paper = post["paper"]
    path = WORKSPACE / PAPERS[paper]["repo"] / "content" / "editions" / post["edition"] if post.get("edition") else find_edition(paper)
    stories = json.loads(path.read_text(encoding="utf-8"))["stories"]
    seen, found = set(), None
    for s in stories:  # rebuild slugs in edition order, as build.py does
        section = slugify(s.get("kicker") or "")
        base = slugify(s.get("headline", s.get("id", "")))
        slug, n = base, 2
        while (section, slug) in seen:
            slug, n = f"{base}-{n}", n + 1
        seen.add((section, slug))
        if s.get("id") == post["story"]:
            found = dict(s, _url=f"{PAPERS[paper]['url']}/{section}/{slug}/")
    if not found:
        sys.exit(f"{paper}: story {post['story']} not in {path.name}")
    img = found.get("image") or {}
    src = str(img.get("src", ""))
    if not src or found.get("creator") or re.search(r"youtu|ytimg|tiktok|instagram|vimeo", src, re.I):
        sys.exit(f"{paper}: {post['story']} has no usable photo (creator video stills are not allowed)")
    if not img.get("credit"):
        sys.exit(f"{paper}: {post['story']} photo has no credit")
    photo = WORKSPACE / PAPERS[paper]["repo"] / "assets" / src
    if not photo.exists():
        photo = WORKSPACE / PAPERS[paper]["repo"] / "public" / "assets" / src
    if not photo.exists():
        sys.exit(f"{paper}: photo file not found: {src}")
    found["_photo"] = photo
    return found


def render_logo(paper, height):
    p = PAPERS[paper]
    svg = (WORKSPACE / p["logo"]).read_text(encoding="utf-8")
    colours = {"ink": p["ink"], "meta": p["meta"], "bg": p["card"], "brand": p["accent"], "closed": p["accent"]}
    svg = re.sub(r"var\(--([a-z0-9-]+)(?:\s*,\s*([^)]+))?\)",
                 lambda m: colours.get(m.group(1)) or (m.group(2) or "#000").strip(), svg)
    if "xmlns=" not in svg[:400]:
        svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    png = resvg_py.svg_to_bytes(svg_string=svg, height=height * 2, font_dirs=[str(FONTS)])
    im = Image.open(io.BytesIO(bytes(png))).convert("RGBA")
    im = im.crop(im.getbbox())  # trim the logo's own margins so every paper lines up
    return im.resize((round(im.width * height / im.height), height), Image.LANCZOS)


# -------------------------------------------------------------------- render
def render(post, story):
    p = PAPERS[post["paper"]]
    ink, meta, accent = hex_rgb(p["ink"]), hex_rgb(p["meta"]), hex_rgb(p["accent"])
    canvas = Image.new("RGB", (W, H), hex_rgb(p["card"]))
    draw = ImageDraw.Draw(canvas)

    # photo, cropped to fill the top band
    photo = ImageOps.exif_transpose(Image.open(story["_photo"])).convert("RGB")
    photo = ImageOps.fit(photo, (W, PHOTO_H), Image.LANCZOS, centering=post.get("focus", (0.5, 0.5)))
    canvas.paste(photo, (0, 0))
    draw.rectangle([0, PHOTO_H, W, PHOTO_H + 10], fill=accent)

    # photo credit, on the photo
    credit = story["image"]["credit"]
    cf = serif(19, 500)
    while cf.getlength(credit) > W - 80 and cf.size > 13:
        cf = serif(cf.size - 1, 500)
    tw = cf.getlength(credit)
    box = [W - 24 - tw - 28, PHOTO_H - 24 - 38, W - 24, PHOTO_H - 24]
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle(box, radius=8, fill=(0, 0, 0, 150))
    canvas.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(canvas)
    draw.text((box[0] + 14, (box[1] + box[3]) / 2), credit, font=cf, fill=(255, 255, 255), anchor="lm")

    # footer first, so the text above knows how much room it has
    logo_h = 72
    logo = render_logo(post["paper"], logo_h)
    foot_top = H - 58 - logo_h
    draw.line([PAD, foot_top - 30, W - PAD, foot_top - 30], fill=hex_rgb(p["edge"]), width=2)
    canvas.paste(logo, (PAD, foot_top), logo)
    ff = barlow(36, "Bold")
    cta = "Full story: link in bio"
    draw.text((W - PAD, foot_top + logo_h / 2), cta, font=ff, fill=ink, anchor="rm")
    draw.line([W - PAD - ff.getlength(cta), foot_top + logo_h / 2 + 24, W - PAD, foot_top + logo_h / 2 + 24],
              fill=accent, width=4)

    # stats: three columns above the footer
    col_gap = 36
    col_w = (W - 2 * PAD - 2 * col_gap) / 3
    lf = serif(23, 450)
    label_lines = [wrap(lab, lf, col_w) for _, lab in post["stats"]]
    if max(len(x) for x in label_lines) > 3:
        lf = serif(21, 450)
        label_lines = [wrap(lab, lf, col_w) for _, lab in post["stats"]]
    num_size = 84
    while any(barlow(num_size).getlength(v) > col_w for v, _ in post["stats"]):
        num_size -= 2
    nf = barlow(num_size)
    label_lh = round(lf.size * 1.3)
    stats_h = num_size + 14 + label_lh * max(len(x) for x in label_lines)

    # kicker and headline: fit the headline in what's left, then centre the
    # kicker + headline + stats block between the photo and the footer
    area_top, area_bottom = PHOTO_H + 10, foot_top - 30
    kick_h, gap = 22 + 24, 44  # kicker cap height + space under it; headline-to-stats gap
    room = area_bottom - area_top - 2 * 40 - kick_h - gap - stats_h
    head = post.get("headline") or story["headline"]
    for size in range(84, 47, -2):
        hf = barlow(size)
        lines = wrap(head, hf, W - 2 * PAD)
        lh = round(size * 1.02)
        if len(lines) <= 4 and lh * len(lines) <= room:
            break
    else:
        sys.exit(f"{post['paper']}: headline does not fit; shorten it with \"headline\"")
    head_h = lh * len(lines)
    spare = room - head_h
    ky = area_top + 40 + 24 + spare // 2  # kicker baseline
    hy = ky + 22
    stats_top = hy + head_h + gap

    kicker = (post.get("kicker") or story.get("eyebrow") or story.get("kicker") or "").upper()
    kf = barlow(34, "Bold")
    x = PAD
    for ch in kicker:  # letter-spaced
        draw.text((x, ky), ch, font=kf, fill=accent, anchor="ls")
        x += kf.getlength(ch) + 2.5
    for j, line in enumerate(lines):
        draw.text((PAD, hy + j * lh), line, font=hf, fill=ink, anchor="la")

    for i, ((value, _), lines_) in enumerate(zip(post["stats"], label_lines)):
        x = PAD + i * (col_w + col_gap)
        if i:
            draw.line([x - col_gap / 2, stats_top + 6, x - col_gap / 2, stats_top + stats_h], fill=hex_rgb(p["edge"]), width=2)
        draw.text((x, stats_top), value, font=nf, fill=accent, anchor="la")
        for j, line in enumerate(lines_):
            draw.text((x, stats_top + num_size + 14 + j * label_lh), line, font=lf, fill=meta, anchor="la")
    return canvas


# ---------------------------------------------------------------------- page
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','GTM-M87KMXHP');</script>
<!-- End Google Tag Manager -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-JT9N4QN4FG"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-JT9N4QN4FG');</script>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Uncs Group on Instagram: the stories we've posted</title>
<meta name="description" content="Every story Uncs Group has posted on Instagram, newest first. Tap a post to read the full story on News Unc, Outdoor Unc, Finance Unc, Sports Unc, Game Unc or Fun Unc.">
<link rel="canonical" href="https://www.uncsgroup.com/ig/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Uncs Group">
<meta property="og:title" content="Uncs Group on Instagram">
<meta property="og:url" content="https://www.uncsgroup.com/ig/">
<meta property="og:image" content="https://www.uncsgroup.com/assets/og.png">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/icon-180.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap" rel="stylesheet">
<style>
:root{{--page:#fafaf8;--ink:#16181b;--meta:#5b6068;--rule:#d9dbde;
  --display:"Barlow Condensed","Arial Narrow",Arial,sans-serif;--serif:"Source Serif 4",Georgia,serif}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--page);color:var(--ink)}}
body{{font-family:var(--serif);font-size:17px;line-height:1.5}}
a{{color:inherit}}
.wrap{{max-width:1120px;margin:0 auto;padding:0 clamp(16px,4vw,40px)}}
.top{{padding:28px 0 20px;border-bottom:1px solid var(--rule);display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
.top img{{width:min(260px,62vw);height:auto;display:block}}
.top p{{margin:0;color:var(--meta);font-size:15px;flex:1 1 220px}}
h2{{font-family:var(--display);font-weight:700;font-size:22px;letter-spacing:.04em;text-transform:uppercase;
  color:var(--meta);margin:30px 0 14px}}
.grid{{list-style:none;margin:0;padding:0;display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr))}}
.post a{{display:block;text-decoration:none;border-radius:8px;overflow:hidden;border:1px solid var(--rule);
  border-top:5px solid var(--accent);background:var(--page)}}
.post a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}
.post img{{display:block;width:100%;height:auto;aspect-ratio:4/5}}
.post .go{{display:flex;justify-content:space-between;gap:12px;padding:12px 14px;font-family:var(--display);
  font-weight:700;font-size:19px;letter-spacing:.02em}}
.post .go span:last-child{{color:var(--accent);white-space:nowrap}}
.post a:hover .go span:first-child{{text-decoration:underline;text-decoration-color:var(--accent);text-decoration-thickness:3px}}
.foot{{border-top:1px solid var(--rule);margin-top:40px;padding:20px 0 32px;color:var(--meta);font-size:14px}}
</style>
</head>
<body>
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-M87KMXHP" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<div class="wrap">
<header class="top">
  <a href="/"><img src="/assets/uncsgroup-logo.svg" alt="Uncs Group" width="493" height="118"></a>
  <p>The stories from our Instagram, newest first. Tap one to read it.</p>
</header>
<main>
{days}
</main>
<footer class="foot">Photo credits are on each image. <a href="/">All six Uncs Group papers</a>.</footer>
</div>
</body>
</html>
"""


def nice_date(d):
    from datetime import date
    y, m, dd = map(int, d.split("-"))
    dt = date(y, m, dd)
    return f"{dt.strftime('%A, %B')} {dd}, {y}"


def build_page(posts):
    days, by_day = [], {}
    for p in posts:
        by_day.setdefault(p["date"], []).append(p)
    first = True
    for d in sorted(by_day, reverse=True):
        items = []
        for p in by_day[d]:
            loading = "eager" if first else "lazy"
            first = False
            items.append(
                f'<li class="post" style="--accent:{p["accent"]}"><a href="{html.escape(p["url"])}">'
                f'<img src="/ig/{html.escape(p["image"])}" alt="{html.escape(p["alt"])}" width="1080" height="1350" loading="{loading}">'
                f'<span class="go"><span>{html.escape(p["paper_name"])}</span><span>Read the story</span></span></a></li>')
        days.append(f'<section><h2>{nice_date(d)}</h2>\n<ul class="grid">\n' + "\n".join(items) + "\n</ul></section>")
    return PAGE.format(days="\n".join(days))


# ---------------------------------------------------------------------- main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CAPTIONS.mkdir(exist_ok=True)
    manifest = OUT / "posts.json"
    old = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []
    old = [p for p in old if p["date"] != DATE]

    new, md = [], [f"# Instagram captions, {nice_date(DATE)}\n"]
    for i, post in enumerate(POSTS):
        assert len(post["stats"]) == 3, f"{post['paper']}: needs exactly three stats"
        story = load_story(post)
        img = render(post, story)
        name = f"{DATE}-{post['paper']}.jpg"
        img.save(OUT / name, "JPEG", quality=88, optimize=True, progressive=True)
        p = PAPERS[post["paper"]]
        head = post.get("headline") or story["headline"]
        new.append({"date": DATE, "order": i, "paper": post["paper"], "paper_name": p["name"],
                    "accent": p["accent"], "story": post["story"], "headline": head,
                    "url": story["_url"], "image": name,
                    "alt": f"{p['name']}: {head}. Photo: {story['image'].get('alt', '')}".strip(),
                    "credit": story["image"]["credit"]})
        md.append(f"## {i + 1}. {p['name']}: {head}\n\nImage: `public/ig/{name}`  \nStory: {story['_url']}\n\n"
                  f"```\n{full_caption(post, story)}\n```\n")
        print(f"  {name}  ->  {story['_url']}")

    # POSTS is the order you post them in, so the last one is the newest: show it first
    posts = sorted(new + old, key=lambda p: (p["date"], p["order"]), reverse=True)
    manifest.write_text(json.dumps(posts, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "index.html").write_text(build_page(posts), encoding="utf-8")
    (CAPTIONS / f"{DATE}.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  public/ig/index.html ({len(posts)} posts), captions/{DATE}.md")


def full_caption(post, story):
    return f"{post['caption']}\n\n{story['image']['credit']}"


# ------------------------------------------------------------------ publish
# Posts the day's images to Instagram through Meta's official Graph API.
# Needs, in the environment (never in this file):
#   IG_ACCESS_TOKEN   a token with instagram_business_content_publish (Instagram
#                     login, starts "IG...") or instagram_content_publish (Facebook login)
#   IG_USER_ID        optional; looked up from the token if missing
# Images are fetched by Instagram from www.uncsgroup.com/ig/, so commit and push first.
import os
import time
import urllib.error
import urllib.parse
import urllib.request

SITE_IG = "https://www.uncsgroup.com/ig/"
PUBLISHED = HERE / "captions" / "published.json"  # what has gone out, so nothing posts twice


def graph(method, path, token, **params):
    host = "graph.instagram.com" if token.startswith("IG") else "graph.facebook.com"
    version = os.environ.get("IG_GRAPH_VERSION", "v23.0")
    params["access_token"] = token
    data = urllib.parse.urlencode(params).encode()
    url = f"https://{host}/{version}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("User-Agent", "uncsgroup-make-posts")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        sys.exit(f"Instagram API error on {path}: {e.code} {body.replace(token, '<token>')}")


def ig_user_id(token):
    if os.environ.get("IG_USER_ID"):
        return os.environ["IG_USER_ID"]
    if token.startswith("IG"):
        me = graph("GET", "me", token, fields="user_id,username")
        print(f"  Instagram account: @{me.get('username')}")
        return me["user_id"]
    pages = graph("GET", "me/accounts", token, fields="name,instagram_business_account{id,username}")
    for pg in pages.get("data", []):
        acct = pg.get("instagram_business_account")
        if acct:
            print(f"  Instagram account: @{acct.get('username')} (via Page {pg.get('name')})")
            return acct["id"]
    sys.exit("No Instagram professional account is linked to this token's Facebook Pages.")


def wait_ready(container, token):
    for _ in range(30):
        st = graph("GET", container, token, fields="status_code,status")
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram could not process {container}: {st}")
        time.sleep(5)
    sys.exit(f"Instagram still processing {container} after 150s; try again later.")


def publish(go, carousel):
    items = []
    for post in POSTS:
        story = load_story(post)
        name = f"{DATE}-{post['paper']}.jpg"
        local = OUT / name
        url = SITE_IG + name
        try:
            # Cloudflare turns away Python's default user agent
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (compatible; uncsgroup-make-posts)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                live = int(r.headers.get("Content-Length") or -1)
        except urllib.error.URLError as e:
            sys.exit(f"{url} is not live ({e}); commit and push first.")
        if live not in (-1, local.stat().st_size):
            sys.exit(f"{url} on the site differs from public/ig/{name}; push the latest images first.")
        items.append((post, story, url))

    done = json.loads(PUBLISHED.read_text(encoding="utf-8")) if PUBLISHED.exists() else {}
    already = done.get(DATE, {})
    todo = [(p, s, u) for p, s, u in items if p["paper"] not in already and not (carousel and already)]
    if not todo:
        print(f"  Nothing to post: {DATE} is already on Instagram ({', '.join(already)}).")
        return

    print(f"  {'One carousel of' if carousel else 'Separate posts for'} {len(todo)} image(s), in this order:")
    for p, s, u in todo:
        print(f"   - {PAPERS[p['paper']]['name']}: {u}")
    if carousel:
        print("  Carousel caption: the first post's caption, then a line for each of the others.")
    if not go:
        print("  Dry run: nothing posted. Add --go to post for real.")
        return

    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        sys.exit("Set IG_ACCESS_TOKEN first (see README: Posting to Instagram).")
    uid = ig_user_id(token)
    limit = graph("GET", f"{uid}/content_publishing_limit", token, fields="quota_usage,config")
    print(f"  Publishing limit: {json.dumps(limit.get('data', limit))}")

    def record(paper, media_id):
        done.setdefault(DATE, {})[paper] = media_id
        PUBLISHED.write_text(json.dumps(done, indent=1) + "\n", encoding="utf-8")

    if carousel:
        children = []
        for p, s, u in todo:
            c = graph("POST", f"{uid}/media", token, image_url=u, is_carousel_item="true")["id"]
            wait_ready(c, token)
            children.append(c)
        first_post, first_story, _ = todo[0]
        others = "\n".join(f"{i + 2}. {PAPERS[p['paper']]['name']}: {p.get('headline') or s['headline']}"
                           for i, (p, s, _) in enumerate(todo[1:]))
        credits = "\n".join(f"{PAPERS[p['paper']]['name']}: {s['image']['credit']}" for p, s, _ in todo)
        caption = f"{first_post['caption']}\n\nAlso today:\n{others}\n\n{credits}"
        c = graph("POST", f"{uid}/media", token, media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
        wait_ready(c, token)
        media = graph("POST", f"{uid}/media_publish", token, creation_id=c)["id"]
        for p, _, _ in todo:
            record(p["paper"], media)
        print(f"  Posted carousel: media id {media}")
        return

    for p, s, u in todo:
        c = graph("POST", f"{uid}/media", token, image_url=u, caption=full_caption(p, s))["id"]
        wait_ready(c, token)
        media = graph("POST", f"{uid}/media_publish", token, creation_id=c)["id"]
        record(p["paper"], media)
        print(f"  Posted {PAPERS[p['paper']]['name']}: media id {media}")
        time.sleep(3)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--publish", action="store_true",
                    help="post today's images to Instagram instead of rendering (a dry run unless --go)")
    ap.add_argument("--go", action="store_true", help="with --publish: really post")
    ap.add_argument("--carousel", action="store_true", help="with --publish: one carousel post instead of six")
    args = ap.parse_args()
    if args.publish:
        publish(args.go, args.carousel)
    else:
        main()
