#!/usr/bin/env python3

import os
import json
import smtplib
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from email.message import EmailMessage

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"

EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_TO = os.environ.get("EMAIL_TO")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")


def main():
    if not EMAIL_FROM or not EMAIL_TO or not EMAIL_APP_PASSWORD:
        print("Email skipped: missing EMAIL_FROM, EMAIL_TO, or EMAIL_APP_PASSWORD")
        return

    items = []
    if DATA_FILE.exists():
        items = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    total_items = len(items)
    source_counts = Counter(item.get("source", "Unknown source") for item in items)
    category_counts = Counter(item.get("category", "general") for item in items)
    newest_items = items[:12]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    github_run = os.environ.get("GITHUB_RUN_NUMBER", "Unknown")
    github_sha = os.environ.get("GITHUB_SHA", "")[:7]
    github_repo = os.environ.get("GITHUB_REPOSITORY", "Unknown")
    github_ref = os.environ.get("GITHUB_REF_NAME", "Unknown")

    body = []
    body.append("AK Pulse Live Update Completed")
    body.append("=" * 32)
    body.append("")
    body.append("Status: SUCCESS")
    body.append(f"Time: {now}")
    body.append(f"Repository: {github_repo}")
    body.append(f"Branch: {github_ref}")
    body.append(f"Workflow Run: #{github_run}")
    body.append(f"Commit: {github_sha}")
    body.append("")
    body.append(f"Total items in feed_items.json: {total_items}")
    body.append("")

    body.append("Items by Source")
    body.append("-" * 15)
    for source, count in source_counts.most_common():
        body.append(f"{source}: {count}")
    body.append("")

    body.append("Items by Category")
    body.append("-" * 17)
    for category, count in category_counts.most_common():
        body.append(f"{category}: {count}")
    body.append("")

    body.append("Newest Articles")
    body.append("-" * 15)
    for item in newest_items:
        title = item.get("title", "Untitled")
        source = item.get("source", "Unknown source")
        category = item.get("category", "general")
        link = item.get("link") or item.get("url", "")

        body.append(f"- {title}")
        body.append(f"  Source: {source} | Category: {category}")
        if link:
            body.append(f"  Link: {link}")
        body.append("")

    body.append("Workflow Notes")
    body.append("-" * 14)
    body.append("Import news: completed before this email step.")
    body.append("Generate feed: completed before this email step.")
    body.append("Commit step: runs after this email step.")
    body.append("")

    msg = EmailMessage()
    msg["Subject"] = f"AK Pulse Live Update SUCCESS - {total_items} Items"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content("\n".join(body))

    print("Connecting to Gmail SMTP...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        print("Logging in...")
        smtp.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
        print("Sending summary email...")
        smtp.send_message(msg)

    print("Summary email sent.")


if __name__ == "__main__":
    main()
