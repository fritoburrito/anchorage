#!/usr/bin/env python3

import time

from config import MAX_TOTAL_ITEMS, MIN_WORLD_ITEMS, SOURCES
from database import sync_to_supabase
from feeds import fetch_source_items
from utils import item_key, load_existing_items, save_items, sort_by_date
from weather import fetch_anchorage_weather


def reserve_world_items(items):
    world_items = [
        item for item in items
        if item.get("category") in ["world", "business", "national"]
        or item.get("tag") in ["world", "business", "national"]
    ]

    non_world_items = [
        item for item in items
        if item not in world_items
    ]

    world_items = sort_by_date(world_items)[:MIN_WORLD_ITEMS]

    non_world_items = sorted(
        non_world_items,
        key=lambda item: (
            item.get("rank", 0),
            sort_by_date([item])[0].get("pubDate", ""),
        ),
        reverse=True,
    )

    return non_world_items[:MAX_TOTAL_ITEMS - len(world_items)] + world_items, len(world_items)


def merge_items(new_items, existing_items):
    merged = []
    seen = set()

    for item in new_items + existing_items:
        key = item_key(item)
        if key and key not in seen:
            seen.add(key)
            merged.append(item)

    return merged


def main():
    existing_items = load_existing_items()
    existing_keys = {item_key(item) for item in existing_items}
    new_items = []

    print(f"Loaded {len(existing_items)} existing items.")

    for source in SOURCES:
        if not source.get("enabled", True):
            continue

        try:
            fetched_items = fetch_source_items(source)

            added = 0
            for item in fetched_items:
                key = item_key(item)
                if key and key not in existing_keys:
                    existing_keys.add(key)
                    new_items.append(item)
                    added += 1

            print(f"  New: {added}")

        except Exception as error:
            print(f"  ERROR: {source['name']} - {error}")

        time.sleep(0.4)

    weather_items = fetch_anchorage_weather()
    print(f"Added {len(weather_items)} weather items")

    combined = merge_items(new_items + weather_items, existing_items)
    combined, world_count = reserve_world_items(combined)

    save_items(combined)

    print(f"Saved {len(combined)} items")
    print(f"World/general items reserved: {world_count}")

    sync_to_supabase(combined)


if __name__ == "__main__":
    main()
