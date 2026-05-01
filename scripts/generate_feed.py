#!/usr/bin/env python3

import json
from html import escape
from pathlib import Path
from email.utils import formatdate

SITE_URL = "https://akpulselive.com/"
FEED_TITLE = "AK Pulse Live"
FEED_DESCRIPTION = "Alaska news, weather, culture, and headlines."
MAX_ITEMS = 50

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"
FEED_FILE = ROOT / "feed.xml"
INDEX_FILE = ROOT / "index.html"


def load_items():
    if not DATA_FILE.exists():
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data[:MAX_ITEMS]
    except Exception as e:
        print("Error reading feed_items.json:", e)

    return []


def build_feed(items):
    now = formatdate(usegmt=True)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        '<channel>',
        f'  <title>{escape(FEED_TITLE)}</title>',
        f'  <link>{escape(SITE_URL)}</link>',
        f'  <description>{escape(FEED_DESCRIPTION)}</description>',
        f'  <lastBuildDate>{now}</lastBuildDate>',
        '  <language>en-us</language>',
    ]

    for item in items:
        title = escape(item.get("title", "Untitled"))
        link = escape(item.get("link", SITE_URL))
        description = escape(item.get("description", ""))
        pub_date = escape(item.get("pubDate", now))
        category = escape(item.get("category", "general"))
        source = escape(item.get("source", "Unknown Source"))

        lines.extend([
            "  <item>",
            f"    <title>{title}</title>",
            f"    <link>{link}</link>",
            f"    <guid>{link}</guid>",
            f"    <pubDate>{pub_date}</pubDate>",
            f"    <category>{category}</category>",
            f"    <source>{source}</source>",
            f"    <description>{description}</description>",
            "  </item>",
        ])

    lines.extend([
        "</channel>",
        "</rss>",
        "",
    ])

    return "\n".join(lines)


def build_index(items):
    rows = []

    for item in items:
        title = escape(item.get("title", "Untitled"))
        link = escape(item.get("link", "#"))
        category = escape(item.get("category", "general"))
        source = escape(item.get("source", "Unknown Source"))
        pub_date = escape(item.get("pubDate", ""))

        rows.append(f"""
        <article class="card" data-category="{category}">
          <div class="meta">
            <span class="badge">{category}</span>
            <span>{source}</span>
          </div>
          <h2><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h2>
          <p class="date">{pub_date}</p>
        </article>
        """)

    item_html = "\n".join(rows) if rows else "<p>No items yet.</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{escape(FEED_TITLE)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="alternate" type="application/rss+xml" title="{escape(FEED_TITLE)}" href="feed.xml">

  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #0b1020;
      color: #f5f7fb;
    }}

    header {{
      padding: 32px 20px;
      background: linear-gradient(135deg, #0f172a, #123456);
      border-bottom: 1px solid rgba(255,255,255,0.1);
    }}

    .wrap {{
      max-width: 1000px;
      margin: 0 auto;
      padding: 20px;
    }}

    h1 {{
      margin: 0;
      font-size: 2.2rem;
    }}

    .subtitle {{
      color: #cbd5e1;
      margin-top: 8px;
    }}

    .feed-link {{
      display: inline-block;
      margin-top: 16px;
      color: #93c5fd;
      text-decoration: none;
      font-weight: bold;
    }}

    .grid {{
      display: grid;
      gap: 16px;
      margin-top: 20px;
    }}

    .card {{
      background: #111827;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 14px;
      padding: 18px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    }}

    .card h2 {{
      margin: 10px 0;
      font-size: 1.2rem;
    }}

    a {{
      color: #dbeafe;
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    .meta {{
      display: flex;
      gap: 10px;
      align-items: center;
      color: #94a3b8;
      font-size: 0.85rem;
    }}

    .badge {{
      background: #2563eb;
      color: white;
      padding: 4px 8px;
      border-radius: 999px;
      text-transform: uppercase;
      font-size: 0.7rem;
      letter-spacing: 0.04em;
    }}

    .date {{
      color: #94a3b8;
      font-size: 0.85rem;
      margin-bottom: 0;
    }}
  </style>
</head>

<body>
  <header>
    <div class="wrap">
      <h1>{escape(FEED_TITLE)}</h1>
      <div class="subtitle">{escape(FEED_DESCRIPTION)}</div>
      <a class="feed-link" href="feed.xml">RSS Feed</a>
    </div>
  </header>

  <main class="wrap">
    <section class="grid">
      {item_html}
    </section>
  </main>
</body>
</html>
"""


def main():
    items = load_items()

    FEED_FILE.write_text(build_feed(items), encoding="utf-8")
    INDEX_FILE.write_text(build_index(items), encoding="utf-8")

    print(f"Wrote {FEED_FILE}")
    print(f"Wrote {INDEX_FILE}")
    print(f"Items: {len(items)}")


if __name__ == "__main__":
    main()
