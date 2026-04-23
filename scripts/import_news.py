#!/usr/bin/env python3
import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import formatdate
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"

MAX_TOTAL_ITEMS = 50
MAX_PER_SOURCE = 5
KEYWORDS = ["anchorage", "alaska", "fairbanks", "juneau"]

WEATHER_ENABLED = True
WEATHER_LAT = 61.2181
WEATHER_LON = -149.9003
WEATHER_TAG = "weather"
WEATHER_SOURCE_NAME = "NWS Anchorage"
WEATHER_PERIODS = 3

SOURCES = [
    {
        "name": "ABC Business",
        "url": "https://abcnews.go.com/abcnews/businessheadlines",
        "tag": "business"
    },
    # Add more sources here later
    # {
    #     "name": "BBC",
    #     "url": "http://feeds.bbci.co.uk/news/rss.xml",
    #     "tag": "world"
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


def fetch_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AnchorageFeedBot/1.0)",
            "Accept": "application/geo+json, application/json"
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def import_weather():
    items = []

    points_url = f"https://api.weather.gov/points/{WEATHER_LAT},{WEATHER_LON}"
    points_data = fetch_json(points_url)

    forecast_url = points_data["properties"]["forecast"]
    forecast_data = fetch_json(forecast_url)

    periods = forecast_data["properties"]["periods"][:WEATHER_PERIODS]

    for period in periods:
        title = f"{WEATHER_SOURCE_NAME}: {period['name']} forecast"

        detail_parts = [
            f"{period.get('temperature')}°{period.get('temperatureUnit', '')}",
            period.get("windSpeed", ""),
            period.get("windDirection", ""),
            period.get("shortForecast", "")
        ]
        detail_line = " | ".join(part for part in detail_parts if part)

        description = (
            f"{detail_line}<br><br>"
            f"{period.get('detailedForecast', '')}"
        )

        period_link = forecast_url + "#" + period["name"].lower().replace(" ", "-")

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

    if WEATHER_ENABLED:
        try:
            weather_items = import_weather()
            imported.extend(weather_items)
            print(f"Imported {len(weather_items)} weather items")
        except Exception as e:
            print(f"Failed to import weather: {e}")

    merged = merge_items(existing, imported)
    DATA_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {DATA_FILE} with {len(merged)} items")


if __name__ == "__main__":
    main()
