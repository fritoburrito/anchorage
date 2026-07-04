def source_rank(source):
    category = source.get("category", "").lower()
    tag = source.get("tag", "").lower()
    name = source.get("name", "").lower()

    if category in ["alaska", "alaska-news", "weather"] or tag == "alaska":
        return 100

    if any(word in name for word in ["alaska", "anchorage", "juneau", "homer", "kenai", "ktoo", "adn"]):
        return 90

    return 10


def auto_category(title, summary, default):
    text = f"{title} {summary}".lower()

    if any(w in text for w in ["weather", "storm", "snow", "wind", "warning", "advisory", "blizzard"]):
        return "weather"
    if any(w in text for w in ["anchorage", "wasilla", "palmer", "mat-su", "matsu", "eagle river"]):
        return "anchorage"
    if any(w in text for w in ["juneau", "sitka", "ketchikan", "southeast", "haines", "skagway"]):
        return "southeast"
    if any(w in text for w in ["fairbanks", "interior", "north pole"]):
        return "interior"
    if any(w in text for w in ["kenai", "homer", "soldotna", "seward", "peninsula"]):
        return "kenai"
    if any(w in text for w in ["governor", "senate", "policy", "legislature", "election", "bill"]):
        return "politics"
    if any(w in text for w in ["native", "tribal", "subsistence", "rural alaska"]):
        return "culture"

    return default
