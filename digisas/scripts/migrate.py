#!/usr/bin/env python3
"""Refresh an offline, editable snapshot of the public DigiSAS WordPress site."""

import argparse
import concurrent.futures
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image, ImageOps
import pillow_heif

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://www.digisaslab.org"
HOSTS = {"www.digisaslab.org", "digisaslab.org"}
pillow_heif.register_heif_opener()


def fetch(url):
    parts = urllib.parse.urlsplit(url)
    url = urllib.parse.urlunsplit((
        parts.scheme, parts.netloc,
        urllib.parse.quote(urllib.parse.unquote(parts.path), safe="/:@"),
        urllib.parse.quote(urllib.parse.unquote(parts.query), safe="=&,:/?+"),
        "",
    ))
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "DigiSAS-static-migration/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read(), response.headers
        except (OSError, urllib.error.URLError):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def collection(kind):
    records, page = [], 1
    while True:
        body, headers = fetch(f"{SOURCE}/wp-json/wp/v2/{kind}?per_page=100&page={page}")
        records.extend(json.loads(body))
        if page >= int(headers.get("X-WP-TotalPages", 1)):
            return records
        page += 1


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def media_path(url):
    parsed = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(parsed.path)
    if parsed.hostname not in HOSTS or not path.startswith("/wp-content/"):
        raise ValueError(f"Not a local WordPress asset: {url}")
    if ".." in Path(path).parts:
        raise ValueError(f"Unsafe asset path: {url}")
    return ROOT / "assets" / "imported" / path.lstrip("/")


def srcset_sources(value):
    return [re.sub(r"\s+[0-9.]+[wx]$", "", part.strip(), flags=re.ASCII)
            for part in value.split(",") if part.strip()]


def download_media(url, reuse=False):
    target = media_path(url)
    suffix = target.suffix.lower()
    convert = suffix in {".heic", ".heif", ".tif", ".tiff"}
    if convert:
        target = target.with_suffix(target.suffix + ".jpg")
    source_hash = None
    if not reuse or not target.exists():
        body, _ = fetch(url)
        source_hash = hashlib.sha256(body).hexdigest()
        target.parent.mkdir(parents=True, exist_ok=True)
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tif", ".tiff"}:
            from io import BytesIO
            with Image.open(BytesIO(body)) as original:
                image = ImageOps.exif_transpose(original)
                clean = Image.new(image.mode, image.size)
                clean.paste(image)
                if convert:
                    clean.convert("RGB").save(target, "JPEG", quality=90)
                elif original.format == "JPEG":
                    clean.convert("RGB").save(target, "JPEG", quality=92)
                else:
                    clean.save(target, format=original.format)
        else:
            target.write_bytes(body)
    return {
        "source": url,
        "path": "/" + target.relative_to(ROOT).as_posix(),
        "bytes": target.stat().st_size,
        "source_sha256": source_hash,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }


