#!/usr/bin/env python3

import json, time, re, html
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, format_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"

MAX_TOTAL_ITEMS = 50
MAX_PER_SOURCE = 5
TIMEOUT = 20


def source_rank(source):
    category = source.get("category", "").lower()
    tag = source.get("tag", "").lower()
    name = source.get("name", "").lower()

    if category in ["alaska", "alaska-news", "weather"] or tag == "alaska":
        return 100

    if any(word in name for word in ["alaska", "anchorage", "juneau", "homer", "kenai", "ktoo", "adn"]):
        return 90

    return 10


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
        "name": "NWS Alaska",
        "url": "https://api.weather.gov/alerts/active.atom?area=AK",
        "category": "weather",
        "tag": "alaska",
        "enabled": True,
    },
    {
        "name": "BBC",
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "category": "world",
        "tag": "world",
        "enabled": True,
    },
]


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def parse_date(d):
    try:
        dt = parsedate_to_datetime(d)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def format_date(dt):
    return format_datetime(dt.astimezone(timezone.utc), usegmt=True)


def normalize(title):
    return re.sub(r"\W+", " ", title.lower()).strip()


def auto_category(title, summary, default):
    t = (title + " " + summary).lower()

    if any(w in t for w in ["weather", "storm", "snow", "wind", "warning", "advisory"]):
        return "weather"
    if any(w in t for w in ["anchorage", "wasilla", "palmer", "mat-su", "matsu"]):
        return "anchorage"
    if any(w in t for w in ["juneau", "sitka", "ketchikan", "southeast"]):
        return "southeast"
    if any(w in t for w in ["fairbanks", "interior"]):
        return "interior"
    if any(w in t for w in ["kenai", "homer", "soldotna", "seward"]):
        return "kenai"
    if any(w in t for w in ["governor", "senate", "policy", "legislature", "election"]):
        return "politics"

    return default


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", "ignore")


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


def parse_feed(xml, source):
    root = ET.fromstring(xml)
    items = []

    entries = root.findall(".//item")

    if not entries:
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for e in entries[:MAX_PER_SOURCE]:
        title = get_child_text(e, {"title"})
        link = get_child_text(e, {"link"}) or get_atom_link(e)
        desc = get_child_text(e, {"description", "summary", "content"})
        pub = get_child_text(e, {"pubDate", "published", "updated"})

        if not title or not link:
            continue

        items.append({
            "title": clean_title(title),
            "link": link,
            "url": link,
            "summary": desc,
            "description": desc,
            "source": source["name"],
            "category": source.get("category", "general"),
            "tag": source.get("tag", ""),
            "pubDate": pub or now_rfc2822(),
        })

    return items


def main():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if DATA_FILE.exists():
        try:
            existing = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    seen = set(normalize(i.get("title", "")) for i in existing)
    new_items = []

    for src in SOURCES:
        if not src.get("enabled", True):
            continue

        print("Fetching:", src["name"])

        try:
            xml = fetch(src["url"])
            items = parse_feed(xml, src)

            for it in items:
                key = normalize(it.get("title", ""))
                if key not in seen:
                    seen.add(key)
                    new_items.append(it)

        except Exception as e:
            print("ERROR:", src["name"], "-", e)

        time.sleep(0.4)

    combined = new_items + existing

    combined = sorted(
        combined,
        key=lambda x: (
            x.get("rank", 0),
            x.get("pubDate", ""),
        ),
        reverse=True,
    )[:MAX_TOTAL_ITEMS]

    DATA_FILE.write_text(json.dumps(combined, indent=2), encoding="utf-8")
    print("Saved", len(combined), "items")


if __name__ == "__main__":
    main()
