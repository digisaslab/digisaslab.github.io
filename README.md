# DigiSAS Lab and FGEA Community of Practice

This repository hosts DigiSAS Lab at <https://digisaslab.github.io/> and the Future
Generation Enterprise Architecture Community of Practice at
<https://digisaslab.github.io/fgea-cop/>. The GitHub account name does not determine
the lab's branding or contact address. The FGEA contact remains
`FGEA@UTS.EDU.AU`.

Both websites are static. DigiSAS has local browser-side search across lab and
community content; neither site requires WordPress, a database or a search
service at runtime. Existing external registration links remain external.
The paid WordPress site and its DNS are not changed by this repository.

## Organiser quick start: publish without installing anything

Use the [repository on GitHub](https://github.com/digisaslab/digisaslab.github.io)
to write and review content in your browser. Each organiser needs their own
GitHub account and **Write** access to this repository, granted by a repository
administrator. Do not share accounts or passwords.

### 1. Choose the right website and content type

| What you are adding | File to create or edit | Published location |
| --- | --- | --- |
| FGEA news, announcement, or recap | `_posts/YYYY-MM-DD-short-title.md` | `/fgea-cop/news/` |
| FGEA symposium or other event | `_events/stable-event-id.md` | `/fgea-cop/events/` |
| FGEA information page | `your-page/index.md` | `/fgea-cop/your-page/` |
| Existing FGEA information | For example, `about/index.md` or `contact/index.md` | Its existing FGEA address |
| DigiSAS Lab news or information page | Add a record to `digisas/content/documents.json` | `/blog/` or the new lab page address |
| Lab homepage selections or event-cover labels | `digisas/content/homepage.json` | Lab homepage and news cards |

**The two sites currently have different authoring formats.** FGEA uses
Markdown; lab content uses JSON containing HTML. A file in `_posts/` is an FGEA
post, not a lab post. Follow the [lab authoring steps](digisas/README.md#adding-lab-posts-and-pages)
for DigiSAS content.

### 2. Create a working branch

1. On the repository's **Code** tab, select the branch menu showing `main`.
2. Enter a short branch name, for example `content/2027-q1-symposium`, and create
   it from `main`. Keep all related edits and image uploads on this branch.
3. For an existing file, open it and choose the pencil/edit button. For a new
   file, choose **Add file > Create new file** and enter its full path.
4. Copy the relevant template below, replace the example facts, and write the
   body. Keep the opening and closing `---` lines on Markdown records.
5. Choose **Commit changes**, write a short description, and commit to your
   working branch, **not `main`**.

GitHub button wording may vary slightly. Saving to this branch does not update
the public website.

### 3. Add the content and any pictures

- **A symposium announcement:** create an event using [Add an event](#add-an-event)
  and a news post using [Add a news item](#add-a-news-item). Give both the same
  `event_id`, following [Link news to an event](#link-news-to-an-event).
- **A standalone update:** create only a news post.
- **A new information page:** follow [Add an FGEA information page](#add-an-fgea-information-page).
  Unlike news and events, it needs a link from an existing page or navigation.
- **Pictures:** follow [Add event images](#add-event-images), including upload,
  alt text, actual dimensions, and the media-permission record. Never upload
  private attendee information or an unapproved photograph.

For FGEA drafts, use `published: false` until ready. Change it to `true` **on the
working branch before requesting final review**, or the item will stay hidden
after merging. New events can reuse the featured picture of their linked news
post. Without a supplied picture, the site provides an illustrated cover; do
not invent an event photograph.

### 4. Ask another organiser to review

1. Open **Pull requests > New pull request** (or **Compare & pull request**).
   Set the base to `main` and the compare branch to your working branch.
2. Describe the change and its intended public address. Request another
   organiser's review, especially for dates, registration links, and pictures.
3. Wait for the **Validate and deploy DigiSAS and FGEA** workflow's build check
   to pass. If it fails, open **Details**, read the first error, correct the
   file on the same branch, and commit again. Do not merge a failing build.
4. Check the **Files changed** tab for accidental deletions or unrelated edits.
   The reviewer should check the title, summary, dates/timezone, links, event
   status, image permissions, and spelling.

**A pull request runs checks but does not publish a preview website.** GitHub's
Markdown preview is not the final page layout. For a visual review before
publication, an organiser with a local setup can use
[Develop and validate](#develop-and-validate); otherwise check the rendered
page immediately after deployment.

### 5. Publish and check the live result

1. Once approved and passing, merge the pull request into `main`.
2. Open **Actions > Validate and deploy DigiSAS and FGEA** and wait for both
   `build` and `deploy` to finish successfully for that merge.
3. Open the public page and check it on a phone and desktop: picture, title,
   links, event time, and registration/contact action. Refresh if an older
   version is cached.
4. Check the relevant News or Events listing too. FGEA listings and the next
   symposium are automatic; new lab posts automatically enter lab news/search.
   A new information page needs an explicit link.

For corrections, edit the original source file through another branch and pull
request. Keep published addresses and event IDs stable. For an accidental
publication, revert the merged pull request on GitHub and let the resulting
change deploy, or ask a repository administrator to help. Never fix generated
files in `_site/`: the next build replaces them.

No WordPress login, hosting change, or DNS change is needed for routine posts.
The [detailed contribution guide](CONTRIBUTING.md) covers less common fields
and content-review requirements.

## Architecture

- `digisas/` contains the complete public lab content snapshot, localised media,
  responsive lab design and Python importer/builder. It is excluded from Jekyll
  and is never published as source.
- `_scripts/build_site.py` builds both sites into one `_site/` artifact: DigiSAS
  at `/`, the existing Jekyll community site at `/fgea-cop/`.
- The original WordPress FGEA overview is retained at
  `/fgea-cop/lab-overview/`; `/fgea-cop/` is the richer community landing page.
- Non-conflicting old FGEA page/media addresses remain available through
  redirects or asset copies. `/` and `/about/` now intentionally belong to
  DigiSAS; the corresponding FGEA pages live below `/fgea-cop/`.
- The root sitemap and search index cover both websites. The original FGEA
  `/feed.xml` is retained; the lab feed is `/feed/index.xml`.
- Jekyll layouts and includes render pages, collections, navigation, metadata,
  and JSON-LD.
- News uses Jekyll posts in `_posts/`.
- Events use the `_events/` collection.
- Resources use the optional `_resources/` collection.
- `_plugins/event_collections.rb` produces predictable upcoming, past, and
  recent activity collections in the `Australia/Sydney` timezone.
- `_data/` holds organisation, navigation, people, community, and media data.
- `_data/media.yml` is the provenance ledger for every migrated local image.
- Sass in `_sass/` and `assets/css/main.scss` produces the site stylesheet.
- `_scripts/validate_content.rb` checks the source content contract before a
  build.

Internal links use Jekyll's `relative_url` or `absolute_url` filters so the
site remains portable between root and project-path deployments.

Event media is stored under `assets/images/events/<event-id>/`. Historical
DigiSAS material retains its canonical source URL and source status; an elapsed
event date alone is never treated as evidence that an event occurred.

## Prerequisites and setup

- Ruby 3.4.4, as declared in `.ruby-version`
- Bundler
- Python 3.11 or newer

From the repository root:

```sh
gem install bundler
bundle config set --local path vendor/bundle
bundle install
python3 -m venv digisas/.venv
digisas/.venv/bin/python -m pip install -r digisas/requirements.txt
```

## Develop and validate

Build and serve the combined site locally:

```sh
digisas/.venv/bin/python _scripts/build_site.py
digisas/.venv/bin/python -m http.server 4000 --bind 127.0.0.1 --directory _site
```

Open <http://127.0.0.1:4000/> for DigiSAS or
<http://127.0.0.1:4000/fgea-cop/> for FGEA. On Homebrew macOS installations,
prefix build commands with `PATH=/opt/homebrew/opt/ruby/bin:$PATH` if the system
Ruby is older than the project version.

Run the source validator and the production build:

```sh
cd digisas && .venv/bin/python -m unittest discover -s tests && cd ..
digisas/.venv/bin/python _scripts/build_site.py
bundle exec htmlproofer ./_site --disable-external
```

To test a project-path deployment:

```sh
digisas/.venv/bin/python _scripts/build_site.py --base-path /example
bundle exec htmlproofer ./_site --disable-external --swap-urls '^/example/:/'
```

`FGEA_TODAY=YYYY-MM-DD` may be supplied to make event grouping deterministic
during a focused test.

See `digisas/README.md` for lab editing, refreshes and known source limitations.
Do not retire WordPress hosting before obtaining a full administrator
files/database backup, confirming the domain/email arrangements, and approving
the static site and external registration workflows. GitHub Pages hosting is
free; retaining a custom domain still incurs domain renewal charges.

## Add FGEA events, news, and pages

FGEA content is added with Markdown files. No page template or archive page needs
to be edited: Jekyll automatically adds published records to the Events, News,
and home pages.

### Add an event

1. Create `_events/<event-id>.md`. Use a stable, lowercase, hyphenated ID,
   such as `fgea-2026-q3-symposium`.
2. Copy this template and replace the example values:

```yaml
---
layout: event
event_id: fgea-2026-q3-symposium
title: "FGEA CoP 2026 Q3 Symposium"
summary: A hybrid FGEA CoP symposium scheduled for 24 September 2026.
start_date: "2026-09-24"
start_time: "10:00"
end_time: "12:30"
timezone: Australia/Sydney
format: hybrid
host_chapter: asia-pacific
event_status: confirmed
occurrence_status: scheduled
venue: Venue name, Sydney
registration_url: https://example.org/register
featured: false
published: true
topics: []
permalink: /events/fgea-2026-q3-symposium/
---

Add the event description, programme, speakers, and other reviewed details
here using Markdown.
```

Dates must be quoted and times use 24-hour `HH:MM`. Valid `format` values are
`online`, `in-person`, `hybrid`, and `unspecified`. Valid `event_status` values
are `confirmed`, `tentative`, `postponed`, and `cancelled`. Use
`occurrence_status: scheduled` for a future event, `occurred` after delivery
has been confirmed, or `unconfirmed` for an older schedule where delivery
cannot be verified. Omit `venue` and `registration_url` when they do not
apply. Set the optional `host_chapter` to a chapter `slug` defined in
`_data/community.yml`; omit it until the host is confirmed.

### Add a news item

1. Create `_posts/YYYY-MM-DD-<short-title>.md`. The filename date is the
   publication date.
2. Copy this template:

```yaml
---
layout: post
title: "News item title"
date: "2026-08-22"
summary: A concise summary shown on news listings.
kind: announcement
published: true
permalink: /news/short-title/
---

Write the news item here using Markdown.
```

Valid `kind` values are `announcement`, `recap`, `article`, and `update`. Use
`published: false` while drafting, then change it to `true` when the item is
ready.

The publication date should be today or earlier in Sydney time. Future-dated
FGEA news is hidden until its publication date and a successful build; the
workflow also runs daily. An event's future `start_date` is different: upcoming
events can be published now.

### Add an FGEA information page

Create `your-page/index.md` with a unique, lowercase, hyphenated page name:

```markdown
---
layout: page
title: "Working groups"
description: Information about the community's reviewed working groups.
permalink: /working-groups/
---

## What we do

Write the reviewed page content here.

[Contact the organisers]({{ '/contact/' | relative_url }})
```

In this example, name the file `working-groups/index.md`; it publishes at
`https://digisaslab.github.io/fgea-cop/working-groups/`. Do **not** put
`/fgea-cop` into the `permalink`: the build adds it. Link to the new page from
another relevant FGEA Markdown page with:

```liquid
[Working groups]({{ '/working-groups/' | relative_url }})
```

Only if it belongs in the main menu, add a matching `title` and `url` entry
under `primary` in `_data/navigation.yml`. Keep the menu short enough for
desktop and mobile. Ordinary pages do not appear in News or Events.

### Link news to an event

For an event announcement, update, or recap, create both files and give them
the same `event_id`:

```yaml
# In _posts/YYYY-MM-DD-short-title.md
event_id: fgea-2026-q3-symposium
```

This automatically adds links between the event and news pages. Use
`kind: recap` only after the event has occurred, and set the event record to
`occurrence_status: occurred`. Only one recap can be linked to each event.

An optional original source link can be added to either record. Both fields
must be supplied together:

```yaml
# Event
source: https://example.org/original
source_label: Original event page

# News
source_url: https://example.org/original
source_label: Original announcement
```

### Add event images

Store images in `assets/images/events/<event-id>/`. A featured image on a news
post or event requires all four fields below, inside its opening `---` block.
In GitHub, open `assets/images/events/` on your working branch and choose
**Add file > Upload files**. Drag in a folder named after your event ID,
containing the prepared JPEG or PNG files, and commit to the same branch.
For an existing event folder, open it and upload additional files there.
Use simple lowercase filenames without spaces.

```yaml
image: /assets/images/events/fgea-2026-q3-symposium/agenda.png
image_alt: Published agenda for the FGEA CoP 2026 Q3 Symposium
image_width: 1600
image_height: 900
image_caption: Published agenda for the 2026 Q3 symposium.
```

The width and height must match the actual image. Strip location, device, and
other private metadata before adding photographs. Record every new local image
in `_data/media.yml`; see existing entries for the required provenance fields.
Transcribe important text from agenda images into the Markdown body so it is
accessible.

Add a new entry **under the existing `items:` list** in `_data/media.yml`,
using the same indentation as neighbouring entries:

```yaml
  - path: /assets/images/events/fgea-2026-q3-symposium/agenda.png
    event_id: fgea-2026-q3-symposium
    source_page: https://example.org/original-event
    source_url: https://example.org/original-agenda.png
    original_format: PNG
    derivative: Metadata-free PNG, 1600x900.
    authorisation: Organiser-owned agenda; approved for public publication.
```

Replace the example links and permission statement with the actual provenance.
For an original organiser upload with no earlier public source, use the public
GitHub file URL as `source_url` and the intended public event URL as
`source_page`; do not invent a source or assume permission. Check pixel
dimensions in your image viewer's information panel before filling in width
and height. Ask an organiser familiar with image preparation to strip metadata
if you cannot verify it.

The featured image appears automatically; do not repeat it in the body unless
needed. To add an extra photograph to an FGEA record, upload it and record its
provenance too, then use:

```liquid
<figure>
  <img src="{{ '/assets/images/events/fgea-2026-q3-symposium/discussion.jpg' | relative_url }}"
       alt="Participants discussing the workshop exercise"
       width="1600" height="900" loading="lazy">
  <figcaption>Workshop discussion, with publication permission confirmed.</figcaption>
</figure>
```

Replace the path, dimensions, description, and caption with accurate values.
Do not prefix FGEA image paths with `/fgea-cop`; `relative_url` handles it.
Listing cards may show a readable title/date cover instead of an agenda
thumbnail; the original featured agenda stays available on the detail page.

### Preview and publish

Build the shared site and open <http://127.0.0.1:4000/fgea-cop/> to review
FGEA content, or the root address for DigiSAS:

```sh
digisas/.venv/bin/python _scripts/build_site.py
digisas/.venv/bin/python -m http.server 4000 --bind 127.0.0.1 --directory _site
```

Before publishing, run:

```sh
digisas/.venv/bin/python _scripts/build_site.py
bundle exec htmlproofer ./_site --disable-external
```

Commit the content files and push them to a branch for review. A pull request
build validates the site without deploying it. Merging or pushing the approved
change to `main` deploys the updated site through GitHub Actions.

For complete field definitions, image requirements, redirects, drafts, and the
review checklist, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Deployment

`.github/workflows/pages.yml` validates content, builds with the base path
derived from the repository name, checks internal HTML links, uploads `_site`, and
deploys that artifact. Pull requests validate without deploying. Pushes to
`main`, manual runs, and the scheduled workflow can deploy.

Only `_site` is uploaded. Source files, configuration, dependencies,
documentation, scripts, and caches are not included in the published artifact.

## Repository structure

| Path | Purpose |
| --- | --- |
| `_config.yml` | Jekyll, collection, plugin, URL, and exclusion settings |
| `_data/` | Reviewed structured facts used across pages |
| `_events/` | Event records |
| `_posts/` | News, announcements, articles, updates, and recaps |
| `_resources/` | Resource records, created when the first resource is ready |
| `_includes/`, `_layouts/` | Reusable presentation and metadata templates |
| `_plugins/` | Build-time event and activity logic |
| `_scripts/` | Shared-site build and FGEA source validation |
| `digisas/` | Public lab content snapshot, media provenance, importer and static builder |
| `_sass/`, `assets/` | Styles, JavaScript, images, and downloads |
| `about/`, `chapters/`, `community/`, `contact/`, `events/`, `news/`, `resources/` | Archive and information pages |

See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete content schemas and
publishing requirements.
