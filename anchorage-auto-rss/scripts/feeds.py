import urllib.request
import xml.etree.ElementTree as ET

from categories import auto_category, source_rank
from config import MAX_PER_SOURCE, TIMEOUT
from utils import clean, format_date, parse_date


def fetch_url(url, headers=None):
    req = urllib.request.Request(
        url,
        headers=headers or {
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


def is_bad_link(link):
    link = (link or "").lower().split("?")[0]
    bad_extensions = [
        ".cap", ".zip", ".exe", ".dmg", ".pkg", ".tar", ".gz",
        ".7z", ".rar", ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ]
    return any(link.endswith(ext) for ext in bad_extensions)


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

        if source.get("name") == "Alaska Landmine":
            link = source.get("home", "https://alaskalandmine.com/")

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


def fetch_source_items(source):
    print(f"Fetching: {source['name']}")
    xml_text = fetch_url(source["url"])
    items = parse_feed(xml_text, source)
    print(f"  Parsed: {len(items)}")
    return items
