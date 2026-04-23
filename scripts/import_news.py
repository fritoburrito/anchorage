#!/usr/bin/env python3
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import formatdate
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"

MAX_TOTAL_ITEMS = 50
MAX_PER_SOURCE = 5
KEYWORDS = ["anchorage", "alaska", "fairbanks", "juneau"]

SOURCES = [
    {
        "name": "ABC Business",
        "url": "https://abcnews.go.com/abcnews/businessheadlines",
        "tag": "business"
    },
    # Add more sources here later
    # {
    #     "name": "Another Source",
    #     "url": "https://example.com/feed.xml",
    #     "tag": "news"
    # },
]


def now_rfc2822() -> str:
    return formatdate(time.time(), usegmt=True)


def load_existing():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def fetch_xml(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AnchorageFeedBot/1.0)"
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def text_of(node, tag_name: str) -> str:
    child = node.find(tag_name)
    return (child.text or "").strip() if child is not None and child.text else ""


def parse_rss(xml_bytes: bytes, source_name: str, tag: str):
    root = ET.fromstring(xml_bytes)
    items = []

    for item in root.findall("./channel/item"):
        title = text_of(item, "title")
        link = text_of(item, "link")
        description = text_of(item, "description")
        pub_date = text_of(item, "pubDate") or now_rfc2822()

        if not title or not link:
            continue

        text_blob = (title + " " + description).lower()
        if KEYWORDS and not any(k in text_blob for k in KEYWORDS):
            continue

        items.append({
            "title": f"{source_name}: {title}",
            "link": link,
            "description": description,
            "pubDate": pub_date,
            "source": source_name,
            "category": tag
        })

    return items[:MAX_PER_SOURCE]

def merge_items(existing, imported):
    seen = set()
    merged = []

    # Keep imported first so newest fetched items float to the top
    for item in imported + existing:
        key = item.get("link", "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)

    return merged[:MAX_TOTAL_ITEMS]


def main():
    existing = load_existing()
    imported = []

    for source in SOURCES:
        try:
            xml_bytes = fetch_xml(source["url"])
            parsed = parse_rss(xml_bytes, source["name"], source["tag"])
            imported.extend(parsed)
            print(f"Imported {len(parsed)} items from {source['name']}")
        except Exception as e:
            print(f"Failed to import from {source['name']}: {e}")

    merged = merge_items(existing, imported)
    DATA_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {DATA_FILE} with {len(merged)} items")


if __name__ == "__main__":
    main()
