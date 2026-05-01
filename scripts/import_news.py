#!/usr/bin/env python3

import json, time, re, html
import urllib.request, urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"

MAX_TOTAL_ITEMS = 50
MAX_PER_SOURCE = 5
TIMEOUT = 20

# -----------------------------
# FEEDS (MERGED ALASKA SET)
# -----------------------------
SOURCES = [
    # Alaska core
    {"name": "Alaska Public Media","url": "https://alaskapublic.org/feed/","category": "alaska-news"},
    {"name": "Alaska Beacon","url": "https://alaskabeacon.com/feed/","category": "alaska-news"},
    {"name": "KTOO","url": "https://feeds.ktoo.org/KTOONewsUpdate","category": "alaska-news"},
    {"name": "Anchorage Daily News","url": "https://www.adn.com/feed/","category": "alaska-news"},

    # Local
    {"name": "Homer News","url": "https://www.homernews.com/feed/","category": "local"},
    {"name": "Juneau Empire","url": "https://www.juneauempire.com/feed/","category": "local"},

    # Opinion
    {"name": "Alaska Landmine","url": "https://alaskalandmine.com/feed/","category": "opinion"},
    {"name": "Must Read Alaska","url": "https://mustreadalaska.com/feed/","category": "opinion"},

    # Culture
    {"name": "Alaska Native News","url": "https://alaska-native-news.com/feed/","category": "culture"},

    # Weather
    {"name": "NWS Alaska","url": "https://api.weather.gov/alerts/active.atom?area=AK","category": "weather"},

    # Extras
    {"name": "BBC","url": "https://feeds.bbci.co.uk/news/rss.xml","category": "world"},
    {"name": "Reddit Alaska","url": "https://www.reddit.com/r/alaska/new/.rss","category": "reddit"},
]

# -----------------------------
# HELPERS
# -----------------------------
def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()

def parse_date(d):
    try:
        return parsedate_to_datetime(d).astimezone(timezone.utc)
    except:
        return datetime.now(timezone.utc)

def format_date(dt):
    return format_datetime(dt, usegmt=True)

def normalize(title):
    return re.sub(r"\W+", " ", title.lower()).strip()

def auto_category(title, summary, default):
    t = (title + " " + summary).lower()

    if any(w in t for w in ["weather","storm","snow","wind","warning"]): return "weather"
    if any(w in t for w in ["anchorage","wasilla","palmer"]): return "anchorage"
    if any(w in t for w in ["juneau","sitka","ketchikan"]): return "southeast"
    if any(w in t for w in ["fairbanks"]): return "interior"
    if any(w in t for w in ["kenai","homer","soldotna"]): return "kenai"
    if any(w in t for w in ["governor","senate","policy"]): return "politics"

    return default

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "ignore")

# -----------------------------
# PARSER
# -----------------------------
def parse_feed(xml, source):
    root = ET.fromstring(xml)
    items = []

    entries = root.findall(".//item") or root.findall(".//entry")

    for e in entries[:MAX_PER_SOURCE]:
        title = clean((e.findtext("title") or ""))
        link = e.findtext("link") or ""
        summary = clean(e.findtext("description") or e.findtext("summary") or "")
        date = parse_date(e.findtext("pubDate") or e.findtext("updated") or "")

        if not title:
            continue

        cat = auto_category(title, summary, source["category"])

        items.append({
            "title": title,
            "link": link,
            "description": summary,
            "pubDate": format_date(date),
            "category": cat,
            "source": source["name"],
        })

    return items

# -----------------------------
# MAIN
# -----------------------------
def main():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if DATA_FILE.exists():
        existing = json.loads(DATA_FILE.read_text())

    seen = set(normalize(i["title"]) for i in existing)
    new_items = []

    for src in SOURCES:
        print("Fetching:", src["name"])
        try:
            xml = fetch(src["url"])
            items = parse_feed(xml, src)

            for it in items:
                key = normalize(it["title"])
                if key not in seen:
                    seen.add(key)
                    new_items.append(it)

        except Exception as e:
            print("ERROR:", e)

        time.sleep(0.4)

    combined = (new_items + existing)[:MAX_TOTAL_ITEMS]

    DATA_FILE.write_text(json.dumps(combined, indent=2))
    print("Saved", len(combined), "items")

if __name__ == "__main__":
    main()
