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
WEATHER_FILE = ROOT / "weather.html"

SITE_URL = "https://akpulselive.com/"
FEED_URL = SITE_URL + "feed.xml"
FEED_TITLE = "AK Live Pulse"
FEED_DESCRIPTION = "A custom WEB/RSS feed published by a Bot."
LANGUAGE = "en-us"
MAX_ITEMS = 75
INDEX_ITEMS = 50


def cdata(text: str) -> str:
    return "<![CDATA[" + str(text).replace("]]>", "]]]]><![CDATA[>") + "]]>"


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


def is_breaking(item) -> bool:
    text = f"{item.get('title', '')} {item.get('description', '')} {item.get('summary', '')}".lower()
    breaking_terms = ["breaking", "urgent", "alert", "developing", "just in"]
    return any(term in text for term in breaking_terms)


def is_local(item) -> bool:
    text = f"{item.get('title', '')} {item.get('description', '')} {item.get('summary', '')} {item.get('source', '')}".lower()
    local_terms = [
        "alaska",
        "anchorage",
        "fairbanks",
        "juneau",
        "mat-su",
        "matsu",
        "wasilla",
        "palmer",
        "kenai",
        "soldotna",
        "seward",
        "homer",
        "bethel",
        "nome",
        "kodiak",
        "sitka",
        "ketchikan",
        "eagle river",
        "chugiak",
        "girdwood",
        "talkeetna",
        "valdez",
        "cordova",
        "dillingham",
        "utqiagvik",
        "barrow",
        "north pole",
        "tok",
        "delta junction",
        "alaskan",
    ]
    return any(term in text for term in local_terms)


def effective_category(item) -> str:
    if is_breaking(item):
        return "breaking"

    original_category = (item.get("category") or item.get("tag") or "general").lower()

    # Weather keeps its own category. Reddit keeps its own category.
    # Other Alaska/local items become Local for clearer display.
    if is_local(item) and original_category not in ("weather", "reddit"):
        return "local"

    return original_category


def category_label(category: str) -> str:
    labels = {
        "breaking": "Breaking",
        "weather": "Weather",
        "top": "Top News",
        "world": "World",
        "business": "Business",
        "local": "Local",
        "reddit": "Reddit",
        "general": "General",
    }
    return labels.get(category, category.title() if category else "General")


def weather_icon(text: str) -> str:
    t = text.lower()
    if "snow" in t:
        return "❄️"
    if "rain" in t or "showers" in t:
        return "🌧️"
    if "thunder" in t or "storm" in t:
        return "⛈️"
    if "cloud" in t or "overcast" in t:
        return "☁️"
    if "sun" in t or "clear" in t:
        return "☀️"
    if "wind" in t:
        return "💨"
    if "fog" in t:
        return "🌫️"
    return "🌡️"


