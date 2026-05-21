from datetime import date, timedelta
from database import get_conn

TOOL_DEFINITIONS = [
    {
        "name": "log_watched",
        "description": "Log a movie, TV show, or book you consumed",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "media_type": {"type": "string", "description": "movie, series, book, podcast, documentary"},
                "rating": {"type": "number", "description": "Your rating out of 10 (optional)"},
                "notes": {"type": "string", "description": "Brief review or thoughts"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "recommend_media",
        "description": "Get a media recommendation based on recent watching history and mood",
        "input_schema": {
            "type": "object",
            "properties": {
                "genre": {"type": "string", "description": "Genre preference (optional)"},
                "media_type": {"type": "string", "description": "movie, series, book (optional)"}
            },
            "required": []
        }
    },
    {
        "name": "get_recently_watched",
        "description": "List recently logged media with ratings",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days to look back (default 30)"},
                "media_type": {"type": "string", "description": "Filter by type (optional)"}
            },
            "required": []
        }
    }
]


def log_watched(title: str, media_type: str = "movie", rating: float = None, notes: str = "") -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO media_log (title, media_type, rating, notes) VALUES (?,?,?,?)",
            (title, media_type.lower(), rating, notes)
        )
    result = {"logged": True, "id": cur.lastrowid, "title": title, "type": media_type}
    if rating:
        result["rating"] = rating
    return result


def recommend_media(genre: str = "", media_type: str = "") -> dict:
    return {
        "note": "TMDb integration not configured.",
        "suggestion": "Configure TMDB_API_KEY for personalized recommendations based on your watch history.",
        "fallback": "Try asking: 'What should I watch tonight?' and I can suggest based on your mood logs."
    }


def get_recently_watched(days: int = 30, media_type: str = "") -> dict:
    start = str(date.today() - timedelta(days=days))
    with get_conn() as conn:
        if media_type:
            rows = conn.execute(
                "SELECT title, media_type, rating, notes, date FROM media_log WHERE date >= ? AND media_type = ? ORDER BY date DESC LIMIT 20",
                (start, media_type.lower())
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT title, media_type, rating, notes, date FROM media_log WHERE date >= ? ORDER BY date DESC LIMIT 20",
                (start,)
            ).fetchall()
    items = [{"title": r["title"], "type": r["media_type"], "rating": r["rating"], "notes": r["notes"], "date": r["date"]} for r in rows]
    avg_rating = None
    ratings = [i["rating"] for i in items if i["rating"]]
    if ratings:
        avg_rating = round(sum(ratings) / len(ratings), 1)
    return {"days": days, "count": len(items), "avg_rating": avg_rating, "media": items}


TOOL_HANDLERS = {
    "log_watched": lambda args: log_watched(**args),
    "recommend_media": lambda args: recommend_media(**args),
    "get_recently_watched": lambda args: get_recently_watched(**args),
}
