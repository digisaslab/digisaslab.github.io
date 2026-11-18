import unittest

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


if __name__ == "__main__":
    unittest.main()
