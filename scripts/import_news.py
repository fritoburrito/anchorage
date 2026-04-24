#!/usr/bin/env python3

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import requests


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "feed_items.json"

MAX_TOTAL_ITEMS = 50
MAX_PER_SOURCE = 8

SOURCES = [
    {
        "name": "Reddit News",
        "url": "https://www.reddit.com/r/news/new/.rss",
        "category": "world",
        "tag": "reddit",
        "enabled": True,
    },
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
]


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

    return datetime.now(timezone.utc).isoformat()


def fetch_feed(url):
    headers = {
        "User-Agent": "AKPulseLive/1.0 (https://akpulselive.com)"
    }

    response = requests.get(url, headers=headers, timeout=25)
    response.raise_for_status()

    return feedparser.parse(response.content)


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


def main():
    existing_items = load_existing_items()
    new_items = []
    seen_links = set()

    for item in existing_items:
        link = item.get("link") or item.get("url")
        if link:
            seen_links.add(link)

    for source in SOURCES:
        if not source.get("enabled", True):
            print(f"Skipped disabled source: {source['name']}")
            continue

        print("Fetching:", source["name"], source["url"])

        try:
            feed = fetch_feed(source["url"])
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

            if not link:
                continue

            if link in seen_links:
                continue

            summary = entry.get("summary", "")
            published = parse_date(entry)

            item = {
                "title": title,
                "link": link,
                "url": link,
                "summary": summary,
                "source": source["name"],
                "category": source.get("category", "news"),
                "tag": source.get("tag", ""),
                "published": published,
                "created_utc": published,
            }

            new_items.append(item)
            seen_links.add(link)
            added_for_source += 1

            print("ADDED:", source["name"], "-", title)

    combined = new_items + existing_items

    combined.sort(
        key=lambda item: item.get("published", item.get("created_utc", "")),
        reverse=True,
    )

    combined = combined[:MAX_TOTAL_ITEMS]

    save_items(combined)


if __name__ == "__main__":
    main()
