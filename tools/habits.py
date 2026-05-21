from datetime import date, timedelta
from database import get_conn

TOOL_DEFINITIONS = [
    {
        "name": "log_habit",
        "description": "Log a habit completion for today (append-only, one entry per habit per day)",
        "input_schema": {
            "type": "object",
            "properties": {
                "habit_name": {"type": "string", "description": "Name of the habit (e.g. meditation, reading, exercise)"},
                "value": {"type": "string", "description": "Optional value or note (e.g. '20 min', '5km', 'chapter 3')"}
            },
            "required": ["habit_name"]
        }
    },
    {
        "name": "query_habits",
        "description": "Query habit logs for a specific habit over a date range",
        "input_schema": {
            "type": "object",
            "properties": {
                "habit_name": {"type": "string", "description": "Habit name to query (or 'all' for all habits)"},
                "days": {"type": "integer", "description": "Days to look back (default 7)"}
            },
            "required": []
        }
    },
    {
        "name": "get_habit_streak",
        "description": "Get the current streak for a specific habit (consecutive days logged)",
        "input_schema": {
            "type": "object",
            "properties": {
                "habit_name": {"type": "string"}
            },
            "required": ["habit_name"]
        }
    },
    {
        "name": "list_habits",
        "description": "List all distinct habits tracked, with last-logged date and 7-day completion rate",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


def log_habit(habit_name: str, value: str = "") -> dict:
    name = habit_name.lower().strip()
    today = str(date.today())
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM habits WHERE habit_name = ? AND date = ?", (name, today)
        ).fetchone()
        if existing:
            conn.execute("UPDATE habits SET value = ? WHERE id = ?", (value, existing["id"]))
            action = "updated"
        else:
            conn.execute("INSERT INTO habits (habit_name, value) VALUES (?,?)", (name, value))
            action = "logged"
    streak = get_habit_streak(name)["streak"]
    return {"action": action, "habit": name, "value": value, "streak": streak}


def query_habits(habit_name: str = "all", days: int = 7) -> dict:
    start = str(date.today() - timedelta(days=days))
    with get_conn() as conn:
        if habit_name.lower() == "all":
            rows = conn.execute(
                "SELECT date, habit_name, value FROM habits WHERE date >= ? ORDER BY date DESC",
                (start,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT date, habit_name, value FROM habits WHERE habit_name = ? AND date >= ? ORDER BY date DESC",
                (habit_name.lower(), start)
            ).fetchall()
    logs = [{"date": r["date"], "habit": r["habit_name"], "value": r["value"]} for r in rows]
    return {"habit": habit_name, "days": days, "logged_count": len(logs), "logs": logs}


def get_habit_streak(habit_name: str) -> dict:
    name = habit_name.lower().strip()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date FROM habits WHERE habit_name = ? ORDER BY date DESC LIMIT 365",
            (name,)
        ).fetchall()
    dates = [r["date"] for r in rows]
    if not dates:
        return {"habit": name, "streak": 0, "last_logged": None}
    streak = 0
    check = date.today()
    for d_str in dates:
        d = date.fromisoformat(d_str)
        if d == check or d == check - timedelta(days=1) and streak == 0:
            streak += 1
            check = d - timedelta(days=1)
        elif d == check:
            streak += 1
            check = d - timedelta(days=1)
        else:
            break
    return {"habit": name, "streak": streak, "last_logged": dates[0] if dates else None}


def list_habits() -> dict:
    week_ago = str(date.today() - timedelta(days=7))
    today = str(date.today())
    with get_conn() as conn:
        habits = conn.execute(
            "SELECT habit_name, MAX(date) as last_logged, COUNT(DISTINCT date) as total_days FROM habits GROUP BY habit_name ORDER BY last_logged DESC"
        ).fetchall()
        week_counts = {r["habit_name"]: r["days"] for r in conn.execute(
            "SELECT habit_name, COUNT(DISTINCT date) as days FROM habits WHERE date >= ? GROUP BY habit_name",
            (week_ago,)
        ).fetchall()}
    result = []
    for h in habits:
        name = h["habit_name"]
        result.append({
            "habit": name,
            "last_logged": h["last_logged"],
            "total_days": h["total_days"],
            "7d_days": week_counts.get(name, 0),
            "logged_today": week_counts.get(name, 0) > 0 and h["last_logged"] == today
        })
    return {"habit_count": len(result), "habits": result}


TOOL_HANDLERS = {
    "log_habit": lambda args: log_habit(**args),
    "query_habits": lambda args: query_habits(**args),
    "get_habit_streak": lambda args: get_habit_streak(**args),
    "list_habits": lambda args: list_habits(),
}
