# Uncs Group — www.uncsgroup.com

The parent company's site. It lists every Uncs Group paper (Outdoor Unc and
Finance Unc today) and is built to take more: sports, entertainment, hobbies,
news or anything else. Plain static HTML. No build step, no database, no API.

```
public/index.html      the page (both logos are inlined in it)
public/404.html        not-found page
public/robots.txt      allows crawling, points at the sitemap
public/sitemap.xml     the one URL
public/_headers        security and cache headers for Cloudflare Pages
public/assets/         logos, favicon, share image (og.png)
```

To change the wording, edit `public/index.html` on GitHub and commit; Cloudflare
redeploys in under a minute.

## The logo

The Uncs Group mark is the stache: a single handlebar moustache. It is Unc, the
one who reads the fine print and tells it straight, and it belongs to no single
subject, so it can sit over any paper the group launches.

```
assets/uncsgroup-logo.svg   stache + UNCS GROUP + tagline (follows light/dark via --ink/--meta)
assets/uncsgroup-mark.svg   the stache alone, in ink
assets/favicon.svg          browser tab: light stache on an ink rounded square
assets/icon-180.png         phone home screen (Apple touch icon)
assets/icon-512.png         app stores, social profiles, the logo in search results
assets/og.png               link preview image
```

Rules of thumb: keep the stache one colour (ink on light, white on ink or on a
paper's colour); never stretch it, outline it or add a face around it; leave at
least half its height clear around it. Other directions considered are in
`brand-options/`.

## Adding a paper

1. In `public/index.html`, copy one `<a class="paper ...">` block inside
   `<main class="papers">`, change the link, logo, promise and beats.
2. In the `<style>` block, add a class for it next to `.outdoor` and `.finance`
   with its card colour, edge, accent and text colours.
3. Add it to the `subOrganization` list in the JSON-LD at the top, and to the
   footer.
The grid lays out any number of papers: one column on phones, two or three on
wider screens.

Setup is in `SETUP.md`.