def main(reuse_media=False):
    print("Fetching public pages, posts, taxonomies and media metadata...", flush=True)
    pages, posts = collection("pages"), collection("posts")
    categories, tags = collection("categories"), collection("tags")
    media = collection("media")
    media_by_id = {item["id"]: item for item in media}
    media_by_link = {urllib.parse.urlsplit(item["link"]).path: item for item in media}
    attachments = {}
    documents, asset_urls, features = [], set(), []
    homepage, _ = fetch(SOURCE + "/")
    homepage_soup = BeautifulSoup(homepage, "html.parser")
    menus = [
        {"label": link.get_text(" ", strip=True), "url": link.get("href")}
        for link in homepage_soup.select("nav a[href]")
    ]
    for kind, records in (("page", pages), ("post", posts)):
        for record in records:
            content = record["content"]["rendered"]
            soup = BeautifulSoup(content, "html.parser")
            for node in soup.select("[style]"):
                for candidate in re.findall(r"url\(([^)]+)\)", node["style"]):
                    absolute = urllib.parse.urljoin(record["link"], candidate.strip(" '\""))
                    parsed = urllib.parse.urlsplit(absolute)
                    if parsed.hostname in HOSTS and parsed.path.startswith("/wp-content/"):
                        asset_urls.add(urllib.parse.urlunsplit(parsed._replace(query="", fragment="")))
            for tag in soup.find_all(True):
                for attribute in ("src", "href", "poster", "data-src"):
                    value = tag.get(attribute, "")
                    if not isinstance(value, str) or not value:
                        continue
                    absolute = urllib.parse.urljoin(record["link"], value)
                    parsed = urllib.parse.urlsplit(absolute)
                    if parsed.hostname in HOSTS and parsed.path.startswith("/wp-content/"):
                        asset_urls.add(urllib.parse.urlunsplit(parsed._replace(query="", fragment="")))
                    elif parsed.hostname in HOSTS and parsed.path in media_by_link:
                        attachment = media_by_link[parsed.path]
                        asset_urls.add(attachment["source_url"])
                        attachments[parsed.path] = {
                            "path": parsed.path, "source_url": attachment["source_url"],
                            "title": BeautifulSoup(attachment["title"]["rendered"], "html.parser").get_text(),
                        }
                for candidate in srcset_sources(tag.get("srcset", "")):
                    absolute = urllib.parse.urljoin(record["link"], candidate)
                    parsed = urllib.parse.urlsplit(absolute)
                    if parsed.hostname in HOSTS and parsed.path.startswith("/wp-content/"):
                        asset_urls.add(urllib.parse.urlunsplit(parsed._replace(query="", fragment="")))
            dynamic = soup.find_all(["form", "iframe", "script", "audio", "video"])
            shortcodes = re.findall(r"\[(?!/?caption\b|/?gallery\b)[a-zA-Z][^\]]*\]", content)
            if dynamic or shortcodes or record.get("comment_status") == "open":
                features.append({
                    "url": record["link"],
                    "embeds": [{"tag": tag.name, "src": tag.get("src"), "action": tag.get("action")}
                               for tag in dynamic],
                    "shortcodes": shortcodes,
                    "comments_open": record.get("comment_status") == "open",
                })
            featured = media_by_id.get(record.get("featured_media"))
            if featured:
                asset_urls.add(featured["source_url"])
            documents.append({
                "id": record["id"], "kind": kind, "slug": record["slug"],
                "title": BeautifulSoup(record["title"]["rendered"], "html.parser").get_text(),
                "url": record["link"], "path": urllib.parse.urlsplit(record["link"]).path,
                "date": record["date"], "modified": record["modified"],
                "categories": record.get("categories", []), "tags": record.get("tags", []),
                "content": content, "excerpt": record["excerpt"]["rendered"],
                "featured_image": featured["source_url"] if featured else None,
            })
    print(f"Found {len(pages)} pages, {len(posts)} posts and {len(asset_urls)} referenced assets.", flush=True)
    previous_path = ROOT / "content" / "media.json"
    previous = {m["source"]: m for m in json.loads(previous_path.read_text())} if previous_path.exists() else {}
    assets, failures = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(download_media, url, reuse_media): url for url in sorted(asset_urls)}
        for future in concurrent.futures.as_completed(futures):
            url = futures[future]
            try:
                item = future.result()
                if not item["source_sha256"]:
                    item["source_sha256"] = previous.get(url, {}).get("source_sha256")
                assets.append(item)
            except Exception as error:
                failures.append({"url": url, "error": str(error)})
                print(f"Asset needs attention: {url}: {error}", flush=True)
    save_json(ROOT / "content" / "documents.json", sorted(documents, key=lambda x: x["path"]))
    save_json(ROOT / "content" / "media.json", sorted(assets, key=lambda x: x["source"]))
    save_json(ROOT / "content" / "attachments.json", list(attachments.values()))
    save_json(ROOT / "content" / "taxonomies.json", {
        "categories": [{"id": t["id"], "name": t["name"], "slug": t["slug"], "url": t["link"]} for t in categories],
        "tags": [{"id": t["id"], "name": t["name"], "slug": t["slug"], "url": t["link"]} for t in tags],
    })
    save_json(ROOT / "migration" / "inventory.json", {
        "source": SOURCE, "fetched_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"pages": len(pages), "posts": len(posts), "media_library": len(media),
                   "referenced_assets": len(asset_urls), "downloaded_assets": len(assets)},
        "documents": [{"id": document["id"], "path": document["path"]} for document in documents],
        "navigation": menus, "features_to_review": features, "asset_failures": failures,
    })
    print(f"Saved editable content and {len(assets)} assets; {len(failures)} asset failures.")
    if any("HTTP Error 404" not in failure["error"] for failure in failures):
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse-media", action="store_true", help="Reuse downloaded media instead of refreshing it")
    main(parser.parse_args().reuse_media)
