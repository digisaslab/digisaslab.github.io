#!/usr/bin/env python3
"""Build DigiSAS at the root and the existing FGEA community below /fgea-cop/."""

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "_site"


def command(*args, env=None):
    subprocess.run(args, cwd=ROOT, check=True, env=env)


def build(base="", origin="https://digisaslab.github.io"):
    base = "/" + base.strip("/") if base.strip("/") else ""
    origin = origin.rstrip("/")
    if OUTPUT.is_symlink():
        raise ValueError("The generated _site directory must not be a symlink")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    community = OUTPUT / "fgea-cop"
    command("bundle", "exec", "ruby", "_scripts/validate_content.rb")
    with tempfile.TemporaryDirectory(prefix="digisas-jekyll-") as directory:
        config = Path(directory) / "config.yml"
        config.write_text(json.dumps({"url": origin, "lab_baseurl": base}))
        command("bundle", "exec", "jekyll", "build", "--strict_front_matter", "--trace",
                "--config", f"_config.yml,{config}", "--baseurl", base + "/fgea-cop",
                "--destination", str(community),
                env={**os.environ, "JEKYLL_ENV": "production"})
    command(sys.executable, str(ROOT / "digisas/scripts/build.py"),
            "--base-path", base, "--site-url", origin, "--output", str(OUTPUT))
    redirects = []
    for source in sorted(community.rglob("*.html")):
        relative = source.relative_to(community)
        target = OUTPUT / relative
        if target.exists() or relative.name == "404.html":
            continue
        route = "/" + relative.as_posix()
        if route.endswith("/index.html"):
            route = route.removesuffix("index.html")
        destination = base + "/fgea-cop" + route
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            '<!doctype html><html lang="en-AU"><head><meta charset="utf-8">'
            f'<title>FGEA Community of Practice</title><link rel="canonical" href="{html.escape(origin + destination)}">'
            f'<meta http-equiv="refresh" content="0;url={html.escape(destination)}">'
            f'</head><body><p>Continue to <a href="{html.escape(destination)}">FGEA Community of Practice</a>.</p></body></html>'
        )
        redirects.append({"from": base + route, "to": destination})
    for source in (community / "assets").rglob("*"):
        if source.is_file():
            target = OUTPUT / "assets" / source.relative_to(community / "assets")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and target.read_bytes() != source.read_bytes():
                raise ValueError(f"Legacy media conflicts with a lab asset: {target}")
            shutil.copyfile(source, target)
    # Keep existing FGEA RSS subscriptions working at their old XML address.
    shutil.copyfile(community / "feed.xml", OUTPUT / "feed.xml")
    search_path = OUTPUT / "search-index.json"
    search = json.loads(search_path.read_text())
    for source in sorted(community.rglob("*.html")):
        soup = BeautifulSoup(source.read_text(), "html.parser")
        main = soup.find("main")
        if not main or not main.find("h1"):
            continue
        route = "/" + source.relative_to(OUTPUT).as_posix()
        if route.endswith("/index.html"):
            route = route.removesuffix("index.html")
        search.append({
            "title": main.h1.get_text(" ", strip=True),
            "url": base + route,
            "text": main.get_text(" ", strip=True),
        })
    search_path.write_text(json.dumps(search, ensure_ascii=False))
    sitemap = ET.parse(OUTPUT / "sitemap.xml")
    locations = {entry.text for entry in sitemap.iter() if entry.tag.endswith("loc")}
    for entry in ET.parse(community / "sitemap.xml").getroot():
        location = next((node.text for node in entry if node.tag.endswith("loc")), None)
        if location and location not in locations:
            sitemap.getroot().append(entry)
            locations.add(location)
    sitemap.write(OUTPUT / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    command(sys.executable, str(ROOT / "digisas/scripts/validate.py"),
            "--base-path", base, "--output", str(OUTPUT))
    assert "Intelligent software" in (OUTPUT / "index.html").read_text()
    assert "Architecture for public good" in (community / "index.html").read_text()
    assert not (OUTPUT / "digisas").exists(), "Source snapshots must not be published"
    (ROOT / "digisas/migration/shared-build.json").write_text(json.dumps({
        "root_site": origin + base + "/",
        "community_site": origin + base + "/fgea-cop/",
        "legacy_redirects": redirects,
        "search_documents": len(search),
        "sitemap_urls": len(locations),
        "intentional_route_changes": {
            "/": "DigiSAS is now the primary homepage; FGEA moved to /fgea-cop/.",
            "/about/": "The lab's About page is primary; FGEA About moved to /fgea-cop/about/.",
        },
    }, indent=2) + "\n")
    print(f"Shared site ready: DigiSAS {base or '/'}, FGEA {base}/fgea-cop/; {len(redirects)} legacy redirects.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-path", default="")
    parser.add_argument("--site-url", default="https://digisaslab.github.io")
    args = parser.parse_args()
    build(args.base_path, args.site_url)
