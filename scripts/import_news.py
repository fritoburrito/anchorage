#!/usr/bin/env python3

import json
import time
import re
import html
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"

MAX_TOTAL_ITEMS = 60
MAX_PER_SOURCE = 10
MIN_WORLD_ITEMS = 20
TIMEOUT = 20


SOURCES = [
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
        "tag": "alaska",
        "enabled": True,
    },
    {
        "name": "KTOO",
        "url": "https://feeds.ktoo.org/KTOONewsUpdate",
        "category": "alaska",
        "tag": "alaska",
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
        "name": "Homer News",
        "url": "https://www.homernews.com/feed/",
        "category": "local",
        "tag": "alaska",
        "enabled": True,
    },
    {
        "name": "Juneau Empire",
        "url": "https://www.juneauempire.com/feed/",
        "category": "local",
        "tag": "alaska",
        "enabled": True,
    },
    {
        "name": "Alaska Landmine",
        "url": "https://alaskalandmine.com/feed/",
        "home": "https://alaskalandmine.com/",
        "category": "opinion",
        "tag": "alaska",
        "enabled": True,
    },
    {
        "name": "FOX Weather",
        "url": "https://moxie.foxweather.com/google-publisher/weather-news.xml",
        "category": "weather",
        "tag": "weather",
        "enabled": True,
    },
    {
        "name": "Must Read Alaska",
        "url": "https://mustreadalaska.com/feed/",
        "category": "opinion",
        "tag": "alaska",
        "enabled": True,
    },
    {
        "name": "Alaska Native News",
        "url": "https://alaska-native-news.com/feed/",
        "category": "culture",
        "tag": "alaska",
        "enabled": True,
    },
    {
        "name": "NWS Alaska Alerts",
        "url": "https://api.weather.gov/alerts/active.atom?area=AK",
        "category": "weather",
        "tag": "alaska",
        "enabled": True,
    },

    # World/general feeds
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "category": "world",
        "tag": "world",
        "enabled": True,
    },
    {
        "name": "BBC News",
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "category": "world",
        "tag": "world",
        "enabled": True,
    },
    {
        "name": "NPR News",
        "url": "https://feeds.npr.org/1001/rss.xml",
        "category": "world",
        "tag": "world",
        "enabled": True,
    },
]


def source_rank(source):
    category = source.get("category", "").lower()
    tag = source.get("tag", "").lower()
    name = source.get("name", "").lower()

    if category in ["alaska", "alaska-news", "weather"] or tag == "alaska":
        return 100

    if any(word in name for word in ["alaska", "anchorage", "juneau", "homer", "kenai", "ktoo", "adn"]):
        return 90

    return 10


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def parse_date(date_text):
    if not date_text:
        return datetime.now(timezone.utc)

    try:
        dt = parsedate_to_datetime(date_text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    try:
        dt = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def format_date(dt):
    return format_datetime(dt.astimezone(timezone.utc), usegmt=True)


def normalize(title):
    return re.sub(r"\W+", " ", (title or "").lower()).strip()


def is_bad_link(link):
    link = (link or "").lower().split("?")[0]
    bad_extensions = [
        ".cap", ".zip", ".exe", ".dmg", ".pkg", ".tar", ".gz",
        ".7z", ".rar", ".pdf", ".doc", ".docx", ".xls", ".xlsx"
    ]
    return any(link.endswith(ext) for ext in bad_extensions)


def auto_category(title, summary, default):
    text = f"{title} {summary}".lower()

    if any(w in text for w in ["weather", "storm", "snow", "wind", "warning", "advisory", "blizzard"]):
        return "weather"
    if any(w in text for w in ["anchorage", "wasilla", "palmer", "mat-su", "matsu", "eagle river"]):
        return "anchorage"
    if any(w in text for w in ["juneau", "sitka", "ketchikan", "southeast", "haines", "skagway"]):
        return "southeast"
    if any(w in text for w in ["fairbanks", "interior", "north pole"]):
        return "interior"
    if any(w in text for w in ["kenai", "homer", "soldotna", "seward", "peninsula"]):
        return "kenai"
    if any(w in text for w in ["governor", "senate", "policy", "legislature", "election", "bill"]):
        return "politics"
    if any(w in text for w in ["native", "tribal", "subsistence", "rural alaska"]):
        return "culture"

    return default


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )

    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return response.read().decode("utf-8", "ignore")


def get_child_text(entry, names):
    for child in list(entry):
        tag = child.tag.split("}", 1)[-1]
        if tag in names:
            return "".join(child.itertext()).strip()
    return ""


