#!/usr/bin/env python3
import hashlib
import json
import re
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"
FEED_FILE = ROOT / "feed.xml"
INDEX_FILE = ROOT / "index.html"

SITE_URL = "https://akpulselive.com/"
FEED_TITLE = "AK Live Pulse"
FEED_DESCRIPTION = "A custom WEB/RSS feed published by a Bot."
MAX_ITEMS = 25


def parse_item_date(item):
    for key in ("pubDate", "published", "created_utc"):
        value = item.get(key)
        if not value:
            continue
        try:
            return parsedate_to_datetime(value)
        except Exception:
            pass
    return None


def effective_category(item):
    return (item.get("category") or "general").lower()


def load_items():
    if not DATA_FILE.exists():
        return []

    items = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    def sort_key(item):
        dt = parse_item_date(item)
        return -(dt.timestamp() if dt else 0)

    items.sort(key=sort_key)
    return items[:MAX_ITEMS]


def build_feed(items):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        '  <channel>',
        f'    <title>{escape(FEED_TITLE)}</title>',
        f'    <link>{escape(SITE_URL)}</link>',
        f'    <description>{escape(FEED_DESCRIPTION)}</description>',
    ]

    for item in items:
        title = escape(item.get("title", "Untitled"))
        link = escape(item.get("link") or "#")
        pub = escape(item.get("pubDate", ""))

        lines.extend([
            '    <item>',
            f'      <title>{title}</title>',
            f'      <link>{link}</link>',
            f'      <pubDate>{pub}</pubDate>',
            '    </item>',
        ])

    lines.extend(['  </channel>', '</rss>'])
    return "\n".join(lines)


def build_index(items):
    rows = []

    for item in items:
        title = escape(item.get("title", "Untitled"))
        link = escape(item.get("link") or "#")
        pub = escape(item.get("pubDate", ""))
        category = effective_category(item)

        rows.append(f'''
<li class="feed-item">
  <div class="item-top">
    <span class="cat-badge cat-{category}">{category}</span>
    <small>{pub}</small>
  </div>
  <div class="item-title"><a href="{link}">{title}</a></div>
</li>
''')

    item_html = "\n".join(rows)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(FEED_TITLE)}</title>

<style>
body {{
  font-family: Arial, sans-serif;
  max-width: 860px;
  margin: 40px auto;
  padding: 0 16px;
  background: #111827;
  color: #f3f4f6;
}}

a {{
  color: #93c5fd;
  text-decoration: none;
}}

.feed-links {{
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 14px;
  margin: 12px 0 18px 0;
  flex-wrap: wrap;
}}

.main-link {{
  display: inline-block;
  padding: 10px 16px;
  background: linear-gradient(135deg, #00c6ff, #7bffb2);
  color: #000;
  border-radius: 8px;
  font-weight: 800;
}}

.feed-list {{
  list-style: none;
  padding: 0;
}}

.feed-item {{
  background: #1f2937;
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 10px;
}}

.item-top {{
  display: flex;
  justify-content: space-between;
}}

.cat-badge {{
  background: #374151;
  padding: 3px 8px;
  border-radius: 6px;
}}
</style>
</head>

<body>

<h1>Anchorage Custom Feed</h1>
<p>{escape(FEED_DESCRIPTION)}</p>

<div class="feed-links">
  <a href="feed.xml">📰 Open RSS Feed</a>
  <a href="main.html" class="main-link">🚀 Open AK Pulse Live</a>
</div>

<ul class="feed-list">
{item_html}
</ul>

</body>
</html>
'''


def main():
    items = load_items()
    FEED_FILE.write_text(build_feed(items), encoding="utf-8")
    INDEX_FILE.write_text(build_index(items), encoding="utf-8")


if __name__ == "__main__":
    main()
