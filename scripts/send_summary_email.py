#!/usr/bin/env python3

import os
import json
import smtplib
from pathlib import Path
from datetime import datetime, timezone
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

    total_items = 0
    newest_items = []

    if DATA_FILE.exists():
        items = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        total_items = len(items)
        newest_items = items[:10]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    body = [
        "AK Pulse Live Update Completed",
        "",
        f"Time: {now}",
        f"Total items in feed_items.json: {total_items}",
        "",
        "Newest articles:",
        "",
    ]

    for item in newest_items:
        title = item.get("title", "Untitled")
        source = item.get("source", "Unknown source")
        category = item.get("category", "general")
        body.append(f"- {title}")
        body.append(f"  Source: {source} | Category: {category}")
        body.append("")

    msg = EmailMessage()
    msg["Subject"] = f"AK Pulse Live Update - {total_items} Items"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content("\n".join(body))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_APP_PASSWORD)
        smtp.send_message(msg)

    print("Summary email sent.")

if __name__ == "__main__":
    main()
