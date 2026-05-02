#!/usr/bin/env python3

import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from email.utils import formatdate, parsedate_to_datetime
from pathlib import Path

import feedparser


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "feed_items.json"

TIMEOUT = 25
MAX_TOTAL_ITEMS = 75
MAX_PER_SOURCE = 8

WEATHER_ENABLED = True
WEATHER_LAT = 61.2181
WEATHER_LON = -149.9003
WEATHER_PERIODS = 1
WEATHER_SOURCE_NAME = "NWS Anchorage"

SOURCES = [
    {
        "name": "BBC News",
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "category": "world",
        "tag": "bbc",
        "enabled": True,
    },
    {
        "name": "ABC News",
        "url": "https://abcnews.go.com/abcnews/topstories",
        "category": "world",
        "tag": "abc",
        "enabled": True,
    },
    {
        "name": "ABC Business",
        "url": "https://abcnews.go.com/abcnews/businessheadlines",
        "category": "business",
        "tag": "business",
        "enabled": True,
    },
    {
        "name": "NPR News",
        "url": "https://feeds.npr.org/1001/rss.xml",
        "category": "world",
        "tag": "npr",
        "enabled": True,
    },

    # Reddit is disabled because GitHub Actions is getting blocked by Reddit.
    {
        "name": "Reddit Alaska RSS",
        "url": "https://www.reddit.com/r/alaska/new/.rss",
        "category": "reddit",
        "tag": "reddit",
        "enabled": False,
    },
    {
        "name": "Reddit News RSS",
        "url": "https://www.reddit.com/r/news/new/.rss",
        "category": "reddit",
        "tag": "reddit",
        "enabled": False,
    },
]


# Reddit JSON is also disabled because GitHub Actions appears blocked by Reddit.
REDDIT_JSON_SOURCES = []


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clean_title(title):
    if not title:
        return "Untitled"
    title = re.sub(r"^\[.*?\]\s*", "", title)
    return title.strip()


def parse_date(entry):
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if value:
            try:
                dt = parsedate_to_datetime(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass

    return now_iso()


def fetch(url, accept="application/rss+xml, application/xml;q=0.9, */*;q=0.8"):
    headers = {
        "User-Agent": "AKPulseLive/1.0 (https://akpulselive.com)",
        "Accept": accept,
    }

    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "ignore")


def fetch_json(url):
    raw = fetch(url, accept="application/json, */*;q=0.8")
    return json.loads(raw)


def load_existing_items():
    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

        if isinstance(data, dict) and "items" in data:
            return data["items"]

    except Exception as e:
        print("Could not read existing feed_items.json:", e)

    return []


def save_items(items):
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(items)} items to {DATA_FILE}")


def import_rss_sources(seen_links):
    new_items = []

    for source in SOURCES:
        if not source.get("enabled", True):
            print(f"Skipped disabled source: {source['name']}")
            continue

        print("Fetching:", source["name"], source["url"])

        try:
            raw = fetch(source["url"])
            feed = feedparser.parse(raw)
        except Exception as e:
            print(f"FETCH ERROR for {source['name']}: {e}")
            continue

        entries = getattr(feed, "entries", [])
        print("Entries found:", len(entries))

        added_for_source = 0

        for entry in entries:
            if added_for_source >= MAX_PER_SOURCE:
                break

            title = clean_title(entry.get("title", "Untitled"))
            link = entry.get("link", "")

            if not link or link in seen_links:
                continue

            summary = entry.get("summary", "")
            published = parse_date(entry)

            try:
                pub_timestamp = datetime.fromisoformat(published).timestamp()
            except Exception:
                pub_timestamp = time.time()

            item = {
                "title": title,
                "link": link,
                "url": link,
                "summary": summary,
                "description": summary,
                "source": source["name"],
                "category": source.get("category", "news"),
                "tag": source.get("tag", ""),
                "pubDate": formatdate(pub_timestamp, usegmt=True),
                "published": published,
                "created_utc": published,
            }

            new_items.append(item)
            seen_links.add(link)
            added_for_source += 1

            print("ADDED:", source["name"], "-", title)

    return new_items


