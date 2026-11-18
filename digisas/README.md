# DigiSAS Lab static website

An editable migration of the public DigiSAS Lab WordPress website, integrated
into the existing FGEA repository. The shared build makes DigiSAS the homepage
and keeps the community at `/fgea-cop/`. Building locally does not change the
live WordPress website or its DNS.

## Build and preview

Requires Python 3.11 or newer and the repository's existing Ruby/Bundler
environment. Run these commands from the repository root:

```sh
python3 -m venv digisas/.venv
digisas/.venv/bin/python -m pip install -r digisas/requirements.txt
digisas/.venv/bin/python _scripts/build_site.py
digisas/.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory _site
```

Open <http://127.0.0.1:8765/>. Stop the server with Ctrl+C.
There is no production server, database, WordPress installation or paid theme.
The generated site consists only of HTML, CSS, JavaScript, media and a search index.

## Content

- `content/documents.json`: page/post titles, original paths, dates and HTML bodies.
- `content/media.json`: source URLs, local files and file hashes.
- `content/taxonomies.json`: original categories and tags.
- `content/attachments.json`: linked WordPress attachment pages.
- `content/site.json`: route overrides, additional imported media, and image replacements.
- `assets/imported/`: downloaded images and documents, with image EXIF removed.
- `assets/web/`: the new site's stylesheet and browser-side code.

Edit a document's `content` field to update its body, keeping valid JSON and HTML.
Its `path` preserves the old public address. To add a post, add a new document with
a unique ID, `kind: "post"`, title, slug, path, source URL, ISO date, modified date,
HTML content, HTML excerpt, category/tag ID arrays and optional featured image.
The source URL is used to resolve relative links; use the intended final URL for
new content. The completeness check permits additional content but protects
original imported documents and routes from accidental deletion.

The importer is for pre-cutover refreshes, not a CMS. It replaces the snapshot's
document and media indexes. **Back up or commit local editorial changes before
running it; do not overwrite new static-site content with a WordPress import.**

```sh
digisas/.venv/bin/python digisas/scripts/migrate.py
```

This refreshes public content and media. `--reuse-media` refreshes text while
retaining already downloaded media. Builds and deployments do not contact
WordPress.

## Pictures and visual design

News cards use their own published pictures, and image-free articles display
their imported featured image. Where no source picture exists, original SVG
editorial covers provide a visual without pretending to be event photography.
These repository-authored illustrations and the homepage's decorative field
live in `assets/web/editorial/`. The shared FGEA cover is recorded separately
under `editorial_assets` in `_data/media.yml`.

FGEA event cards and detail pages reuse the picture from their linked news
record unless the event supplies its own. Agenda images are shown uncropped.
Keep accurate image descriptions and captions with the original news record.

To replace a low-resolution source picture, map its original URL path to the
verified full-size source URL in `content/site.json` under `image_overrides`.
Also list that URL in `additional_media` so later imports retain it. The image
must be downloaded into the local media manifest, not hotlinked. Sarv Girn's
portrait uses this mechanism on both his people and historical speaker pages.

## GitHub Pages

The root Actions workflow builds and validates both sites before deploying the
shared artifact when changes reach `main`. The existing repository is already
configured to use GitHub Actions for Pages.

Both organisation/user root sites and project sites are supported:

```sh
digisas/.venv/bin/python _scripts/build_site.py \
  --base-path /example --site-url https://example.github.io
```

The workflow derives the root/project base path from the repository name.
Do not add a `CNAME` or change DNS until the final domain has been selected and
the preview accepted.

## Preserved and changed behaviour

Original page/post paths, text, internal links, category/tag/date archives,
linked files, external registration links and published contact details are
preserved. The homepage, navigation and responsive layout are new. Search runs
entirely in the browser; it requires JavaScript. News is also available as
`/feed/index.xml`; existing feed subscribers should use this explicit XML URL.

WordPress administration, PHP plugins, database access and API endpoints are not
part of a static site. No active contact forms or comment threads were found in
the imported public document bodies. Existing Humanitix, Google Forms, meeting,
video and other external links still depend on their respective providers.
There is no new form backend and no claim that registrations are captured locally.

One historical organiser portrait was already missing on the source site.
Its text is preserved and its image has an accessible placeholder. The exact
source issue is recorded in `migration/known-source-issues.json`; unexpected
missing assets fail validation.

The existing FGEA community site is retained at
<https://fgeacop.github.io/fgea-cop/>. Its native event/news archive now also
includes the 2026 Q3 and Q4 symposium records. The original public FGEA overview
is retained at `/fgea-cop/lab-overview/`.

Public REST data is not a full WordPress backup. Before retiring paid hosting,
obtain an administrator export and a complete files/database backup, check any
hosting-bundled email/domain services, approve the final site and domain, and
confirm external registration/contact workflows. A custom domain still has
renewal costs even when GitHub Pages hosting is free.

## Checks

```sh
cd digisas && .venv/bin/python -m unittest discover -s tests && cd ..
digisas/.venv/bin/python _scripts/build_site.py
node --check digisas/assets/web/site.js
```

With the preview server running and Google Chrome installed, optional browser
checks exercise desktop/mobile layouts, visible images, navigation and search:

```sh
node digisas/scripts/browser-check.mjs http://127.0.0.1:8765 /tmp/digisas-browser-results
```

Set `CHROME` to the browser executable if necessary. Screenshots and results are
written only to the selected output directory.
