# Anchorage auto-updating RSS feed

This repo keeps your RSS data in `data/feed_items.json` and automatically rebuilds:
- `feed.xml`
- `index.html`

## How it works
- You edit `data/feed_items.json`
- GitHub Actions runs `scripts/generate_feed.py`
- The workflow commits the rebuilt files back to `main`
- GitHub Pages serves the updated feed from your repo

## One-time setup
1. Upload all files in this package to your `anchorage` repository.
2. In GitHub, go to **Settings → Pages**.
3. Keep **Deploy from a branch**.
4. Set branch to `main` and folder to `/(root)`.
5. Go to **Actions** and enable workflows if GitHub asks.

## Updating your feed manually on GitHub
Open `data/feed_items.json` and add a new object like this near the top of the list:

```json
{
  "title": "A new item",
  "link": "https://fritoburrito.github.io/anchorage/",
  "guid": "unique-id-here",
  "description": "What this item is about.",
  "pubDate": "Wed, 22 Apr 2026 18:30:00 GMT"
}
```

Then commit the change. The workflow will regenerate `feed.xml` and `index.html` automatically.

## Updating locally with the helper script
```bash
python3 scripts/add_item.py \
  --title "A new item" \
  --link "https://fritoburrito.github.io/anchorage/" \
  --guid "item-2" \
  --description "What this item is about." \
  --pubdate "Wed, 22 Apr 2026 18:30:00 GMT"
```

## Workflow schedule
The workflow also runs on a schedule every hour at minute 17 UTC. GitHub Actions schedules run in UTC and public repository schedules can be disabled after 60 days of inactivity, so the repo still supports manual runs from the **Actions** tab and push-triggered updates. See GitHub's docs for details.
