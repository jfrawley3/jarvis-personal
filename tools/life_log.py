import json
from datetime import date, timedelta
from database import get_conn

TOOL_DEFINITIONS = [
    {
        "name": "log_idea",
        "description": "Log an idea with optional tags for future reference",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Brief title for the idea"},
                "content": {"type": "string", "description": "Full description of the idea"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for organization"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "log_decision",
        "description": "Log an important decision with the reasoning behind it",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The decision made"},
                "content": {"type": "string", "description": "Reasoning, context, alternatives considered"},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["title"]
        }
    },
    {
        "name": "log_social",
        "description": "Log a social interaction, conversation, or relationship note",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Who and what (e.g. 'Coffee with Sarah — job update')"},
                "content": {"type": "string", "description": "Key notes, follow-ups, context"},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["title"]
        }
    },
    {
        "name": "log_learning",
        "description": "Log something learned — concept, skill, insight, or course progress",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "What was learned"},
                "content": {"type": "string", "description": "Key takeaway or detail"},
                "tags": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["title"]
        }
    },
    {
        "name": "get_recent_ideas",
        "description": "Retrieve recent ideas from the life log",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days to look back (default 14)"},
                "limit": {"type": "integer", "description": "Max results (default 10)"}
            },
            "required": []
        }
    },
    {
        "name": "get_recent_decisions",
        "description": "Retrieve recent decisions from the life log",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days to look back (default 30)"},
                "limit": {"type": "integer", "description": "Max results (default 10)"}
            },
            "required": []
        }
    },
    {
        "name": "search_life_log",
        "description": "Full-text search across all life log entries",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term"},
                "log_type": {"type": "string", "description": "Filter by type: idea, decision, social, learning, or all"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "generate_self_portrait",
        "description": "Generate a text-based self-portrait summarizing who you are based on your logs",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


def _log_entry(log_type: str, title: str, content: str = "", tags: list = None) -> dict:
    tags_json = json.dumps(tags or [])
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO life_log (log_type, title, content, tags) VALUES (?,?,?,?)",
            (log_type, title, content, tags_json)
        )
    return {"logged": True, "type": log_type, "id": cur.lastrowid, "title": title}


def log_idea(title: str, content: str = "", tags: list = None) -> dict:
    return _log_entry("idea", title, content, tags)


def log_decision(title: str, content: str = "", tags: list = None) -> dict:
    return _log_entry("decision", title, content, tags)


def log_social(title: str, content: str = "", tags: list = None) -> dict:
    return _log_entry("social", title, content, tags)


def log_learning(title: str, content: str = "", tags: list = None) -> dict:
    return _log_entry("learning", title, content, tags)


def _get_recent(log_type: str, days: int, limit: int) -> dict:
    start = str(date.today() - timedelta(days=days))
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, content, tags, date FROM life_log WHERE log_type = ? AND date >= ? ORDER BY timestamp DESC LIMIT ?",
            (log_type, start, limit)
        ).fetchall()
    entries = [{"id": r["id"], "title": r["title"], "content": r["content"][:150], "tags": json.loads(r["tags"]), "date": r["date"]} for r in rows]
    return {"type": log_type, "count": len(entries), "entries": entries}


def get_recent_ideas(days: int = 14, limit: int = 10) -> dict:
    return _get_recent("idea", days, limit)


def get_recent_decisions(days: int = 30, limit: int = 10) -> dict:
    return _get_recent("decision", days, limit)


def search_life_log(query: str, log_type: str = "all") -> dict:
    with get_conn() as conn:
        if log_type and log_type.lower() != "all":
            rows = conn.execute(
                "SELECT id, log_type, title, content, date FROM life_log WHERE log_type = ? AND (title LIKE ? OR content LIKE ?) ORDER BY timestamp DESC LIMIT 20",
                (log_type.lower(), f"%{query}%", f"%{query}%")
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, log_type, title, content, date FROM life_log WHERE title LIKE ? OR content LIKE ? ORDER BY timestamp DESC LIMIT 20",
                (f"%{query}%", f"%{query}%")
            ).fetchall()
    results = [{"id": r["id"], "type": r["log_type"], "title": r["title"], "snippet": r["content"][:120], "date": r["date"]} for r in rows]
    return {"query": query, "results": len(results), "entries": results}


def generate_self_portrait() -> dict:
    today = str(date.today())
    with get_conn() as conn:
        ideas = conn.execute("SELECT COUNT(*) FROM life_log WHERE log_type = 'idea'").fetchone()[0]
        decisions = conn.execute("SELECT COUNT(*) FROM life_log WHERE log_type = 'decision'").fetchone()[0]
        habit_data = conn.execute(
            "SELECT habit_name, COUNT(*) as c FROM habits WHERE date >= date('now', '-30 days') GROUP BY habit_name ORDER BY c DESC LIMIT 5"
        ).fetchall()
        avg_mood = conn.execute(
            "SELECT AVG(mood_score) FROM mood_logs WHERE date >= date('now', '-30 days')"
        ).fetchone()[0]
        recent_decisions = conn.execute(
            "SELECT title FROM life_log WHERE log_type = 'decision' ORDER BY timestamp DESC LIMIT 3"
        ).fetchall()
    top_habits = [{"habit": r["habit_name"], "days": r["c"]} for r in habit_data]
    portrait = {
        "generated": today,
        "stats": {
            "ideas_logged": ideas,
            "decisions_logged": decisions,
            "avg_mood_30d": round(avg_mood, 1) if avg_mood else None,
            "top_habits": top_habits,
        },
        "recent_decisions": [r["title"] for r in recent_decisions],
        "note": "Self-portrait is data-driven and grows richer with more logs."
    }
    return portrait


TOOL_HANDLERS = {
    "log_idea": lambda args: log_idea(**args),
    "log_decision": lambda args: log_decision(**args),
    "log_social": lambda args: log_social(**args),
    "log_learning": lambda args: log_learning(**args),
    "get_recent_ideas": lambda args: get_recent_ideas(**args),
    "get_recent_decisions": lambda args: get_recent_decisions(**args),
    "search_life_log": lambda args: search_life_log(**args),
    "generate_self_portrait": lambda args: generate_self_portrait(),
}
