import os

from config import SUPABASE_BATCH_SIZE


def item_to_article_row(item):
    return {
        "title": item.get("title"),
        "url": item.get("link"),
        "source": item.get("source"),
        "author": item.get("author"),
        "published_at": item.get("published_at") or item.get("pubDate"),
        "summary": item.get("description"),
        "content": item.get("content") or item.get("description"),
        "category": item.get("category"),
        "tags": item.get("tag"),
    }


def sync_to_supabase(items):
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        print("Supabase sync skipped: missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return

    try:
        from supabase import create_client
    except ImportError:
        print("Supabase sync skipped: Python package 'supabase' is not installed")
        return

    rows = []
    seen_urls = set()

    for item in items:
        row = item_to_article_row(item)
        url = (row.get("url") or "").strip()

        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        rows.append(row)

    if not rows:
        print("No articles to sync to Supabase.")
        return

    supabase = create_client(supabase_url, supabase_key)
    synced = 0

    for start in range(0, len(rows), SUPABASE_BATCH_SIZE):
        batch = rows[start:start + SUPABASE_BATCH_SIZE]
        supabase.table("articles").upsert(batch, on_conflict="url").execute()
        synced += len(batch)

    print(f"Synced {synced} articles to Supabase.")
