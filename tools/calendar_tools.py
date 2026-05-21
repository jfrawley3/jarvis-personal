from datetime import date, datetime, timedelta
from database import get_conn

TOOL_DEFINITIONS = [
    {
        "name": "query_calendar",
        "description": "List calendar events for today or a date range",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD or 'today' (default: today)"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD (default: same as start_date)"}
            },
            "required": []
        }
    },
    {
        "name": "add_calendar_event",
        "description": "Add an event to the calendar",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "start_datetime": {"type": "string", "description": "YYYY-MM-DD HH:MM or YYYY-MM-DD"},
                "end_datetime": {"type": "string", "description": "YYYY-MM-DD HH:MM (optional)"},
                "location": {"type": "string"},
                "notes": {"type": "string"}
            },
            "required": ["title", "start_datetime"]
        }
    }
]


def _resolve(date_str: str) -> str:
    if not date_str or date_str.lower() == "today":
        return str(date.today())
    if date_str.lower() == "tomorrow":
        return str(date.today() + timedelta(days=1))
    return date_str


def query_calendar(start_date: str = "today", end_date: str = "") -> dict:
    start = _resolve(start_date)
    end = _resolve(end_date) if end_date else start
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, start_datetime, end_datetime, location, notes FROM calendar_events WHERE date(start_datetime) BETWEEN ? AND ? ORDER BY start_datetime",
            (start, end)
        ).fetchall()
    events = []
    for r in rows:
        events.append({
            "id": r["id"],
            "title": r["title"],
            "start": r["start_datetime"],
            "end": r["end_datetime"],
            "location": r["location"],
            "notes": r["notes"]
        })
    return {"date_range": f"{start} to {end}", "count": len(events), "events": events}


def add_calendar_event(title: str, start_datetime: str, end_datetime: str = None, location: str = "", notes: str = "") -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO calendar_events (title, start_datetime, end_datetime, location, notes) VALUES (?,?,?,?,?)",
            (title, start_datetime, end_datetime, location, notes)
        )
    return {"added": True, "id": cur.lastrowid, "title": title, "start": start_datetime}


TOOL_HANDLERS = {
    "query_calendar": lambda args: query_calendar(**args),
    "add_calendar_event": lambda args: add_calendar_event(**args),
}
