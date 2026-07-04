import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from utils import format_date


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

    except Exception as error:
        print(f"Weather fetch failed: {error}")
        return []

    weather_items = []
    base_link = "https://forecast.weather.gov/MapClick.php?lat=61.2176&lon=-149.8997"

    for index, period in enumerate(data.get("properties", {}).get("periods", [])[:5], start=1):
        name = period.get("name", "Forecast")
        short = period.get("shortForecast", "")
        detail = period.get("detailedForecast", "")
        temp = period.get("temperature", "")
        unit = period.get("temperatureUnit", "F")
        wind = period.get("windSpeed", "")
        direction = period.get("windDirection", "")

        period_key = urllib.parse.quote(name.lower().replace(" ", "-"))
        link = f"{base_link}&period={index}-{period_key}"

        weather_items.append({
            "title": f"Anchorage Weather: {name} - {short}",
            "link": link,
            "description": f"{temp}°{unit}. Wind {direction} {wind}. {detail}",
            "pubDate": format_date(datetime.now(timezone.utc)),
            "category": "weather",
            "tag": "weather",
            "source": "National Weather Service Anchorage",
            "rank": 0,
        })

    return weather_items
