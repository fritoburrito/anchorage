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
MAX_TOTAL_ITEMS = 100
MAX_PER_SOURCE = 8

WEATHER_ENABLED = True
WEATHER_LAT = 61.2181
WEATHER_LON = -149.9003
WEATHER_PERIODS = 1
WEATHER_SOURCE_NAME = "NWS Anchorage"


# ============================================================
# RSS SOURCES
# ============================================================
# Alaska feeds are restored and enabled.
# Reddit remains disabled because GitHub Actions is often blocked by Reddit.

SOURCES = [
    # ----------------------------
    # ALASKA / ANCHORAGE LOCAL
    # ----------------------------
    {
        "name": "Alaska Public Media",
        "url": "https://alaskapublic.org/feed/",
        "category": "alaska",
        "tag": "alaska",
        "enabled": True,
    },
    {
        "name": "Alaska Beacon",
        "url": "https://alaskabeacon.com/feed/",
        "category": "alaska",
        "tag": "alaska-beacon",
        "enabled": True,
    },
    {
    "name": "Anchorage Daily News",
    "url": "https://www.adn.com/rss/",
    "category": "alaska",
    "tag": "alaska",
    "enabled": True,
    },
    {
        "name": "Alaska's News Source",
        "url": "https://www.alaskasnewssource.com/arc/outboundfeeds/rss/",
        "category": "alaska",
        "tag": "ktuu",
        "enabled": True,
    },
    {
        "name": "KTOO News",
        "url": "https://www.ktoo.org/feed/",
        "category": "alaska",
        "tag": "ktoo",
        "enabled": True,
    },
    {
        "name": "Fairbanks Daily News-Miner",
        "url": "https://www.newsminer.com/search/?f=rss&t=article&c=news&l=50&s=start_time&sd=desc",
        "category": "alaska",
        "tag": "fairbanks",
        "enabled": True,
    },

    # ----------------------------
    # NATIONAL / WORLD
    # ----------------------------
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
    # ----------------------------
    # SCIENCE / SPACE
    # ----------------------------
   {
        "name": "NASA Main",
        "url": "https://www.nasa.gov/feed/",
        "category": "science",
        "tag": "nasa",
        "enabled": True,
    },
    {
        "name": "NASA JPL News",
        "url": "https://www.jpl.nasa.gov/feeds/news/",
        "category": "science",
        "tag": "nasa-jpl",
        "enabled": True,
    },
    {
        "name": "NASA APOD",
        "url": "https://apod.nasa.gov/apod.rss",
        "category": "science",
        "tag": "nasa-apod",
        "enabled": True,
    },
    # ----------------------------
    # REDDIT DISABLED
    # ----------------------------
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


REDDIT_JSON_SOURCES = []


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clean_title(title):
    if not title:
        return "Untitled"
    title = re.sub(r"^\[.*?\]\s*", "", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def clean_summary(summary):
    if not summary:
        return ""
    summary = re.sub(r"\s+", " ", str(summary)).strip()
    return summary


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

    # feedparser sometimes stores parsed date tuples
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            try:
                dt = datetime.fromtimestamp(time.mktime(value), timezone.utc)
                return dt.isoformat()
            except Exception:
                pass

    return now_iso()


def fetch(url, accept="application/rss+xml, application/xml;q=0.9, */*;q=0.8"):
    headers = {
        "User-Agent": "AKPulseLive/1.0 (+https://akpulselive.com; contact: akpulselive.com)",
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

        if getattr(feed, "bozo", False):
            print(f"FEED WARNING for {source['name']}: {getattr(feed, 'bozo_exception', '')}")

        added_for_source = 0

        for entry in entries:
            if added_for_source >= MAX_PER_SOURCE:
                break

            title = clean_title(entry.get("title", "Untitled"))
            link = entry.get("link", "")

            if not link or link in seen_links:
                continue

            summary = clean_summary(
                entry.get("summary")
                or entry.get("description")
                or entry.get("subtitle")
                or ""
            )

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

            summary = clean_summary(p.get("selftext", ""))
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
        "User-Agent": "AKPulseLive/1.0 (+https://akpulselive.com)",
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


def sort_key(item):
    value = item.get("published") or item.get("created_utc") or ""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


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

    # Deduplicate again after combining, keeping newest/front-loaded items first.
    deduped = []
    final_seen = set()

    for item in combined:
        link = item.get("link") or item.get("url")
        if not link or link in final_seen:
            continue
        final_seen.add(link)
        deduped.append(item)

    deduped.sort(key=sort_key, reverse=True)
    deduped = deduped[:MAX_TOTAL_ITEMS]

    save_items(deduped)


if __name__ == "__main__":
    main()