def get_atom_link(entry):
    for child in list(entry):
        tag = child.tag.split("}", 1)[-1]
        if tag == "link":
            return child.attrib.get("href", "").strip()
    return ""


def parse_feed(xml_text, source):
    root = ET.fromstring(xml_text)
    items = []

    entries = root.findall(".//item")

    if not entries:
        entries = [
            entry for entry in root.iter()
            if entry.tag.split("}", 1)[-1] == "entry"
        ]

    for entry in entries[:MAX_PER_SOURCE]:
        title = clean(get_child_text(entry, ["title"]))
        link = get_child_text(entry, ["link"]) or get_atom_link(entry)

        # Alaska Landmine feed links can be unreliable.
        # Keep the headline, but send users to the homepage.
        if source.get("name") == "Alaska Landmine":
            link = source.get("home", "https://alaskalandmine.com/")

        # Skip direct-download links like .CAP files.
        if is_bad_link(link):
            continue

        summary = clean(get_child_text(entry, ["description", "summary", "content"]))
        date_text = get_child_text(entry, ["pubDate", "updated", "published"])
        pub_date = parse_date(date_text)

        if not title:
            continue

        category = auto_category(title, summary, source.get("category", "general"))

        items.append({
            "title": title,
            "link": link,
            "description": summary,
            "pubDate": format_date(pub_date),
            "category": category,
            "tag": source.get("tag", ""),
            "source": source.get("name", ""),
            "rank": source_rank(source),
        })

    return items


def sort_by_date(items):
    return sorted(
        items,
        key=lambda item: parse_date(item.get("pubDate", "")),
        reverse=True,
    )


def load_existing_items():
    if not DATA_FILE.exists():
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        pass

    return []


def fetch_anchorage_weather():
    points_url = "https://api.weather.gov/points/61.2176,-149.8997"

    headers = {
        "User-Agent": "AKPulseLive/1.0 contact: rob.schultz.usa@outlook.com",
        "Accept": "application/geo+json",
    }

    try:
        req = urllib.request.Request(points_url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            point_data = json.loads(response.read().decode("utf-8"))

        forecast_url = point_data["properties"]["forecast"]

        req = urllib.request.Request(forecast_url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))

    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return []

    weather_items = []

    for period in data.get("properties", {}).get("periods", [])[:5]:
        name = period.get("name", "Forecast")
        short = period.get("shortForecast", "")
        detail = period.get("detailedForecast", "")
        temp = period.get("temperature", "")
        unit = period.get("temperatureUnit", "F")
        wind = period.get("windSpeed", "")
        direction = period.get("windDirection", "")

        weather_items.append({
            "title": f"Anchorage Weather: {name} - {short}",
            "link": "https://forecast.weather.gov/MapClick.php?lat=61.2176&lon=-149.8997",
            "description": f"{temp}°{unit}. Wind {direction} {wind}. {detail}",
            "pubDate": format_date(datetime.now(timezone.utc)),
            "category": "weather",
            "tag": "weather",
            "source": "National Weather Service Anchorage",
            "rank": 0,
        })

    return weather_items
    
def main():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing = load_existing_items()
    seen = set(normalize(item.get("title", "")) for item in existing)
    new_items = []

    for source in SOURCES:
        if not source.get("enabled", True):
            continue

        print("Fetching:", source["name"])

        try:
            xml_text = fetch(source["url"])
            fetched_items = parse_feed(xml_text, source)

            for item in fetched_items:
                key = normalize(item.get("title", ""))
                if key and key not in seen:
                    seen.add(key)
                    new_items.append(item)

            print("  Added:", len(fetched_items))

        except Exception as error:
            print("  ERROR:", source["name"], "-", error)

        time.sleep(0.4)

    combined = new_items + existing

    world_items = [
        item for item in combined
        if item.get("category") in ["world", "business", "national"]
        or item.get("tag") in ["world", "business", "national"]
    ]

    non_world_items = [
        item for item in combined
        if item not in world_items
    ]

    world_items = sort_by_date(world_items)[:MIN_WORLD_ITEMS]

    non_world_items = sorted(
        non_world_items,
        key=lambda item: (
            item.get("rank", 0),
            parse_date(item.get("pubDate", "")),
        ),
        reverse=True,
    )

    combined = non_world_items[:MAX_TOTAL_ITEMS - len(world_items)] + world_items

    weather_items = fetch_anchorage_weather()
    new_items.extend(weather_items)
    print(f"Added {len(weather_items)} weather items")
    
    DATA_FILE.write_text(json.dumps(new_items, indent=2), encoding="utf-8")
   
    print("Saved", len(combined), "items")
    print("World/general items reserved:", len(world_items))


if __name__ == "__main__":
    main()
