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
        
        lines.extend([
            '    <item>',
            f'      <title>{escape(item["title"])}</title>',
            f'      <link>{escape(item["link"])}</link>',
            f'      <guid isPermaLink="false">{escape(guid)}</guid>',
            f'      <pubDate>{escape(item["pubDate"])}</pubDate>',
            f'      <description>{cdata(item.get("description", ""))}</description>',
            '    </item>',
        ])

    lines.extend(['  </channel>', '</rss>', ''])
    return "\n".join(lines)


def build_index(items):
    rows = []
    for item in items[:10]:
        rows.append(
            '<li><a href="{link}">{title}</a> <small>{pub}</small></li>'.format(
                link=escape(item["link"]),
                title=escape(item["title"]),
                pub=escape(item["pubDate"]),
            )
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
    body {{ font-family: Arial, sans-serif; max-width: 760px; margin: 40px auto; padding: 0 16px; line-height: 1.5; }}
    code {{ background: #f3f3f3; padding: 2px 6px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>{escape(FEED_TITLE)}</h1>
  <p>{escape(FEED_DESCRIPTION)}</p>
  <p><a href="feed.xml">Open the RSS feed</a></p>
  <p>Feed URL: <code>{escape(FEED_URL)}</code></p>
  <h2>Latest items</h2>
  <ul>
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
