#!/usr/bin/env python3
"""Add a new RSS item to data/feed_items.json and rebuild feed.xml/index.html.

Example:
python scripts/add_item.py \
  --title "My new item" \
  --link "https://example.com/post" \
  --guid "post-123" \
  --description "A short summary" \
  --pubdate "Wed, 22 Apr 2026 18:30:00 GMT"
"""

import argparse
import json
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"
GENERATOR = ROOT / "scripts" / "generate_feed.py"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--link", required=True)
    parser.add_argument("--guid", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--pubdate", required=True, help="RFC 2822 date, example: Wed, 22 Apr 2026 18:30:00 GMT")
    args = parser.parse_args()

    items = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items.insert(0, {
        "title": args.title,
        "link": args.link,
        "guid": args.guid,
        "description": args.description,
        "pubDate": args.pubdate,
    })
    DATA_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    run(["python3", str(GENERATOR)], check=True)
    print("Added item and rebuilt feed.xml/index.html")


if __name__ == "__main__":
    main()
