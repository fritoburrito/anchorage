from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "feed_items.json"

MAX_TOTAL_ITEMS = 60
MAX_PER_SOURCE = 10
MIN_WORLD_ITEMS = 20
TIMEOUT = 20
SUPABASE_BATCH_SIZE = 100

SOURCES = [
    {"name": "Alaska Public Media", "url": "https://alaskapublic.org/feed/", "category": "alaska", "tag": "alaska", "enabled": True},
    {"name": "Alaska Beacon", "url": "https://alaskabeacon.com/feed/", "category": "alaska", "tag": "alaska", "enabled": True},
    {"name": "KTOO", "url": "https://feeds.ktoo.org/KTOONewsUpdate", "category": "alaska", "tag": "alaska", "enabled": True},
    {"name": "Anchorage Daily News", "url": "https://www.adn.com/rss/", "category": "alaska", "tag": "alaska", "enabled": True},
    {"name": "Homer News", "url": "https://www.homernews.com/feed/", "category": "local", "tag": "alaska", "enabled": True},
    {"name": "Juneau Empire", "url": "https://www.juneauempire.com/feed/", "category": "local", "tag": "alaska", "enabled": True},
    {"name": "Alaska Landmine", "url": "https://alaskalandmine.com/feed/", "home": "https://alaskalandmine.com/", "category": "opinion", "tag": "alaska", "enabled": True},
    {"name": "FOX Weather", "url": "https://moxie.foxweather.com/google-publisher/weather-news.xml", "category": "weather", "tag": "weather", "enabled": True},
    {"name": "Must Read Alaska", "url": "https://mustreadalaska.com/feed/", "category": "opinion", "tag": "alaska", "enabled": True},
    {"name": "Alaska Native News", "url": "https://alaska-native-news.com/feed/", "category": "culture", "tag": "alaska", "enabled": True},
    {"name": "NWS Alaska Alerts", "url": "https://api.weather.gov/alerts/active.atom?area=AK", "category": "weather", "tag": "alaska", "enabled": True},

    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "world", "tag": "world", "enabled": True},
    {"name": "FOX World News", "url": "https://moxie.foxnews.com/google-publisher/latest.xml", "category": "world", "tag": "world", "enabled": True},
    {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/rss.xml", "category": "world", "tag": "world", "enabled": True},
    {"name": "NPR News", "url": "https://feeds.npr.org/1001/rss.xml", "category": "world", "tag": "world", "enabled": True},
]