def make_slug(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "forecast"


def load_items():
    if not DATA_FILE.exists():
        return []

    items = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    def sort_key(item):
        dt = parse_item_date(item)
        timestamp = dt.timestamp() if dt else 0

        # Priority:
        # 1. Breaking items
        # 2. Alaska/local items
        # 3. Everything else by newest
        breaking_rank = 0 if is_breaking(item) else 1
        local_rank = 0 if is_local(item) else 1

        return (breaking_rank, local_rank, -timestamp)

    items.sort(key=sort_key)
    return items[:MAX_ITEMS]


def build_feed(items):
    last_build = items[0].get("pubDate", "") if items else "Fri, 01 May 2026 00:00:00 GMT"

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
        title = item.get("title", "Untitled")
        link = item.get("link") or item.get("url") or SITE_URL
        desc = item.get("description") or item.get("summary") or ""
        pub = item.get("pubDate", "")
        category = effective_category(item)
        guid = item.get("guid") or hashlib.sha1(link.encode("utf-8")).hexdigest()

        lines.extend([
            '    <item>',
            f'      <title>{escape(title)}</title>',
            f'      <link>{escape(link)}</link>',
            f'      <guid isPermaLink="false">{escape(guid)}</guid>',
            f'      <pubDate>{escape(pub)}</pubDate>',
            f'      <description>{cdata(desc)}</description>',
            f'      <category>{escape(category)}</category>',
            '    </item>',
        ])

    lines.extend(['  </channel>', '</rss>', ''])
    return "\n".join(lines)


def build_index(items):
    rows = []

    for item in items[:INDEX_ITEMS]:
       
        raw_title = item.get("title", "Untitled")

        # Add 🚀 icon for NASA items
        if item.get("tag") in ("nasa", "nasa-jpl", "nasa-apod"):
            raw_title = "🚀 " + raw_title

        title = escape(raw_title)
        link = escape(item.get("link") or item.get("url") or "#")
        pub = escape(item.get("pubDate", ""))
        category = effective_category(item)
        category_text = escape(category_label(category))
        category_class = escape(category)

        rows.append(
            f'''<li class="feed-item">
      <div class="item-top">
        <span class="cat-badge cat-{category_class}">{category_text}</span>
        <small>{pub}</small>
      </div>
      <div class="item-title"><a href="{link}">{title}</a></div>
    </li>'''
        )

    item_html = "\n".join("        " + row for row in rows) if rows else "        <li>No items yet.</li>"

    top_item = items[0] if items else None

    if top_item:
        top_title = escape(top_item.get("title", "Untitled"))
        top_link = escape(top_item.get("link") or top_item.get("url") or "#")
        top_pub = escape(top_item.get("pubDate", ""))
        top_category = escape(category_label(effective_category(top_item)))

        top_story_html = f'''
  <section class="top-story">
    <div class="top-story-label">🔥 Top Story</div>
    <h2><a href="{top_link}">{top_title}</a></h2>
    <div class="top-story-meta">{top_category} • {top_pub}</div>
  </section>
'''
    else:
        top_story_html = ""

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(FEED_TITLE)}</title>
  <link rel="icon" type="image/png" href="favicon.png">
  <link rel="alternate" type="application/rss+xml" title="{escape(FEED_TITLE)}" href="feed.xml">
  <style>
    .site-header {{
      text-align: center;
      margin: 12px 0 18px 0;
    }}

    .header-inner {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 18px;
      flex-wrap: wrap;
    }}

    .site-logo {{
      width: 120px;
      max-width: 45vw;
      height: auto;
      display: block;
      filter: drop-shadow(0 0 8px rgba(0,198,255,0.35));
    }}

    .site-clock-wrap {{
      background: #1f2937;
      border: 1px solid #374151;
      border-radius: 12px;
      padding: 8px 12px;
      min-width: 130px;
    }}

    .site-clock-label {{
      font-size: 0.68rem;
      color: #9aa3b2;
      letter-spacing: 0.08em;
      font-weight: 700;
    }}

    .site-clock {{
      font-size: 1.2rem;
      font-weight: 800;
      color: #7bffb2;
      line-height: 1.2;
    }}

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

    .feed-links {{
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 14px;
      margin: 12px 0 18px 0;
      flex-wrap: wrap;
    }}

    .feed-links a {{
      font-weight: 600;
    }}

    .feed-links a:first-child {{
      padding: 10px 14px;
      background: #1f2937;
      border: 1px solid #374151;
      border-radius: 8px;
    }}

    .main-link {{
      display: inline-block;
      padding: 12px 18px;
      background: linear-gradient(135deg, #00c6ff, #7bffb2);
      color: #000;
      border-radius: 10px;
      font-weight: 800;
      font-size: 1rem;
      text-decoration: none;
      margin: 0;
      box-shadow: 0 4px 14px rgba(0,198,255,0.35);
      transition: all 0.2s ease;
    }}

    .main-link:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 18px rgba(123,255,178,0.45);
      text-decoration: none;
      color: #000;
    }}

    .top-story {{
      background: linear-gradient(135deg, rgba(220,38,38,0.35), rgba(31,41,55,0.95));
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: 14px;
      padding: 18px;
      margin: 18px 0 22px 0;
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    }}

    .top-story-label {{
      display: inline-block;
      background: #dc2626;
      color: #fff;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 800;
      text-transform: uppercase;
    }}

    .top-story h2 {{
      margin: 12px 0 8px 0;
      line-height: 1.25;
    }}

    .top-story-meta {{
      color: #9ca3af;
      font-size: 0.88rem;
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

    .cat-breaking {{
      background: #dc2626;
      color: #ffffff;
      animation: breakingPulse 1s infinite;
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

    .cat-science {{
      background: #2563eb;
      color: #eff6ff;
    }}

    .cat-reddit {{
      background: #ff4500;
      color: #fff7ed;
    }}

    .cat-general {{
      background: #4b5563;
      color: #f9fafb;
    }}

    @keyframes breakingPulse {{
      0% {{ opacity: 1; }}
      50% {{ opacity: 0.65; }}
      100% {{ opacity: 1; }}
    }}
  </style>
</head>
<body>
  <header class="site-header">
    <div class="header-inner">
      <a href="main.html" title="Open AK Pulse Live full site">
        <img src="assets/akpulse-logo.png" class="site-logo" alt="AK Pulse Live logo">
      </a>
      <div class="site-clock-wrap">
        <div class="site-clock-label">ANCHORAGE TIME</div>
        <div class="site-clock" id="clock">--:--</div>
      </div>
    </div>
  </header>

  <h1>Anchorage Custom Feed</h1>
  <p>{escape(FEED_DESCRIPTION)}</p>

<div class="feed-links">
  <a href="feed.xml">📰 Open RSS Feed</a>
  <a href="main.html" class="main-link">🚀 Open AK Pulse Live</a>
  <a href="about.html">About</a>
</div>

  <p>Feed URL: <code>akpulselive.com/feed.xml</code></p>

{top_story_html}

  <h2>Latest items</h2>
  <ul class="feed-list">
{item_html}
  </ul>

  <script>
    function updateClock() {{
      const now = new Date();
      const time = now.toLocaleTimeString([], {{
        hour: "2-digit",
        minute: "2-digit"
      }});

      const clock = document.getElementById("clock");
      if (clock) clock.textContent = time;
    }}

    updateClock();
    setInterval(updateClock, 1000);
  </script>
</body>
</html>
'''


def build_weather_page(items):
    weather_items = [item for item in items if effective_category(item) == "weather"]

    cards = []

    for item in weather_items:
        title_raw = item.get("title", "Forecast")
        desc = item.get("description") or item.get("summary") or ""
        slug = make_slug(title_raw.split(":")[-1].strip())
        icon = weather_icon(title_raw + " " + desc)

        cards.append(f'''
      <section class="weather-card" id="{escape(slug)}">
        <h2>{icon} {escape(title_raw)}</h2>
        <div class="weather-desc">{desc}</div>
      </section>
''')

    cards_html = "\n".join(cards) if cards else "<p>No weather forecast available.</p>"

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Anchorage Weather Forecast</title>
  <link rel="icon" type="image/png" href="favicon.png">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      font-family: Arial, sans-serif;
      max-width: 860px;
      margin: 40px auto;
      padding: 0 16px;
      background: #111827;
      color: #f3f4f6;
      line-height: 1.6;
    }}

    a {{
      color: #93c5fd;
    }}

    .weather-card {{
      background: #1f2937;
      border: 1px solid #374151;
      border-radius: 14px;
      padding: 18px;
      margin-bottom: 16px;
    }}

    .weather-card h2 {{
      color: #bfdbfe;
      margin-top: 0;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 1.2rem;
    }}

    .weather-desc {{
      font-size: 1rem;
    }}
  </style>
</head>
<body>
  <h1>Anchorage Weather Forecast</h1>
  <p><a href="index.html">← Back to feed</a> • <a href="main.html">AK Pulse Live</a></p>
  {cards_html}
</body>
</html>
'''


def main():
    items = load_items()

    FEED_FILE.write_text(build_feed(items), encoding="utf-8")
    INDEX_FILE.write_text(build_index(items), encoding="utf-8")
    WEATHER_FILE.write_text(build_weather_page(items), encoding="utf-8")

    print(f"Wrote {FEED_FILE}")
    print(f"Wrote {INDEX_FILE}")
    print(f"Wrote {WEATHER_FILE}")


if __name__ == "__main__":
    main()
