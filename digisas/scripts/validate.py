#!/usr/bin/env python3
"""Verify migration coverage, local dependencies and rendered HTML links."""

import argparse
import json
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def validate(base_path="", output_path=None):
    base = "/" + base_path.strip("/") if base_path.strip("/") else ""
    output = Path(output_path).resolve() if output_path else ROOT / "_site"
    route_overrides = json.loads((ROOT / "content/site.json").read_text()).get("route_overrides", {})
    documents = json.loads((ROOT / "content/documents.json").read_text())
    inventory = json.loads((ROOT / "migration/inventory.json").read_text())
    media = json.loads((ROOT / "content/media.json").read_text())
    errors = []
    known = json.loads((ROOT / "migration/known-source-issues.json").read_text())
    allowed_missing = {item["url"] for item in known}
    for failure in inventory["asset_failures"]:
        if failure["url"] not in allowed_missing:
            errors.append(f"Unresolved download failure: {failure['url']}")
    report = json.loads((ROOT / "migration/build-report.json").read_text())
    for missing in report["missing_images"]:
        if missing["url"] not in allowed_missing:
            errors.append(f"Unexpected missing source image: {missing['url']}")
    if report["unresolved_local_links"]:
        errors.append("WordPress links remain unresolved in the build report")
    kinds = {kind: sum(d["kind"] == kind for d in documents) for kind in ("page", "post")}
    imported = {(item["id"], item["path"]) for item in inventory["documents"]}
    current = {(item["id"], item["path"]) for item in documents}
    if not imported.issubset(current):
        errors.append("One or more original imported documents or routes were removed")
    for doc in documents:
        route = route_overrides.get(doc["path"], doc["path"])
        destination = output / route.lstrip("/") / "index.html"
        if not destination.exists():
            errors.append(f"Missing original route: {doc['path']}")
            continue
        soup = BeautifulSoup(destination.read_text(), "html.parser")
        if not soup.h1 or soup.h1.get_text() != doc["title"]:
            errors.append(f"Title missing or changed: {doc['path']}")
        if not soup.select_one("main img"):
            errors.append(f"Content page is missing its picture: {doc['path']}")
        source = BeautifulSoup(doc["content"], "html.parser")
        for node in source.find_all(["script", "style", "iframe", "form", "input", "button", "object", "embed"]):
            node.decompose()
        original_words = " ".join(source.get_text(" ", strip=True).split())
        prose = soup.select_one(".prose")
        for node in prose.select(".image-unavailable, .notice"):
            node.decompose()
        actual_words = " ".join(prose.get_text(" ", strip=True).split())
        if original_words not in actual_words:
            errors.append(f"Source text was lost or reordered: {doc['path']}")
    anchors = {}
    parsed_pages = {}
    for path in output.rglob("*.html"):
        soup = BeautifulSoup(path.read_text(), "html.parser")
        parsed_pages[path] = soup
        anchors[path] = {node["id"] for node in soup.select("[id]")}
    for path, soup in parsed_pages.items():
        redirect = soup.find("meta", attrs={"http-equiv": lambda value: value and value.lower() == "refresh"})
        if not redirect and (not soup.title or not soup.find("html", lang=True) or not soup.find("main")):
            errors.append(f"Missing document structure: {path.relative_to(output)}")
        for image in soup.find_all("img"):
            if not image.has_attr("alt"):
                errors.append(f"Image missing alt attribute: {path.relative_to(output)}")
        if soup.select_one("body.layout-event, body.layout-post") and not soup.select_one(".record-image img"):
            errors.append(f"FGEA news/event page is missing its picture: {path.relative_to(output)}")
        for node in soup.find_all(True):
            if any(attr.startswith("on") for attr in node.attrs):
                errors.append(f"Inline event handler: {path.relative_to(output)}")
            for attribute in ("href", "src", "poster"):
                value = node.get(attribute)
                if not value:
                    continue
                parsed = urllib.parse.urlsplit(value)
                if parsed.scheme or parsed.netloc:
                    if attribute in ("src", "poster") and parsed.hostname in {"www.digisaslab.org", "digisaslab.org"}:
                        errors.append(f"WordPress runtime dependency: {value}")
                    continue
                if parsed.path.startswith("/"):
                    if base and not (parsed.path == base or parsed.path.startswith(base + "/")):
                        errors.append(f"Link escapes Pages base path: {value}")
                        continue
                    relative = urllib.parse.unquote(parsed.path[len(base):]).lstrip("/")
                    target = output / relative
                elif not parsed.path:
                    target = path
                else:
                    target = path.parent / urllib.parse.unquote(parsed.path)
                if target.is_dir():
                    target = target / "index.html"
                if not target.exists():
                    errors.append(f"Missing local target in {path.relative_to(output)}: {value}")
                elif parsed.fragment and target in anchors and urllib.parse.unquote(parsed.fragment) not in anchors[target]:
                    errors.append(f"Missing anchor in {path.relative_to(output)}: {value}")
    for item in media:
        path = ROOT / item["path"].lstrip("/")
        if not path.exists():
            errors.append(f"Missing imported asset: {item['path']}")
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            with Image.open(path) as image:
                if image.getexif():
                    errors.append(f"Image retains EXIF: {item['path']}")
            with Image.open(path) as image:
                image.verify()
    ET.parse(output / "feed/index.xml")
    if len(ET.parse(output / "feed/index.xml").findall("channel/item")) != kinds["post"]:
        errors.append("RSS feed does not include every imported post")
    search = json.loads((output / "search-index.json").read_text())
    required_search = {(d["title"], base + route_overrides.get(d["path"], d["path"])) for d in documents}
    if not required_search.issubset({(d["title"], d["url"]) for d in search}):
        errors.append("Search index does not cover every document")
    if (output / "sitemap.xml").exists():
        ET.parse(output / "sitemap.xml")
    for path in (output / "assets/editorial").glob("*.svg"):
        ET.parse(path)
    people = parsed_pages.get(output / "people/index.html")
    sarv = people.select_one("#sarv-girn img") if people else None
    if not sarv or not sarv.get("src", "").endswith("/Sarv.jpg") or sarv.get("alt") != "Sarv Girn":
        errors.append("Sarv Girn's full-size labelled portrait is missing")
    for path, soup in parsed_pages.items():
        for layout, listing in (("post", "news"), ("event", "events")):
            if not soup.select_one(f"body.layout-{layout}"):
                continue
            if layout == "event" and any(
                json.loads(script.string or "{}").get("eventStatus") == "https://schema.org/EventCancelled"
                for script in soup.select('script[type="application/ld+json"]')
            ):
                continue
            listing_page = parsed_pages.get(output / f"fgea-cop/{listing}/index.html")
            route = base + "/" + path.parent.relative_to(output).as_posix() + "/"
            link = listing_page.select_one(f'.card h3 a[href="{route}"]') if listing_page else None
            if not link or link.get_text(" ", strip=True) != soup.h1.get_text(" ", strip=True):
                errors.append(f"FGEA {listing} listing is missing its record card: {route}")
                continue
            card_image = link.find_parent("article", class_="card").find("img")
            detail_image = soup.select_one(".record-image img")
            if not card_image or not detail_image or card_image.get("src") != detail_image.get("src"):
                errors.append(f"FGEA listing picture does not match its record: {route}")
    if errors:
        for error in sorted(set(errors)):
            print("ERROR:", error)
        raise SystemExit(1)
    print(f"Validated {len(documents)} source documents, {len(parsed_pages)} HTML pages, {len(media)} assets, RSS and search.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-path", default="")
    parser.add_argument("--output")
    args = parser.parse_args()
    validate(args.base_path, args.output)
