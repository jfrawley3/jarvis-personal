import httpx
from datetime import datetime
from config import LOCATION, NEWS_API_KEY

TOOL_DEFINITIONS = [
    {
        "name": "get_weather",
        "description": "Get current weather and today's forecast for the configured location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name or lat,lon (uses config default if omitted)"}
            },
            "required": []
        }
    },
    {
        "name": "news_digest",
        "description": "Get top news headlines",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic filter (optional): technology, health, business, world"},
                "count": {"type": "integer", "description": "Number of headlines (default 5, max 10)"}
            },
            "required": []
        }
    },
    {
        "name": "get_literature_quote",
        "description": "Get an inspiring quote from literature or philosophy",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_current_time",
        "description": "Get the current date and time",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]

QUOTES = [
    ("The obstacle is the way.", "Marcus Aurelius"),
    ("We suffer more in imagination than in reality.", "Seneca"),
    ("You have power over your mind, not outside events. Realize this, and you will find strength.", "Marcus Aurelius"),
    ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
    ("The only way out is through.", "Robert Frost"),
    ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("Either write something worth reading or do something worth writing.", "Benjamin Franklin"),
    ("First, do no harm.", "Hippocrates"),
    ("The best time to plant a tree was 20 years ago. The second best time is now.", "Chinese Proverb"),
    ("An unexamined life is not worth living.", "Socrates"),
    ("Do not go where the path may lead, go instead where there is no path and leave a trail.", "Ralph Waldo Emerson"),
    ("Whatever you are, be a good one.", "Abraham Lincoln"),
    ("Simplicity is the ultimate sophistication.", "Leonardo da Vinci"),
    ("It is not the strongest of the species that survive, but the most adaptable.", "Charles Darwin"),
]


def get_weather(location: str = "") -> dict:
    loc = location or LOCATION
    try:
        with httpx.Client(timeout=8) as client:
            resp = client.get(f"https://wttr.in/{loc}?format=j1")
            data = resp.json()
        current = data["current_condition"][0]
        today = data["weather"][0]
        return {
            "location": loc,
            "temp_c": int(current["temp_C"]),
            "temp_f": int(current["temp_F"]),
            "feels_c": int(current["FeelsLikeC"]),
            "condition": current["weatherDesc"][0]["value"],
            "humidity_pct": int(current["humidity"]),
            "wind_mph": int(current["windspeedMiles"]),
            "max_c": int(today["maxtempC"]),
            "min_c": int(today["mintempC"]),
            "uv_index": today.get("uvIndex", "n/a")
        }
    except Exception as e:
        return {"error": f"Weather unavailable: {str(e)}", "location": loc}


def news_digest(topic: str = "", count: int = 5) -> dict:
    count = min(count or 5, 10)
    if NEWS_API_KEY:
        try:
            url = "https://newsapi.org/v2/top-headlines"
            params = {"apiKey": NEWS_API_KEY, "pageSize": count, "language": "en"}
            if topic:
                params["q"] = topic
            else:
                params["country"] = "us"
            with httpx.Client(timeout=8) as client:
                resp = client.get(url, params=params)
                data = resp.json()
            articles = [
                {"title": a["title"], "source": a["source"]["name"], "url": a["url"]}
                for a in data.get("articles", [])[:count]
            ]
            return {"source": "newsapi.org", "topic": topic or "top", "count": len(articles), "articles": articles}
        except Exception:
            pass
    try:
        feed_url = "https://feeds.bbci.co.uk/news/rss.xml" if not topic else f"https://feeds.bbci.co.uk/news/{topic.lower()}/rss.xml"
        with httpx.Client(timeout=8) as client:
            resp = client.get(feed_url, headers={"User-Agent": "JARVIS/1.0"})
        import re
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", resp.text)[1:count + 1]
        if not titles:
            titles = re.findall(r"<title>(.*?)</title>", resp.text)[1:count + 1]
        return {"source": "BBC RSS", "topic": topic or "top", "count": len(titles), "headlines": titles}
    except Exception as e:
        return {"error": f"News unavailable: {str(e)}"}


def get_literature_quote() -> dict:
    import hashlib
    today_hash = int(hashlib.md5(str(datetime.today().date()).encode()).hexdigest(), 16)
    quote, author = QUOTES[today_hash % len(QUOTES)]
    return {"quote": quote, "author": author}


def get_current_time() -> dict:
    now = datetime.now()
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": str(now.date()),
        "time": now.strftime("%H:%M"),
        "day": now.strftime("%A"),
        "week": now.strftime("Week %V of %Y")
    }


TOOL_HANDLERS = {
    "get_weather": lambda args: get_weather(**args),
    "news_digest": lambda args: news_digest(**args),
    "get_literature_quote": lambda args: get_literature_quote(),
    "get_current_time": lambda args: get_current_time(),
}
