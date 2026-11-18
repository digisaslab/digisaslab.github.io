import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from bs4 import BeautifulSoup

from scripts.build import Builder


class MigrationRenderingTests(unittest.TestCase):
    def setUp(self):
        self.builder = Builder()
        self.doc = {
            "url": "https://www.digisaslab.org/about/",
            "path": "/about/",
            "content": "",
        }

    def test_project_site_rewrites_pages_search_and_media(self):
        self.builder.base = "/digisas-lab"
        self.assertEqual(self.builder.url("/people/#researchers", self.doc), "/digisas-lab/people/#researchers")
        self.assertEqual(self.builder.url("/?s=agentic+AI", self.doc), "/digisas-lab/search/?q=agentic%20AI")
        media_path = next(iter(self.builder.media_by_path))
        self.assertEqual(self.builder.url(media_path, self.doc, "src"), "/digisas-lab" + media_path)

    def test_wordpress_id_links_preserve_the_destination(self):
        identity, path = next(iter(self.builder.ids.items()))
        self.assertEqual(self.builder.url(f"/?p={identity}", self.doc), path)

    def test_converted_images_use_browser_compatible_routes(self):
        source = "/wp-content/uploads/photo.heic"
        self.builder.media_by_path[source] = {"path": "/assets/imported" + source + ".jpg"}
        self.assertEqual(self.builder.url(source, self.doc, "src"), source + ".jpg")

    def test_content_keeps_text_but_removes_wordpress_runtime(self):
        self.doc["content"] = '<p onclick="bad()">Hello <strong>world</strong>.</p><script>bad()</script><iframe src="https://www.digisaslab.org/about/embed/"></iframe>'
        rendered = self.builder.content(self.doc)
        self.assertIn("Hello <strong>world</strong>.", rendered)
        for removed in ("onclick", "<script", "<iframe"):
            self.assertNotIn(removed, rendered)

    def test_missing_source_image_has_a_non_broken_placeholder(self):
        self.doc["content"] = '<p>Speaker</p><img src="/wp-content/uploads/missing.jpg" alt="Speaker portrait">'
        rendered = self.builder.content(self.doc)
        self.assertNotIn("<img", rendered)
        self.assertIn("Speaker portrait", rendered)
        self.assertEqual(len(self.builder.issues["missing_images"]), 1)

    def test_css_only_research_visuals_are_preserved(self):
        path = next(iter(self.builder.media_by_path))
        self.doc["content"] = f'<div style="background-image:url({path})"><h3>Research</h3></div>'
        rendered = self.builder.content(self.doc)
        self.assertIn(f'src="{path}"', rendered)
        self.assertIn("<h3>Research</h3>", rendered)
        self.assertNotIn("style=", rendered)

    def test_external_registration_links_remain_external(self):
        url = "https://events.humanitix.com/example"
        self.assertEqual(self.builder.url(url, self.doc), url)
        self.assertEqual(self.builder.url("javascript:alert(1)", self.doc), "")

    def test_imported_email_link_whitespace_is_repaired(self):
        source = "mailto:FEITshortcourses@UTS.edu.au%20?subject=Course"
        self.assertEqual(self.builder.url(source, self.doc),
                         "mailto:FEITshortcourses@UTS.edu.au?subject=Course")

    def test_empty_source_links_keep_their_text(self):
        self.doc["content"] = '<p><a>Speaker name</a> <a id="topic"></a></p>'
        rendered = self.builder.content(self.doc)
        self.assertIn("Speaker name", rendered)
        self.assertIn('id="topic"', rendered)
        self.assertNotIn("<a", rendered)

    def test_featured_picture_is_restored_for_image_free_posts(self):
        source = next(d["featured_image"] for d in self.builder.documents if d.get("featured_image"))
        document = {**self.doc, "title": "Research news", "featured_image": source}
        visual = self.builder.visual(document)
        self.assertNotEqual(visual["kind"], "illustration")
        self.assertIn("/wp-content/uploads/", visual["src"])

    def test_full_size_srcset_preserves_unicode_filenames(self):
        prefix = "https://www.digisaslab.org/wp-content/uploads/2026/09/Screenshot-2026-09-24-at-9.26.49\u202fam"
        image = {"src": prefix + "-1024x515.png", "srcset": prefix + "-1024x515.png 1024w, " + prefix + ".png 1576w"}
        self.assertEqual(self.builder.image_source(image, self.doc), prefix + ".png")

    def test_missing_source_pictures_use_honest_editorial_art(self):
        visual = self.builder.visual({**self.doc, "title": "Research seminar", "slug": "research-seminar"})
        self.assertEqual(visual["kind"], "illustration")
        self.assertTrue(visual["src"].endswith("/editorial/talk.svg"))

    def test_people_cards_restore_sarv_without_losing_any_biographies(self):
        document = next(d for d in self.builder.documents if d["path"] == "/people/")
        source = BeautifulSoup(document["content"], "html.parser")
        rendered = BeautifulSoup(self.builder.content(document), "html.parser")
        self.assertEqual(" ".join(source.get_text(" ", strip=True).split()),
                         " ".join(rendered.get_text(" ", strip=True).split()))
        portrait = rendered.select_one("#sarv-girn img")
        self.assertIsNotNone(portrait)
        self.assertTrue(portrait["src"].endswith("/Sarv.jpg"))
        self.assertEqual(portrait["alt"], "Sarv Girn")
        self.assertEqual(portrait["loading"], "eager")

    def test_header_uses_official_local_logo_at_project_base_path(self):
        with TemporaryDirectory() as directory:
            self.builder.output = Path(directory)
            self.builder.base = "/example"
            self.builder.write("/", "Home", "<h1>Home</h1>")
            soup = BeautifulSoup((Path(directory) / "index.html").read_text(), "html.parser")
        logo = soup.select_one(".brand-logo")
        self.assertIsNotNone(logo)
        self.assertEqual(logo["src"], "/example/wp-content/uploads/2022/03/cropped-DigiSAS-Logo-Under-Black.png")
        self.assertEqual(logo["alt"], "DigiSAS Lab")
        self.assertEqual(logo.parent["href"], "/example/")
        self.assertIsNone(soup.select_one(".brand-mark"))

    def test_news_navigation_keeps_section_context_on_articles_and_archives(self):
        with TemporaryDirectory() as directory:
            self.builder.output = Path(directory)
            for route in ("/blog/example/", "/blog/2026/", "/category/example/"):
                with self.subTest(route=route):
                    if route.startswith("/category/"):
                        self.builder.archives[route] = ("Archive", [])
                    self.builder.write(route, "News", "<h1>News</h1>")
                    soup = BeautifulSoup((Path(directory) / route.lstrip("/") / "index.html").read_text(), "html.parser")
                    link = soup.select_one('nav a[href="/blog/"]')
                    self.assertEqual(link["aria-current"], "location")
            self.builder.write("/blog/", "News", "<h1>News</h1>")
            soup = BeautifulSoup((Path(directory) / "blog/index.html").read_text(), "html.parser")
            self.assertEqual(soup.select_one('nav a[href="/blog/"]')["aria-current"], "page")

    def test_archive_card_titles_fit_the_page_heading_hierarchy(self):
        rendered = BeautifulSoup(self.builder.cards(self.builder.posts[:1], heading_level=2), "html.parser")
        title = rendered.select_one(".card h2 a")
        self.assertEqual(title.get_text(), self.builder.posts[0]["title"])
        self.assertEqual(title["href"], self.builder.posts[0]["path"])
        self.assertIsNone(rendered.select_one(".card h3"))

    def test_event_card_uses_a_readable_cover_without_removing_the_original_agenda(self):
        self.builder.base = "/example"
        document = next(doc for doc in self.builder.documents if doc["id"] == 1734)
        card = BeautifulSoup(self.builder.cards([document]), "html.parser")
        self.assertEqual(card.select_one(".card-media img")["src"], "/example/assets/editorial/cover-field.svg")
        self.assertIn("26 November 2026", card.select_one(".cover-note").get_text())
        self.assertEqual(card.h3.a.get_text(), document["title"])
        detail = BeautifulSoup(self.builder.content(document), "html.parser")
        self.assertTrue(any("Pasted-2026-11-17" in image["src"] for image in detail.select("img")))

    def test_homepage_prioritises_research_and_links_to_original_projects_and_people(self):
        self.builder.base = "/example"
        home = BeautifulSoup(self.builder.homepage_content(), "html.parser")
        sections = [section.get("aria-labelledby") for section in home.select("section")]
        self.assertLess(sections.index("projects-title"), sections.index("news-title"))
        research = BeautifulSoup(self.builder.content(next(doc for doc in self.builder.documents if doc["path"] == "/research/")), "html.parser")
        people = BeautifulSoup(self.builder.content(next(doc for doc in self.builder.documents if doc["path"] == "/people/")), "html.parser")
        for link in home.select(".project-preview a, .theme-link, .person-preview"):
            target = people if "/people/" in link["href"] else research
            self.assertTrue(link["href"].startswith("/example/"))
            self.assertIsNotNone(target.find(id=link["href"].split("#")[1]))
        self.assertIn("Executable Twin", home.select_one(".hero-visual img")["alt"])
        self.assertTrue(all(link.find("img").get("alt") for link in home.select(".person-preview")))


if __name__ == "__main__":
    unittest.main()
