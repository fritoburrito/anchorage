#!/usr/bin/env python3
"""
generate_feed.py for AK Pulse Live

Drop this file into:
  scripts/generate_feed.py

It reads:
  data/feed_items.json

And generates:
  feed.xml
  index.html
  sitemap.xml
  news-sitemap.xml
  robots.txt

Designed for GitHub Pages + Google Search Console + Google News / Publisher Center.
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


SITE_URL = "https://akpulselive.com"
SITE_NAME = "AK Pulse Live"
SITE_DESCRIPTION = "Fresh Alaska headlines, weather, community updates, and curated news feeds."
SITE_LANGUAGE = "en"
SITE_AUTHOR = "AK Pulse Live"

DATA_FILE = Path("data/feed_items.json")

FEED_FILE = Path("feed.xml")
INDEX_FILE = Path("index.html")
SITEMAP_FILE = Path("sitemap.xml")
NEWS_SITEMAP_FILE = Path("news-sitemap.xml")
ROBOTS_FILE = Path("robots.txt")

MAX_FEED_ITEMS = 50
MAX_INDEX_ITEMS = 50
MAX_SITEMAP_ITEMS = 200
MAX_NEWS_SITEMAP_ITEMS = 1000
NEWS_SITEMAP_MAX_AGE_DAYS = 2


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def xml_escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def clean_text(value: Any, limit: Optional[int] = None) -> str:
    text = str(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def safe_url(url: Any) -> str:
    url = str(url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return ""
    return url


def parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None

    text = str(value).strip()
    if not text:
        return None

    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def w3c_date(dt: Optional[datetime]) -> str:
    if not dt:
        dt = utc_now()
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rss_date(dt: Optional[datetime]) -> str:
    if not dt:
        dt = utc_now()
    return format_datetime(dt.astimezone(timezone.utc), usegmt=True)


def domain_from_url(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host.replace("www.", "")
    except Exception:
        return ""


def load_items() -> List[Dict[str, Any]]:
    if not DATA_FILE.exists():
        print(f"WARNING: {DATA_FILE} not found. Generating empty site.")
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: Could not read {DATA_FILE}: {exc}")
        return []

    if isinstance(data, dict):
        if isinstance(data.get("items"), list):
            data = data["items"]
        else:
            data = list(data.values())

    if not isinstance(data, list):
        print(f"WARNING: {DATA_FILE} did not contain a list of items.")
        return []

    return [x for x in data if isinstance(x, dict)]


def normalize_item(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = clean_text(raw.get("title") or raw.get("headline"), 180)
    link = safe_url(raw.get("link") or raw.get("url"))
    if not title or not link:
        return None

    published = (
        parse_datetime(raw.get("published"))
        or parse_datetime(raw.get("published_at"))
        or parse_datetime(raw.get("pubDate"))
        or parse_datetime(raw.get("date"))
        or parse_datetime(raw.get("timestamp"))
        or utc_now()
    )

    source = clean_text(
        raw.get("source")
        or raw.get("source_name")
        or raw.get("publisher")
        or domain_from_url(link)
        or SITE_NAME,
        80,
    )

    category = clean_text(raw.get("category") or raw.get("tag") or "general", 50)
    summary = clean_text(
        raw.get("summary")
        or raw.get("description")
        or raw.get("excerpt")
        or raw.get("content")
        or title,
        300,
    )

    display_title = title
    if source and source.lower() not in title.lower():
        display_title = f"{title} | {source}"

    return {
        "title": display_title,
        "original_title": title,
        "link": link,
        "summary": summary,
        "source": source,
        "author": clean_text(raw.get("author") or source or SITE_AUTHOR, 80),
        "category": category,
        "published_dt": published,
        "published": w3c_date(published),
    }


def get_items() -> List[Dict[str, Any]]:
    seen = set()
    items: List[Dict[str, Any]] = []

    for raw in load_items():
        item = normalize_item(raw)
        if not item:
            continue
        link = item["link"]
        if link in seen:
            continue
        seen.add(link)
        items.append(item)

    items.sort(key=lambda x: x.get("published_dt") or utc_now(), reverse=True)
    return items


def build_feed(items: List[Dict[str, Any]]) -> str:
    now = utc_now()

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{xml_escape(SITE_NAME)}</title>",
        f"    <link>{xml_escape(SITE_URL)}/</link>",
        f"    <description>{xml_escape(SITE_DESCRIPTION)}</description>",
        f"    <language>{xml_escape(SITE_LANGUAGE)}</language>",
        f"    <lastBuildDate>{rss_date(now)}</lastBuildDate>",
        f'    <atom:link href="{xml_escape(SITE_URL)}/feed.xml" rel="self" type="application/rss+xml" />',
    ]

    for item in items[:MAX_FEED_ITEMS]:
        description = item["summary"]
        if item["source"]:
            description += f" Source: {item['source']}."

        lines += [
            "    <item>",
            f"      <title>{xml_escape(item['title'])}</title>",
            f"      <link>{xml_escape(item['link'])}</link>",
            f"      <guid isPermaLink=\"true\">{xml_escape(item['link'])}</guid>",
            f"      <description>{xml_escape(description)}</description>",
            f"      <category>{xml_escape(item['category'])}</category>",
            f"      <source url=\"{xml_escape(item['link'])}\">{xml_escape(item['source'])}</source>",
            f"      <pubDate>{rss_date(item['published_dt'])}</pubDate>",
            "    </item>",
        ]

    lines += ["  </channel>", "</rss>", ""]
    return "\n".join(lines)


def build_sitemap(items: List[Dict[str, Any]]) -> str:
    now = w3c_date(utc_now())

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "  <url>",
        f"    <loc>{xml_escape(SITE_URL)}/</loc>",
        f"    <lastmod>{now}</lastmod>",
        "    <changefreq>hourly</changefreq>",
        "    <priority>1.0</priority>",
        "  </url>",
        "  <url>",
        f"    <loc>{xml_escape(SITE_URL)}/feed.xml</loc>",
        f"    <lastmod>{now}</lastmod>",
        "    <changefreq>hourly</changefreq>",
        "    <priority>0.9</priority>",
        "  </url>",
        "  <url>",
        f"    <loc>{xml_escape(SITE_URL)}/news-sitemap.xml</loc>",
        f"    <lastmod>{now}</lastmod>",
        "    <changefreq>hourly</changefreq>",
        "    <priority>0.8</priority>",
        "  </url>",
    ]

    for item in items[:MAX_SITEMAP_ITEMS]:
        lines += [
            "  <url>",
            f"    <loc>{xml_escape(item['link'])}</loc>",
            f"    <lastmod>{w3c_date(item.get('published_dt'))}</lastmod>",
            "    <changefreq>daily</changefreq>",
            "    <priority>0.6</priority>",
            "  </url>",
        ]

    lines += ["</urlset>", ""]
    return "\n".join(lines)


def build_news_sitemap(items: List[Dict[str, Any]]) -> str:
    now = utc_now()
    cutoff = now - timedelta(days=NEWS_SITEMAP_MAX_AGE_DAYS)

    recent_items = []
    for item in items:
        pub_dt = item.get("published_dt") or now
        if pub_dt >= cutoff:
            recent_items.append(item)

    recent_items = recent_items[:MAX_NEWS_SITEMAP_ITEMS]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">',
    ]

    for item in recent_items:
        title = item.get("original_title") or item.get("title") or SITE_NAME
        pub_dt = item.get("published_dt") or now

        lines += [
            "  <url>",
            f"    <loc>{xml_escape(item['link'])}</loc>",
            "    <news:news>",
            "      <news:publication>",
            f"        <news:name>{xml_escape(SITE_NAME)}</news:name>",
            f"        <news:language>{xml_escape(SITE_LANGUAGE)}</news:language>",
            "      </news:publication>",
            f"      <news:publication_date>{xml_escape(w3c_date(pub_dt))}</news:publication_date>",
            f"      <news:title>{xml_escape(title)}</news:title>",
            "    </news:news>",
            "  </url>",
        ]

    lines += ["</urlset>", ""]
    return "\n".join(lines)


def build_robots() -> str:
    return "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {SITE_URL}/sitemap.xml",
            f"Sitemap: {SITE_URL}/news-sitemap.xml",
            "",
        ]
    )


def category_class(category: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-")
    return slug or "general"


def build_index(items: List[Dict[str, Any]]) -> str:
    now = utc_now()
    latest = items[:MAX_INDEX_ITEMS]

    cards = []
    for item in latest:
        title = clean_text(item.get("original_title") or item["title"], 180)
        link = item["link"]
        summary = clean_text(item["summary"], 240)
        source = clean_text(item["source"], 80)
        category = clean_text(item["category"], 40)
        pub_dt = item.get("published_dt") or now

        cards.append(f"""
      <article class="story-card category-{category_class(category)}" itemscope itemtype="https://schema.org/NewsArticle">
        <div class="story-meta">
          <span class="category">{html.escape(category.title())}</span>
          <span class="source">{html.escape(source)}</span>
          <time datetime="{html.escape(w3c_date(pub_dt))}" itemprop="datePublished">{html.escape(pub_dt.strftime("%b %d, %Y %H:%M UTC"))}</time>
        </div>
        <h2 itemprop="headline">
          <a href="{html.escape(link)}" target="_blank" rel="noopener noreferrer" itemprop="url">{html.escape(title)}</a>
        </h2>
        <p itemprop="description">{html.escape(summary)}</p>
      </article>""")

    cards_html = "\n".join(cards) if cards else "<p>No stories found yet. Check back soon.</p>"

    org_schema = {
        "@context": "https://schema.org",
        "@type": "NewsMediaOrganization",
        "name": SITE_NAME,
        "url": SITE_URL,
        "logo": f"{SITE_URL}/logo.png",
        "description": SITE_DESCRIPTION,
    }

    webpage_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": SITE_NAME,
        "url": SITE_URL,
        "description": SITE_DESCRIPTION,
        "isPartOf": {
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": SITE_URL,
        },
    }

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />

  <title>{html.escape(SITE_NAME)} | Alaska News, Weather & Community Updates</title>
  <meta name="description" content="{html.escape(SITE_DESCRIPTION)}" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{html.escape(SITE_URL)}/" />

  <link rel="alternate" type="application/rss+xml" title="{html.escape(SITE_NAME)} RSS Feed" href="{html.escape(SITE_URL)}/feed.xml" />
  <link rel="sitemap" type="application/xml" title="Sitemap" href="{html.escape(SITE_URL)}/sitemap.xml" />

  <meta property="og:title" content="{html.escape(SITE_NAME)}" />
  <meta property="og:description" content="{html.escape(SITE_DESCRIPTION)}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{html.escape(SITE_URL)}/" />

  <script type="application/ld+json">
{json.dumps(org_schema, indent=2)}
  </script>

  <script type="application/ld+json">
{json.dumps(webpage_schema, indent=2)}
  </script>

  <style>
    :root {{
      --bg: #0b0f1a;
      --panel: #121827;
      --panel-soft: #172033;
      --text: #f4f7fb;
      --muted: #9aa3b2;
      --blue: #00c6ff;
      --green: #7bffb2;
      --red: #ff4757;
      --border: rgba(255,255,255,0.08);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(0,198,255,0.18), transparent 35%),
        radial-gradient(circle at top right, rgba(123,255,178,0.12), transparent 30%),
        var(--bg);
      color: var(--text);
    }}

    header {{
      padding: 32px 20px 22px;
      border-bottom: 1px solid var(--border);
      background: rgba(11,15,26,0.88);
      position: sticky;
      top: 0;
      backdrop-filter: blur(12px);
      z-index: 10;
    }}

    .wrap {{
      max-width: 1100px;
      margin: 0 auto;
    }}

    h1 {{
      margin: 0;
      font-size: clamp(2rem, 5vw, 4rem);
      letter-spacing: -0.05em;
      line-height: 0.95;
    }}

    .rocket {{
      display: block;
      margin-top: 8px;
      color: var(--green);
      font-size: 1rem;
      letter-spacing: 0.04em;
    }}

    .tagline {{
      color: var(--muted);
      margin: 12px 0 0;
      max-width: 720px;
      font-size: 1.05rem;
    }}

    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }}

    nav a {{
      color: var(--text);
      text-decoration: none;
      border: 1px solid var(--border);
      background: var(--panel-soft);
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 0.9rem;
    }}

    main {{ padding: 26px 20px 60px; }}

    .status-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      justify-content: space-between;
      align-items: center;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 14px 16px;
      margin-bottom: 18px;
      color: var(--muted);
    }}

    .status-bar strong {{ color: var(--green); }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }}

    .story-card {{
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 18px;
      box-shadow: 0 12px 34px rgba(0,0,0,0.22);
    }}

    .story-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-bottom: 10px;
      color: var(--muted);
      font-size: 0.78rem;
    }}

    .category {{
      color: #061018;
      background: var(--blue);
      border-radius: 999px;
      padding: 4px 8px;
      font-weight: bold;
    }}

    .source {{ color: var(--green); }}

    h2 {{
      margin: 0 0 10px;
      font-size: 1.1rem;
      line-height: 1.25;
    }}

    h2 a {{
      color: var(--text);
      text-decoration: none;
    }}

    h2 a:hover {{
      color: var(--blue);
      text-decoration: underline;
    }}

    p {{
      color: var(--muted);
      line-height: 1.45;
    }}

    footer {{
      border-top: 1px solid var(--border);
      padding: 24px 20px;
      color: var(--muted);
      background: rgba(0,0,0,0.18);
    }}

    footer a {{ color: var(--green); }}

    .about {{
      margin-top: 26px;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
    }}
  </style>
</head>

<body>
  <header>
    <div class="wrap">
      <h1>{html.escape(SITE_NAME)}</h1>
      <span class="rocket">🚀 Open AK Pulse Live</span>
      <p class="tagline">{html.escape(SITE_DESCRIPTION)}</p>

      <nav aria-label="Site sections">
        <a href="#latest">Latest</a>
        <a href="{html.escape(SITE_URL)}/feed.xml">RSS Feed</a>
        <a href="{html.escape(SITE_URL)}/sitemap.xml">Sitemap</a>
        <a href="{html.escape(SITE_URL)}/news-sitemap.xml">News Sitemap</a>
      </nav>
    </div>
  </header>

  <main>
    <div class="wrap">
      <section class="status-bar" aria-label="Feed status">
        <div><strong>Live feed updated:</strong> {html.escape(now.strftime("%B %d, %Y %H:%M UTC"))}</div>
        <div>{len(latest)} latest stories displayed</div>
      </section>

      <section id="latest" class="grid" aria-label="Latest news stories">
{cards_html}
      </section>

      <section class="about" id="about">
        <h2>About AK Pulse Live</h2>
        <p>
          AK Pulse Live is an Alaska-focused news and information hub that curates fresh headlines,
          weather, community updates, and public-interest stories from multiple sources. Links point
          readers to the original publishers.
        </p>
      </section>
    </div>
  </main>

  <footer>
    <div class="wrap">
      <p>
        © {now.year} {html.escape(SITE_NAME)} ·
        <a href="{html.escape(SITE_URL)}/feed.xml">RSS</a> ·
        <a href="{html.escape(SITE_URL)}/sitemap.xml">Sitemap</a> ·
        <a href="{html.escape(SITE_URL)}/news-sitemap.xml">News sitemap</a>
      </p>
    </div>
  </footer>
</body>
</html>
"""


def main() -> None:
    items = get_items()

    FEED_FILE.write_text(build_feed(items), encoding="utf-8")
    INDEX_FILE.write_text(build_index(items), encoding="utf-8")
    SITEMAP_FILE.write_text(build_sitemap(items), encoding="utf-8")
    NEWS_SITEMAP_FILE.write_text(build_news_sitemap(items), encoding="utf-8")
    ROBOTS_FILE.write_text(build_robots(), encoding="utf-8")

    print(f"Generated {FEED_FILE} with {min(len(items), MAX_FEED_ITEMS)} items")
    print(f"Generated {INDEX_FILE}")
    print(f"Generated {SITEMAP_FILE}")
    print(f"Generated {NEWS_SITEMAP_FILE}")
    print(f"Generated {ROBOTS_FILE}")


if __name__ == "__main__":
    main()
