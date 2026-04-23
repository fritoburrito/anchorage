#!/usr/bin/env python3
import json
import hashlib
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"
FEED_FILE = ROOT / "feed.xml"
INDEX_FILE = ROOT / "index.html"

SITE_URL = "https://fritoburrito.github.io/anchorage/"
FEED_URL = SITE_URL + "feed.xml"
FEED_TITLE = "Anchorage Custom Feed"
FEED_DESCRIPTION = "A custom RSS feed published from GitHub Pages."
LANGUAGE = "en-us"
MAX_ITEMS = 25


def cdata(text: str) -> str:
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def load_items():
    items = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    def sort_key(item):
        return parsedate_to_datetime(item["pubDate"])

    items.sort(key=sort_key, reverse=True)
    return items[:MAX_ITEMS]


def category_label(category: str) -> str:
    labels = {
        "weather": "Weather",
        "top": "Top News",
        "world": "World",
        "business": "Business",
        "local": "Local",
    }
    return labels.get(category, category.title() if category else "General")


def build_feed(items):
    last_build = items[0]["pubDate"] if items else "Wed, 22 Apr 2026 17:00:00 GMT"
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        '  <channel>',
        f'    <title>{escape(FEED_TITLE)}</title>',
        f'    <link>{escape(SITE_URL)}</link>',
        f'    <description>{escape(FEED_DESCRIPTION)}</description>',
        f'    <language>{LANGUAGE}</language>',
        f'    <lastBuildDate>{escape(last_build)}</lastBuildDate>',
    ]

    for item in items:
        guid = item.get("guid") or hashlib.sha1(item["link"].encode()).hexdigest()
        title = item["title"]
        category = item.get("category", "")

        lines.extend([
            '    <item>',
            f'      <title>{escape(title)}</title>',
            f'      <link>{escape(item["link"])}</link>',
            f'      <guid isPermaLink="false">{escape(guid)}</guid>',
            f'      <pubDate>{escape(item["pubDate"])}</pubDate>',
            f'      <description>{cdata(item.get("description", ""))}</description>',
        ])

        if category:
            lines.append(f'      <category>{escape(category)}</category>')

        lines.append('    </item>')

    lines.extend(['  </channel>', '</rss>', ''])
    return "\n".join(lines)


def build_index(items):
    rows = []
    for item in items[:15]:
        title = escape(item["title"])
        link = escape(item["link"])
        pub = escape(item["pubDate"])
        category = item.get("category", "")
        category_text = escape(category_label(category))
        category_class = escape(category if category else "general")

        rows.append(
            f'''<li class="feed-item">
      <div class="item-top">
        <span class="cat-badge cat-{category_class}">{category_text}</span>
        <small>{pub}</small>
      </div>
      <div class="item-title"><a href="{link}">{title}</a></div>
    </li>'''
        )

    item_html = "\n".join("        " + row for row in rows) if rows else '        <li>No items yet.</li>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(FEED_TITLE)}</title>
  <link rel="alternate" type="application/rss+xml" title="{escape(FEED_TITLE)}" href="feed.xml">
  <style>
    body {{
      font-family: Arial, sans-serif;
      max-width: 860px;
      margin: 40px auto;
      padding: 0 16px;
      line-height: 1.5;
      background: #111827;
      color: #f3f4f6;
    }}

    a {{
      color: #93c5fd;
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    code {{
      background: #1f2937;
      padding: 2px 6px;
      border-radius: 4px;
      color: #e5e7eb;
    }}

    .feed-list {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}

    .feed-item {{
      background: #1f2937;
      border: 1px solid #374151;
      border-radius: 12px;
      padding: 14px 16px;
      margin: 0 0 14px 0;
    }}

    .item-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }}

    .item-title {{
      font-size: 1.02rem;
      font-weight: 600;
    }}

    .cat-badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }}

    .cat-weather {{
      background: #1d4ed8;
      color: #eff6ff;
    }}

    .cat-top {{
      background: #b91c1c;
      color: #fef2f2;
    }}

    .cat-world {{
      background: #7c3aed;
      color: #f5f3ff;
    }}

    .cat-business {{
      background: #047857;
      color: #ecfdf5;
    }}

    .cat-local {{
      background: #c2410c;
      color: #fff7ed;
    }}

    .cat-general {{
      background: #4b5563;
      color: #f9fafb;
    }}
  </style>
</head>
<body>
  <h1>{escape(FEED_TITLE)}</h1>
  <p>{escape(FEED_DESCRIPTION)}</p>
  <p><a href="feed.xml">Open the RSS feed</a></p>
  <p>Feed URL: <code>{escape(FEED_URL)}</code></p>
  <h2>Latest items</h2>
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
    print(f"Wrote {FEED_FILE}")
    print(f"Wrote {INDEX_FILE}")


if __name__ == "__main__":
    main()
