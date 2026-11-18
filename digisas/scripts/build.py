#!/usr/bin/env python3
"""Build the editable content snapshot into a dependency-free static website."""

import argparse
import html
import json
import re
import shutil
import urllib.parse
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://www.digisaslab.org"
HOSTS = {"www.digisaslab.org", "digisaslab.org"}
ESC = html.escape


def load(name):
    return json.loads((ROOT / "content" / f"{name}.json").read_text())


class Builder:
    def __init__(self, base_path="", site_url="", output=None):
        self.base = "/" + base_path.strip("/") if base_path.strip("/") else ""
        self.site_url = site_url.rstrip("/")
        self.output = Path(output).resolve() if output else ROOT / "_site"
        self.route_overrides = load("site").get("route_overrides", {})
        self.documents = load("documents")
        self.posts = sorted((d for d in self.documents if d["kind"] == "post"),
                            key=lambda d: d["date"], reverse=True)
        self.media = {m["source"]: m for m in load("media")}
        self.media_by_path = {urllib.parse.unquote(urllib.parse.urlsplit(u).path): m
                              for u, m in self.media.items()}
        self.ids = {str(d["id"]): d["path"] for d in self.documents}
        self.taxonomies = load("taxonomies")
        self.attachments = load("attachments")
        self.routes = {d["path"] for d in self.documents} | {"/", "/blog/", "/search/", "/pages/", "/feed/"}
        self.archives = {"/blog/": ("News & events", self.posts)}
        self.issues = {"missing_images": [], "external_dependencies": [], "unresolved_local_links": []}
        self.search = []
        self.generated = set()
        for taxonomy, field in (("categories", "categories"), ("tags", "tags")):
            for term in self.taxonomies[taxonomy]:
                items = [d for d in self.posts if term["id"] in d[field]]
                self.archives[urllib.parse.urlsplit(term["url"]).path] = (html.unescape(term["name"]), items)
        date_archives = defaultdict(list)
        for post in self.posts:
            date = post["date"][:10].replace("-", "/")
            for length in (4, 7, 10):
                date_archives[f"/blog/{date[:length]}/"].append(post)
        for path, items in date_archives.items():
            self.archives[path] = ("News archive: " + path.removeprefix("/blog/").strip("/"), items)
        self.archives["/blog/author/admin/"] = ("News & events", self.posts)
        for number in range(1, (len(self.posts) + 9) // 10 + 1):
            items = self.posts[(number - 1) * 10:number * 10]
            self.archives[f"/page/{number}/"] = ("News & events", items)
            self.archives[f"/blog/page/{number}/"] = ("News & events", items)
        self.routes.update(self.archives)
        self.routes.update(item["path"] for item in self.attachments)
        self.routes.update(self.route_overrides.values())

    def local(self, path):
        return self.base + path

    def url(self, value, document, attribute="href"):
        if value and value.startswith("mailto:"):
            parsed = urllib.parse.urlsplit(value)
            address = urllib.parse.quote(urllib.parse.unquote(parsed.path).strip(), safe="@+.,")
            return "mailto:" + address + ("?" + parsed.query if parsed.query else "")
        if not value or value.startswith(("#", "tel:")):
            return value
        absolute = urllib.parse.urljoin(document["url"], value)
        parsed = urllib.parse.urlsplit(absolute)
        if parsed.scheme not in {"https", "http"}:
            return ""
        if parsed.hostname not in HOSTS:
            if parsed.scheme == "http" and parsed.hostname in {"data-science-group.github.io", "collectivelearning.ai"}:
                absolute = urllib.parse.urlunsplit(parsed._replace(scheme="https"))
            self.issues["external_dependencies"].append({"page": document["path"], "url": absolute, "type": attribute})
            return absolute
        path = urllib.parse.unquote(parsed.path)
        query = urllib.parse.parse_qs(parsed.query)
        if "p" in query or "page_id" in query:
            path = self.ids.get((query.get("p") or query["page_id"])[0], path)
        if "s" in query:
            return self.local("/search/") + "?q=" + urllib.parse.quote(query["s"][0])
        if path in self.media_by_path:
            public_path = self.media_by_path[path]["path"].removeprefix("/assets/imported")
            return self.local(public_path) + ("#" + parsed.fragment if parsed.fragment else "")
        if path in self.routes:
            return self.local(path) + ("#" + parsed.fragment if parsed.fragment else "")
        self.issues["unresolved_local_links"].append({"page": document["path"], "url": absolute, "type": attribute})
        return absolute

    def content(self, document):
        soup = BeautifulSoup(document["content"], "html.parser")
        for node in soup.select("[style]"):
            for candidate in re.findall(r"url\(([^)]+)\)", node["style"]):
                source = urllib.parse.urljoin(document["url"], candidate.strip(" '\""))
                if urllib.parse.urlsplit(source).hostname in HOSTS:
                    image = soup.new_tag("img", src=source, alt="", attrs={"class": "imported-background"})
                    node.insert(0, image)
        for node in soup.find_all(["script", "style", "object", "embed", "form", "input", "button"]):
            node.decompose()
        for frame in soup.find_all("iframe"):
            source = frame.get("src", "")
            if urllib.parse.urlsplit(source).hostname in HOSTS:
                # WordPress adds an iframe beside an already usable blockquote link.
                frame.decompose()
            else:
                link = soup.new_tag("a", href=source)
                link.string = frame.get("title") or "View embedded content"
                frame.replace_with(link)
        for anchor in soup.find_all("a"):
            if not anchor.get("href"):
                if anchor.get("id") or anchor.get("name"):
                    anchor["id"] = anchor.get("id") or anchor["name"]
                    anchor.name = "span"
                else:
                    anchor.unwrap()
        for image in list(soup.find_all("img")):
            path = urllib.parse.unquote(urllib.parse.urlsplit(
                urllib.parse.urljoin(document["url"], image.get("src", ""))).path)
            if path not in self.media_by_path:
                self.issues["missing_images"].append({"page": document["path"], "url": image.get("src", "")})
                placeholder = soup.new_tag("span", attrs={"class": "image-unavailable"})
                placeholder.string = image.get("alt") or "Image unavailable"
                image.replace_with(placeholder)
            else:
                image["loading"] = "lazy"
                image["decoding"] = "async"
                image.attrs.pop("srcset", None)
                image.attrs.pop("sizes", None)
                if not image.has_attr("alt"):
                    image["alt"] = ""
        for node in soup.find_all(True):
            for attribute in list(node.attrs):
                if attribute.startswith("on") or attribute in {"style", "srcdoc", "data-secret", "data-src"}:
                    del node[attribute]
            if node.name == "a":
                node["rel"] = "noopener noreferrer" if node.get("target") == "_blank" else "noopener"
            for attribute in ("href", "src", "poster"):
                if node.has_attr(attribute):
                    node[attribute] = self.url(node[attribute], document, attribute)
        if document["path"] == "/about/":
            contact = soup.find(string=lambda value: value and value.strip() == "Contact")
            if contact:
                contact.parent["id"] = "contact"
        return str(soup)

    def cards(self, documents):
        cards = []
        for doc in documents:
            excerpt = BeautifulSoup(doc["excerpt"], "html.parser").get_text(" ", strip=True)
            if not excerpt:
                excerpt = BeautifulSoup(doc["content"], "html.parser").get_text(" ", strip=True)
            excerpt = excerpt.split("[")[0].strip()
            if len(excerpt) > 180:
                excerpt = excerpt[:177].rsplit(" ", 1)[0] + "..."
            date = datetime.fromisoformat(doc["date"]).strftime("%d %b %Y").lstrip("0")
            cards.append(f'''<article class="card"><p class="eyebrow"><time datetime="{doc["date"][:10]}">{date}</time></p>
<h3><a href="{ESC(self.local(doc["path"]))}">{ESC(doc["title"])}</a></h3><p>{ESC(excerpt)}</p>
<span class="card-arrow" aria-hidden="true">&rarr;</span></article>''')
        return '<div class="cards">' + "".join(cards) + "</div>"

    def write(self, route, title, body, description=""):
        nav = [("/about/", "About"), ("/people/", "People"), ("/research/", "Research"),
               ("/blog/", "News & events"), ("/fgea-cop/", "FGEA CoP"), ("/ea4ai-2026/", "EA4AI 2026")]
        links = "".join(f'<a href="{self.local(p)}"{" aria-current=page" if p == route else ""}>{label}</a>' for p, label in nav)
        canonical = f'<link rel="canonical" href="{ESC(self.site_url + self.local(route))}">' if self.site_url else ""
        page = f'''<!doctype html>
<html lang="en-AU"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ESC(title)} | DigiSAS Lab</title><meta name="description" content="{ESC(description[:250])}">
{canonical}<link rel="stylesheet" href="{self.local('/assets/site.css')}">
<link rel="alternate" type="application/rss+xml" title="DigiSAS Lab news" href="{self.local('/feed/index.xml')}">
<script src="{self.local('/assets/site.js')}" defer></script></head><body>
<a class="skip" href="#main">Skip to content</a>
<div class="university-bar">University of Technology Sydney <span>Software and societal systems</span></div>
<header class="site-header"><div class="header-inner"><a class="brand" href="{self.local('/')}"><span class="brand-mark" aria-hidden="true">D<span>:</span></span><span>DigiSAS Lab<small>Research &amp; innovation</small></span></a>
<details class="navigation"><summary>Menu</summary><nav aria-label="Main navigation">{links}<a href="{self.local('/search/')}">Search</a></nav></details></div></header>
<main id="main">{body}</main>
<footer><div class="footer-grid"><div><a class="footer-brand" href="{self.local('/')}">DigiSAS Lab</a><p>Research and innovation in software<br>and societal systems.</p><p>School of Computer Science<br>University of Technology Sydney</p></div>
<div><h2>Explore</h2><a href="{self.local('/research/')}">Research &amp; innovation</a><a href="{self.local('/people/')}">Our people</a><a href="{self.local('/pages/')}">All pages &amp; archives</a><a href="{self.local('/feed/index.xml')}">News feed</a></div>
<div><h2>Connect</h2><a href="{self.local('/about/#contact')}">Contact the lab</a><a href="{self.local('/fgea-cop/')}">FGEA Community of Practice</a><a href="{self.local('/fgea-cop/contact/')}">Contact / join FGEA CoP</a></div></div>
<div class="footer-bottom">DigiSAS Research &amp; Innovation Lab <span>Thinking. Architecting. Building. Evaluating.</span></div></footer></body></html>'''
        destination = self.output / route.lstrip("/") / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(page)
        self.generated.add(route)

    def build(self):
        self.output.mkdir(exist_ok=True)
        shutil.copytree(ROOT / "assets" / "web", self.output / "assets", dirs_exist_ok=True)
        for path, media in self.media_by_path.items():
            public_path = media["path"].removeprefix("/assets/imported")
            target = self.output / public_path.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / media["path"].lstrip("/"), target)
        for doc in self.documents:
            rendered = self.content(doc)
            eyebrow = "Research & innovation" if doc["kind"] == "page" else datetime.fromisoformat(doc["date"]).strftime("%d %B %Y").lstrip("0")
            intro = ""
            if doc["path"] == "/fgea-cop/":
                intro = f'<aside class="notice">Explore the <a href="{self.local("/fgea-cop/")}">FGEA Community of Practice</a> for community information and its event archive.</aside>'
            route = self.route_overrides.get(doc["path"], doc["path"])
            self.write(route, doc["title"],
                       f'<section class="page-heading wrap"><a class="breadcrumb" href="{self.local("/")}">DigiSAS Lab</a><p class="eyebrow">{ESC(eyebrow)}</p><h1>{ESC(doc["title"])}</h1></section>'
                       f'<div class="prose wrap">{intro}{rendered}</div>')
            text = BeautifulSoup(rendered, "html.parser").get_text(" ", strip=True)
            self.search.append({"title": doc["title"], "url": self.local(route), "text": text})
        for route, (title, items) in self.archives.items():
            self.write(route, title, f'<section class="wrap section"><p class="eyebrow">DigiSAS Lab</p><h1>{ESC(title)}</h1>{self.cards(items)}</section>')
        for item in self.attachments:
            target = urllib.parse.unquote(urllib.parse.urlsplit(item["source_url"]).path)
            target = self.media_by_path[target]["path"].removeprefix("/assets/imported")
            self.write(item["path"], item["title"],
                       f'<section class="wrap section"><h1>{ESC(item["title"])}</h1><a class="button" href="{ESC(self.local(target))}">Open or download document &rarr;</a></section>')
        self.write("/", "Research & innovation",
                   f'''<section class="hero"><div class="wrap hero-grid"><div><p class="eyebrow">DigiSAS Research &amp; Innovation Lab</p>
<h1>Intelligent software.<br>Meaningful societal impact.</h1>
<p class="hero-intro">Human-centred research and innovation for safe, resilient and responsible digital ecosystems.</p>
<div class="actions"><a class="button" href="{self.local('/research/')}">Explore our research &rarr;</a><a class="text-link" href="{self.local('/about/')}">Meet the lab &rarr;</a></div></div>
<div class="hero-panel"><p class="eyebrow">Our approach</p><ol><li><span>01</span>Thinking</li><li><span>02</span>Architecting</li><li><span>03</span>Building</li><li><span>04</span>Evaluating</li></ol><p>Software and societal systems.<br>Research grounded in practice.</p></div></div></section>
<section class="wrap section"><div class="section-top"><div><p class="eyebrow">From the lab</p><h2>Latest news &amp; events</h2></div><a href="{self.local('/blog/')}">All news &rarr;</a></div>{self.cards(self.posts[:6])}</section>
<section class="community-strip"><div class="wrap"><p class="eyebrow">Connecting research and practice</p><h2>A community for what comes next.</h2><p>Explore the Future Generation Enterprise Architecture Community of Practice, and our enterprise architecture and AI activities.</p><div class="actions"><a class="button" href="{self.local('/fgea-cop/')}">FGEA Community of Practice &rarr;</a><a class="text-link" href="{self.local('/ea4ai-2026/')}">EA4AI 2026 &rarr;</a></div></div></section>''',
                   "DigiSAS Lab at the University of Technology Sydney: research and innovation in human-centred software and societal systems.")
        page_links = "".join(f'<li><a href="{ESC(self.local(d["path"]))}">{ESC(d["title"])}</a></li>'
                             for d in sorted(self.documents, key=lambda x: x["title"]) if d["kind"] == "page")
        self.write("/pages/", "All pages & archives", f'<section class="wrap section"><h1>All pages &amp; archives</h1><p>Research, people, services, programmes and historical event pages.</p><ul class="page-list">{page_links}</ul><a href="{self.local("/blog/")}">Browse all news &amp; events &rarr;</a></section>')
        self.write("/search/", "Search", '''<section class="wrap section"><p class="eyebrow">Explore the lab</p><h1>Search</h1><form id="site-search" role="search"><label for="query">Search pages, people, research and news</label><div class="search-box"><input type="search" id="query" name="q" required><button class="button" type="submit">Search</button></div></form><p id="search-status" role="status"></p><ul id="search-results" class="search-results"></ul><noscript>Search requires JavaScript. Browse the site using the navigation or the all-pages link in the footer.</noscript></section>''')
        (self.output / "search-index.json").write_text(json.dumps(self.search, ensure_ascii=False))
        self.feed()
        self.sitemap()
        (self.output / ".nojekyll").touch()
        self.write("/404/", "Page not found", f'<section class="wrap section"><h1>Page not found</h1><p>Try <a href="{self.local("/search/")}">searching the site</a> or <a href="{self.local("/pages/")}">browsing all pages</a>.</p></section>')
        shutil.copyfile(self.output / "404" / "index.html", self.output / "404.html")
        for key in self.issues:
            self.issues[key] = list({json.dumps(item, sort_keys=True): item for item in self.issues[key]}.values())
        (ROOT / "migration" / "build-report.json").write_text(json.dumps({
            "base_path": self.base, "site_url": self.site_url, "content_documents": len(self.documents),
            "generated_routes": len(self.generated), **self.issues,
        }, ensure_ascii=False, indent=2) + "\n")
        print(f"Built {len(self.documents)} content documents and {len(self.generated)} routes into {self.output}")
        print(f"Missing source images: {len(self.issues['missing_images'])}; unresolved source links: {len(self.issues['unresolved_local_links'])}")

    def feed(self):
        root = ET.Element("rss", version="2.0")
        channel = ET.SubElement(root, "channel")
        for key, value in (("title", "DigiSAS Lab"), ("link", self.site_url + self.local("/")),
                           ("description", "DigiSAS Lab news and events")):
            ET.SubElement(channel, key).text = value
        for post in self.posts:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = post["title"]
            ET.SubElement(item, "link").text = self.site_url + self.local(post["path"])
            ET.SubElement(item, "guid", isPermaLink="false").text = f"digisas-wordpress-{post['id']}"
            ET.SubElement(item, "description").text = BeautifulSoup(post["excerpt"], "html.parser").get_text(" ", strip=True)
        target = self.output / "feed" / "index.xml"
        target.parent.mkdir(exist_ok=True)
        ET.indent(root)
        target.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
        # Pages serves directory indexes as HTML, so the feed links target the XML file.
        self.write("/feed/", "News feed", f'<section class="wrap section"><h1>News feed</h1><a href="{self.local("/feed/index.xml")}">Subscribe to the RSS feed</a></section>')

    def sitemap(self):
        if not self.site_url:
            return
        root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for route in sorted(self.generated):
            entry = ET.SubElement(root, "url")
            ET.SubElement(entry, "loc").text = self.site_url + self.local(route)
        (self.output / "sitemap.xml").write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
        (self.output / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {self.site_url}{self.local('/sitemap.xml')}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-path", default="")
    parser.add_argument("--site-url", default="")
    parser.add_argument("--output")
    args = parser.parse_args()
    Builder(args.base_path, args.site_url, args.output).build()
