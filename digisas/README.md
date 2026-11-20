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

## Adding lab posts and pages

For browser-only branches, organiser review, and publishing, start with the
[organiser quick start](../README.md#organiser-quick-start-publish-without-installing-anything).
These steps are for **DigiSAS Lab**, not the FGEA Markdown collections.
Lab authoring currently requires JSON and a small amount of HTML; there is no
WordPress-style visual editor.

1. On your working branch, open `digisas/content/documents.json` and choose
   **Edit**. This file is one JSON array of document objects.
2. Add a comma after the last existing object, then paste the object below
   **before the final `]`**. Do not replace an imported record to create a new
   one.
3. Choose an integer `id` not used by any other document. `200001` below is an
   example, not a reusable ID; search the file for it before using it.
4. Replace the title, slug, dates, path, body, and summary. Keep all keys.
   Use a unique address ending in `/`; do not reuse an existing page, archive,
   `/fgea-cop/` route, or other generated address.
5. Save on the branch, then follow the root README's pull-request review and
   deployment steps. Check the resulting `/blog/` listing and the new page.

Copy this object for a lab news post:

```json
{
  "id": 200001,
  "kind": "post",
  "slug": "research-workshop-announcement",
  "title": "Research workshop announcement",
  "url": "https://digisaslab.github.io/blog/2027/02/01/research-workshop-announcement/",
  "path": "/blog/2027/02/01/research-workshop-announcement/",
  "date": "2027-02-01T09:00:00",
  "modified": "2027-02-01T09:00:00",
  "content": "<p>Write the reviewed announcement here.</p><h2>Details</h2><p>Add confirmed dates, speakers, and registration information.</p>",
  "excerpt": "<p>A short, factual summary for news cards.</p>",
  "categories": [],
  "tags": [],
  "featured_image": null
}
```

Use the actual publication date consistently in `date`, `url`, and `path`.
Update `modified` when correcting a record. Leave category/tag arrays empty
unless using IDs already defined in `content/taxonomies.json`.

**Lab records do not currently support drafts or scheduled publication.**
Every record in `documents.json` is built, even with a future date or a
`published: false` field. Keep unfinished or embargoed work off `main`.
Unmerged branches are not deployed but are still visible in this public
repository: never use them for confidential drafts or private material.

For an information page, use the same object with `"kind": "page"`, a unique
`slug` such as `"industry-collaboration"`, and matching addresses:

```json
"url": "https://digisaslab.github.io/industry-collaboration/",
"path": "/industry-collaboration/"
```

New lab posts enter the news archive, recent homepage news, feed, and search
automatically. New information pages enter **All pages & archives** and search;
also link them from a relevant existing lab page. The lab's main navigation is
defined in `scripts/build.py`, not `_data/navigation.yml`; ask the maintainer
to change it only when a new main-menu entry is necessary.

### Writing the lab body

The `content` and `excerpt` values are HTML strings, not Markdown. Useful
elements are `<p>Paragraph</p>`, `<h2>Section heading</h2>`, and
`<ul><li>List item</li></ul>`. The template supplies the main page title, so do
not add another `<h1>`.

JSON requires double quotes around strings and commas between fields/objects,
but no trailing comma before `}` or `]`. Inside a JSON string, escape HTML
attribute quotes with `\"`, for example:

```json
"content": "<p><a href=\"/research/\">Explore our research</a></p>"
```

Do not paste literal line breaks inside a JSON string; use one line or escaped
`\n`. Use root-relative lab links such as `/research/` and
`/fgea-cop/events/`, or full HTTPS addresses for external websites. The build
checks internal destinations.

### Pictures for lab content

- To reuse an existing lab picture, find its `source` URL in
  `content/media.json`. Copy that complete URL into `featured_image` instead
  of `null`. Use a photograph genuinely related to the post.
- To show it within the article as well, add an `<img>` inside a `<figure>` in
  `content`, with accurate `alt` text and a `<figcaption>`; escape its attribute
  quotes as above. The existing manifest lets the build serve a local copy.
- Without a supplied picture, a new record gets an illustrated cover. There
  is no need to invent a photo or edit CSS.
- **A new upload needs maintainer preparation:** the file must be metadata-free,
  placed in `assets/imported/`, and registered with its source, path, byte
  count, and hashes in `content/media.json`. Simply uploading a photo or
  pasting a new external URL into `featured_image` is not enough for the
  automatic card image to use it. Include the approved photo, caption, and
  provenance in the review handoff; do not run the WordPress importer to add it.

The FGEA Markdown image-upload workflow is separate and documented in the
[root README](../README.md#add-event-images).

### Correcting existing lab content

Search `documents.json` for the page's `path` or title. Change only the relevant
body/title/summary and `modified` date, preserving its ID and published address.
For people, edit the original `/people/` content; homepage previews reuse those
profiles. Selected homepage research links and cover labels are in
`content/homepage.json`. Never edit `_site/` output or refresh from WordPress as
part of routine publishing.

## Refreshing the original WordPress import

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

The header uses the original DigiSAS Lab logo published on the WordPress site,
downloaded locally and recorded in the media manifest. Its source and original
dimensions are configured under `logo` in `content/site.json`, and its URL is
also included in `additional_media` so later imports retain it.

Shared colours, typography and cover treatments live in `assets/web/identity.css`,
loaded by both DigiSAS and FGEA. The lab homepage is research-led; its selected
projects, three research themes, photographed workshop and dated event-cover
labels are configured in `content/homepage.json`. Project previews reuse the
original research descriptions and link to their full records.

News cards use their own published photographs, and image-free articles display
their imported featured image. Where no source picture exists, original SVG
editorial covers provide a visual without pretending to be event photography.
These repository-authored illustrations and the shared cover-field artwork
live in `assets/web/editorial/`. The shared FGEA cover is recorded separately
under `editorial_assets` in `_data/media.yml`.

FGEA events reuse the picture from their linked news record unless the event
supplies its own. Listing cards replace agenda screenshots with legible,
title-and-date covers; the original, uncropped agendas remain on detail pages.
Cover markup retains its original image reference for build-time validation.
Keep accurate image descriptions and captions with the original news record.
Photograph galleries use consistent thumbnails linked to the full-size images.
People use compact, centred directory entries rather than large boxes.
Incomplete card rows are centred; longer prose remains left-aligned
in a narrower reading column. FGEA listing pages use `wide: true` with the shared
card includes to keep the same layout across event, news, and leadership records.

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

The workflow derives the Pages origin from the repository owner and the
root/project base path from the repository name.
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
<https://digisaslab.github.io/fgea-cop/>. Its native event/news archive now also
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
