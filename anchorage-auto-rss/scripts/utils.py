import html
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime, format_datetime

from config import DATA_FILE


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
        dt = datetime.fromisoformat(str(date_text).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def format_date(dt):
    return format_datetime(dt.astimezone(timezone.utc), usegmt=True)


def normalize(text):
    return re.sub(r"\W+", " ", (text or "").lower()).strip()


def item_key(item):
    link = (item.get("link") or item.get("url") or "").strip().lower()
    if link:
        return "url:" + link

    title = normalize(item.get("title", ""))
    source = normalize(item.get("source", ""))
    return f"title:{source}:{title}"


def sort_by_date(items):
    return sorted(items, key=lambda item: parse_date(item.get("pubDate", "")), reverse=True)


def load_existing_items():
    if not DATA_FILE.exists():
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception as error:
        print(f"Could not read existing feed_items.json: {error}")

    return []


def save_items(items):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")
