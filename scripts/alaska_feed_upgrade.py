# Alaska Feed Upgrade Bundle

ALASKA_FEEDS = [
    {"name": "Alaska Public Media","url": "https://alaskapublic.org/feed/","category": "alaska-news","priority": 1},
    {"name": "Alaska Beacon","url": "https://alaskabeacon.com/feed/","category": "alaska-news","priority": 1},
    {"name": "KTOO News Update","url": "https://feeds.ktoo.org/KTOONewsUpdate","category": "alaska-news","priority": 1},
    {"name": "Anchorage Daily News","url": "https://www.adn.com/feed/","category": "alaska-news","priority": 2},
    {"name": "Alaska's News Source","url": "https://www.alaskasnewssource.com/rss/","category": "alaska-news","priority": 2},
    {"name": "Juneau Empire","url": "https://www.juneauempire.com/feed/","category": "local","priority": 3},
    {"name": "Homer News","url": "https://www.homernews.com/feed/","category": "local","priority": 3},
    {"name": "Peninsula Clarion","url": "https://www.peninsulaclarion.com/feed/","category": "local","priority": 3},
    {"name": "Alaska Landmine","url": "https://alaskalandmine.com/feed/","category": "opinion","priority": 3},
    {"name": "Must Read Alaska","url": "https://mustreadalaska.com/feed/","category": "opinion","priority": 3},
    {"name": "Alaska Native News","url": "https://alaska-native-news.com/feed/","category": "culture","priority": 3},
    {"name": "NWS Alaska Alerts","url": "https://api.weather.gov/alerts/active.atom?area=AK","category": "weather","priority": 1},
]

def alaska_auto_category(title, summary="", default="alaska-news"):
    text = f"{title} {summary}".lower()
    if any(w in text for w in ["weather","storm","snow","wind","flood","warning","advisory"]): return "weather"
    if any(w in text for w in ["anchorage","mat-su","matsu","palmer","wasilla"]): return "anchorage"
    if any(w in text for w in ["juneau","southeast","sitka","ketchikan","haines"]): return "southeast"
    if any(w in text for w in ["fairbanks","north pole","interior"]): return "interior"
    if any(w in text for w in ["kenai","soldotna","homer","seward","peninsula"]): return "kenai"
    if any(w in text for w in ["legislature","governor","senate","house","election","policy"]): return "politics"
    if any(w in text for w in ["native","tribal","subsistence","rural alaska"]): return "culture"
    return default

def normalize_title(title):
    return " ".join(title.lower().strip().split())

def is_duplicate(new_item, existing_items):
    new_title = normalize_title(new_item.get("title",""))
    new_link = new_item.get("link","").strip()
    for item in existing_items:
        if new_link and new_link == item.get("link","").strip(): return True
        if new_title and new_title == normalize_title(item.get("title","")): return True
    return False
