#!/usr/bin/env python3

import json
import os
from pathlib import Path
from supabase import create_client

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"
STATS_FILE = ROOT / "data" / "import_stats.json"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

items = json.loads(DATA_FILE.read_text(encoding="utf-8"))

inserted = 0
duplicates = 0
updated = 0

for item in items:
    title = item.get("title", "").strip()
    link = item.get("link", "").strip()

    if not title or not link:
        continue

    existing = (
        supabase.table("articles")
        .select("id")
        .eq("url", link)
        .limit(1)
        .execute()
    )

    if existing.data:
        duplicates += 1
        continue

    row = {
        "title": title,
        "url": link,
        "source": item.get("source", ""),
        "category": item.get("category", ""),
        "summary": item.get("description", ""),
        "published_at": item.get("pubDate", None),
    }

    supabase.table("articles").insert(row).execute()
    inserted += 1

total_result = supabase.table("articles").select("id", count="exact").limit(1).execute()
database_total = total_result.count or 0

stats = {
    "rows_inserted": inserted,
    "rows_updated": updated,
    "duplicates_ignored": duplicates,
    "database_total": database_total,
}

STATS_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")

print("Supabase import complete")
print(f"Rows Inserted: {inserted}")
print(f"Rows Updated: {updated}")
print(f"Duplicates Ignored: {duplicates}")
print(f"Database Total: {database_total}")