def import_reddit_json_sources(seen_links):
    # Currently disabled because Reddit blocks GitHub Actions.
    new_items = []

    for source in REDDIT_JSON_SOURCES:
        if not source.get("enabled", True):
            print(f"Skipped disabled Reddit JSON source: {source['name']}")
            continue

        print("Fetching Reddit JSON:", source["name"], source["url"])

        try:
            data = fetch_json(source["url"])
        except Exception as e:
            print(f"REDDIT JSON ERROR for {source['name']}: {e}")
            continue

        posts = data.get("data", {}).get("children", [])
        print("Reddit posts found:", len(posts))

        added_for_source = 0

        for post in posts:
            if added_for_source >= MAX_PER_SOURCE:
                break

            p = post.get("data", {})
            title = clean_title(p.get("title", "Untitled"))
            permalink = p.get("permalink", "")
            created = p.get("created_utc")

            if not permalink or not created:
                continue

            link = "https://www.reddit.com" + permalink

            if link in seen_links:
                continue

            summary = p.get("selftext", "")
            published = datetime.fromtimestamp(created, timezone.utc).isoformat()

            item = {
                "title": title,
                "link": link,
                "url": link,
                "summary": summary,
                "description": summary,
                "source": source["name"],
                "category": source.get("category", "reddit"),
                "tag": source.get("tag", "reddit"),
                "pubDate": formatdate(created, usegmt=True),
                "published": published,
                "created_utc": published,
            }

            new_items.append(item)
            seen_links.add(link)
            added_for_source += 1

            print("ADDED:", source["name"], "-", title)

    return new_items


def import_weather():
    if not WEATHER_ENABLED:
        return []

    headers = {
        "User-Agent": "AKPulseLive/1.0 (https://akpulselive.com)",
        "Accept": "application/geo+json, application/json",
    }

    points_url = f"https://api.weather.gov/points/{WEATHER_LAT},{WEATHER_LON}"
    req = urllib.request.Request(points_url, headers=headers)

    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        points_data = json.loads(r.read().decode("utf-8"))

    forecast_url = points_data["properties"]["forecast"]
    req = urllib.request.Request(forecast_url, headers=headers)

    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        forecast_data = json.loads(r.read().decode("utf-8"))

    weather_items = []
    now = datetime.now(timezone.utc)

    for period in forecast_data["properties"]["periods"][:WEATHER_PERIODS]:
        name = period.get("name", "Forecast")
        temp = period.get("temperature")
        unit = period.get("temperatureUnit", "F")
        wind_speed = period.get("windSpeed", "")
        wind_dir = period.get("windDirection", "")
        short = period.get("shortForecast", "")
        detailed = period.get("detailedForecast", "")

        description = f"{temp}°{unit} | {wind_speed} {wind_dir} | {short}<br><br>{detailed}"

        period_slug = name.lower().replace(" ", "-")
        period_link = f"https://akpulselive.com/weather.html#{period_slug}"

        weather_items.append({
            "title": f"Anchorage Weather: {name}",
            "link": period_link,
            "url": period_link,
            "summary": description,
            "description": description,
            "source": WEATHER_SOURCE_NAME,
            "category": "weather",
            "tag": "weather",
            "pubDate": formatdate(now.timestamp(), usegmt=True),
            "published": now.isoformat(),
            "created_utc": now.isoformat(),
        })

    print(f"Imported {len(weather_items)} weather items")
    return weather_items


def main():
    existing_items = load_existing_items()
    seen_links = set()

    for item in existing_items:
        link = item.get("link") or item.get("url")
        if link:
            seen_links.add(link)

    new_items = []

    new_items.extend(import_rss_sources(seen_links))
    new_items.extend(import_reddit_json_sources(seen_links))

    weather_items = []
    try:
        weather_items = import_weather()
    except Exception as e:
        print("WEATHER ERROR:", e)

    combined = weather_items + new_items + existing_items

    combined.sort(
        key=lambda item: item.get("published", item.get("created_utc", "")),
        reverse=True,
    )

    combined = combined[:MAX_TOTAL_ITEMS]

    save_items(combined)


if __name__ == "__main__":
    main()
