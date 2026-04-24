#!/usr/bin/env python3
import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import feedparser
import re
from email.utils import formatdate
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"

MAX_TOTAL_ITEMS = 75
MAX_PER_SOURCE = 5
REQUEST_TIMEOUT = 20

#KEYWORDS = ["anchorage", "alaska", "fairbanks", "juneau"]
KEYWORDS = []

WEATHER_ENABLED = True
WEATHER_LAT = 61.2181
WEATHER_LON = -149.9003
WEATHER_TAG = "weather"
WEATHER_SOURCE_NAME = "NWS Anchorage"
WEATHER_PERIODS = 3

SOURCES = [
    {
        "enabled": True,
        "name": "ABC Business",
        "url": "https://abcnews.go.com/abcnews/businessheadlines",
        "tag": "business",
        "use_keywords": True,
    },
    {
        "enabled": True,
        "name": "BBC World",
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "tag": "world",
        "use_keywords": True,
    },
    {
    "name": "Reddit News",
    "url": "https://www.reddit.com/r/news/new/.rss",
    "category": "world",
    "tag": "reddit",
    },
    {
        "enabled": True,
        "name": "BBC Front Page",
        "url": "http://feeds.bbci.co.uk/news/rss.xml",
        "tag": "top",
        "use_keywords": True,
    },
    {
        "enabled": True,
        "name": "NPR News Now",
        "url": "https://feeds.npr.org/500005/podcast.xml",
        "tag": "top",
        "use_keywords": True,
    },
]


def now_rfc2822() -> str:
    return formatdate(time.time(), usegmt=True)


def load_existing():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AnchorageFeedBot/1.0)"
        },
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read()


def fetch_xml(url: str) -> bytes:
    return fetch_bytes(url)


def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AnchorageFeedBot/1.0)",
            "Accept": "application/geo+json, application/json"
        },
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def import_weather():
    items = []

    points_url = f"https://api.weather.gov/points/{WEATHER_LAT},{WEATHER_LON}"
    points_data = fetch_json(points_url)

    forecast_url = points_data["properties"]["forecast"]
    forecast_data = fetch_json(forecast_url)

    periods = forecast_data["properties"]["periods"][:WEATHER_PERIODS]

    for period in periods:
        title = f"Anchorage Weather: {period['name']}"

        detail_parts = [
            f"{period.get('temperature')}°{period.get('temperatureUnit', '')}",
            period.get("windSpeed", ""),
            period.get("windDirection", ""),
            period.get("shortForecast", "")
        ]
        detail_line = " | ".join(part for part in detail_parts if part)

        description = detail_line
        detailed = period.get("detailedForecast", "").strip()
        if detailed:
            description += f"<br><br>{detailed}"

        period_slug = period["name"].lower().replace(" ", "-")
        period_link = f"https://akpulselive.com/weather.html#{period_slug}"

        items.append({
            "title": title,
            "link": period_link,
            "description": description,
            "pubDate": now_rfc2822(),
            "source": WEATHER_SOURCE_NAME,
            "category": WEATHER_TAG
        })

    return items


def text_of(node, tag_name: str) -> str:
    child = node.find(tag_name)
    return (child.text or "").strip() if child is not None and child.text else ""


def first_nonempty(*values) -> str:
    for value in values:
        if value and str(value).strip():
            return str(value).strip()
    return ""


def parse_rss(xml_bytes: bytes, source_name: str, tag: str, use_keywords: bool = True):
    root = ET.fromstring(xml_bytes)
    items = []

    for item in root.findall("./channel/item"):
        title = text_of(item, "title")
        link = text_of(item, "link")
        description = text_of(item, "description")
        pub_date = text_of(item, "pubDate") or now_rfc2822()

        if not title or not link:
            continue

        if use_keywords and KEYWORDS:
            text_blob = (title + " " + description).lower()
            if not any(k in text_blob for k in KEYWORDS):
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


def parse_atom(xml_bytes: bytes, source_name: str, tag: str, use_keywords: bool = True):
    root = ET.fromstring(xml_bytes)
    items = []

    ns = {"atom": "http://www.w3.org/2005/Atom"}

    for entry in root.findall(".//atom:entry", ns):
        title = first_nonempty(text_of(entry, "{http://www.w3.org/2005/Atom}title"))
        summary = first_nonempty(
            text_of(entry, "{http://www.w3.org/2005/Atom}summary"),
            text_of(entry, "{http://www.w3.org/2005/Atom}content"),
        )

        link = ""
        for link_node in entry.findall("{http://www.w3.org/2005/Atom}link"):
            href = link_node.attrib.get("href", "").strip()
            rel = link_node.attrib.get("rel", "alternate").strip()
            if href and rel in ("alternate", ""):
                link = href
                break
        if not link:
            link = text_of(entry, "{http://www.w3.org/2005/Atom}id")

        pub_date = first_nonempty(
            text_of(entry, "{http://www.w3.org/2005/Atom}updated"),
            text_of(entry, "{http://www.w3.org/2005/Atom}published"),
            now_rfc2822(),
        )

        if not title or not link:
            continue

        if use_keywords and KEYWORDS:
            text_blob = (title + " " + summary).lower()
            if not any(k in text_blob for k in KEYWORDS):
                continue

        items.append({
            "title": f"{source_name}: {title}",
            "link": link,
            "description": summary,
            "pubDate": pub_date,
            "source": source_name,
            "category": tag
        })

    return items[:MAX_PER_SOURCE]
    
def fetch_feed(url):
    headers = {
        "User-Agent": "AKPulseLive/1.0 (by akpulselive.com)"
    }

    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()

    return feedparser.parse(r.content)

def clean_title(title):
    title = re.sub(r'^\[.*?\]\s*', '', title)
    return title.strip()

def parse_feed(xml_bytes: bytes, source_name: str, tag: str, use_keywords: bool = True):
    xml_text = xml_bytes.decode("utf-8", errors="replace")

    # Try RSS first, then Atom.
    try:
        return parse_rss(xml_text.encode("utf-8"), source_name, tag, use_keywords)
    except Exception:
        pass

    try:
        return parse_atom(xml_text.encode("utf-8"), source_name, tag, use_keywords)
    except Exception:
        pass

    raise ValueError(f"Could not parse feed from {source_name}")


def merge_items(existing, imported):
    seen = set()
    merged = []

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
        if not source.get("enabled", True):
            print(f"Skipped disabled source: {source['name']}")
            continue
        print("Fetching:", source["name"], source["url"])
        feed = fetch_feed(source["url"])
        print("Entries found:", len(feed.entries))

        try:
            xml_bytes = fetch_xml(source["url"])
            parsed = parse_feed(
                xml_bytes,
                source["name"],
                source["tag"],
                source.get("use_keywords", True),
            )
            imported.extend(parsed)
            print(f"Imported {len(parsed)} items from {source['name']}")
        except Exception as e:
            print(f"Failed to import from {source['name']}: {e}")

    if WEATHER_ENABLED:
        try:
            weather_items = import_weather()
            imported = weather_items + imported
            print(f"Imported {len(weather_items)} weather items")
        except Exception as e:
            print(f"Failed to import weather: {e}")

    merged = merge_items(existing, imported)
    DATA_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {DATA_FILE} with {len(merged)} items")


if __name__ == "__main__":
    main()
