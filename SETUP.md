# Setting up www.uncsgroup.com

Same pattern as Finance Unc, minus the database. About 20 minutes plus waiting
for the nameservers.

## 1. Put the files on GitHub
1. github.com -> New repository -> name it `uncsgroup`, Private, create.
2. Click "uploading an existing file". Drag in everything inside this folder:
   `README.md`, `SETUP.md` and the `public` folder. Commit.
3. The repo's top level should show `public/` and `README.md`. Inside `public/`
   should be `index.html`.

## 2. Add the domain to Cloudflare
1. Cloudflare home -> Domains -> Add domain -> `uncsgroup.com` -> Free plan.
2. Cloudflare imports the Squarespace records. Delete all of these on the
   review screen (they point at a Squarespace site you are not using):
   - the four A records for `uncsgroup.com` (198.185.159.x, 198.49.23.x)
   - the `www` CNAME to `ext-sq.squarespace.com`
   - the `_domainconnect` CNAME
   Keep the TXT records (SPF, DMARC, DKIM).
3. Cloudflare shows two nameservers. In Squarespace -> Domains -> uncsgroup.com
   -> DNS -> Domain Nameservers, switch to custom nameservers and enter them.
   (Squarespace will then say "You're using custom nameservers"; that is right.)
4. Wait for Cloudflare to show uncsgroup.com as Active.

## 3. Create the Pages project
1. Workers & Pages -> Create application. Use the Pages option (a Pages tab, or
   the "Looking to deploy Pages? Get started" link at the bottom). Not the
   Workers form with a "Deploy command" box.
2. Import an existing Git repository -> GitHub -> `outdooruncs-maker/uncsgroup`.
   If it is not listed, give the Cloudflare GitHub app access to the repo at
   github.com/settings/installations -> Cloudflare Workers and Pages -> Configure.
3. Build settings:

   | | |
   |---|---|
   | Project name | `uncsgroup` |
   | Production branch | `main` |
   | Framework preset | None |
   | Build command | *(leave empty)* |
   | Build output directory | `public` |

4. Save and Deploy. Check `uncsgroup.pages.dev`.

## 4. Connect www.uncsgroup.com
Workers & Pages -> uncsgroup -> Custom domains -> Set up a custom domain ->
`www.uncsgroup.com` -> Activate.

## 5. Redirect uncsgroup.com to www
1. uncsgroup.com -> DNS -> Records -> Add record: type AAAA, name `@`,
   address `100::`, Proxied.
2. Rules -> Overview -> Create rule -> Redirect Rule:
   - Custom filter expression: Field `Hostname`, Operator `equals`,
     Value `uncsgroup.com`  (just the domain; nothing else in the box).
     Expression preview must read: `(http.host eq "uncsgroup.com")`
   - Then: Type Dynamic, expression
     `concat("https://www.uncsgroup.com", http.request.uri.path)`
   - Status 301, Preserve query string checked. Save.

## 6. Check
- https://www.uncsgroup.com loads the two-paper page.
- https://uncsgroup.com and http://uncsgroup.com redirect (301) to www.
- Both links open the papers.

## Optional
- Search Console: add the domain and submit https://www.uncsgroup.com/sitemap.xml.
- Link back from each paper's footer or About page to www.uncsgroup.com.
- The domain was registered Oct 16, 2026, so it can move to Cloudflare Registrar
  from Dec 15, 2026, the same day as financeunc.com.
