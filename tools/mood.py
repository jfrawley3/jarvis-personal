from datetime import date, timedelta
from database import get_conn

TOOL_DEFINITIONS = [
    {
        "name": "log_mood",
        "description": "Log current mood score with optional context",
        "input_schema": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "description": "Mood score 1-10 (1=very low, 10=excellent)"},
                "context": {"type": "string", "description": "Optional note about what influenced the mood"}
            },
            "required": ["score"]
        }
    },
    {
        "name": "log_energy",
        "description": "Log current energy level",
        "input_schema": {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "description": "Energy level 1-10"},
                "context": {"type": "string", "description": "Optional context"}
            },
            "required": ["score"]
        }
    },
    {
        "name": "query_mood",
        "description": "Get mood and energy logs for a date range",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (default 7)"}
            },
            "required": []
        }
    },
    {
        "name": "analyze_mood_patterns",
        "description": "Analyze mood patterns, find correlations, and surface trends over time",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Analysis window in days (default 30)"}
            },
            "required": []
        }
    },
    {
        "name": "get_mood_summary",
        "description": "Get a concise mood and energy summary for the current week",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


def log_mood(score: int, context: str = "") -> dict:
    score = max(1, min(10, score))
    today = str(date.today())
    with get_conn() as conn:
        existing = conn.execute("SELECT id, mood_score FROM mood_logs WHERE date = ?", (today,)).fetchone()
        if existing:
            conn.execute("UPDATE mood_logs SET mood_score = ?, context = ? WHERE date = ?", (score, context, today))
            action = "updated"
        else:
            conn.execute("INSERT INTO mood_logs (mood_score, context) VALUES (?,?)", (score, context))
            action = "logged"
    emoji = "🟢" if score >= 7 else "🟡" if score >= 5 else "🔴"
    return {"action": action, "mood": score, "emoji": emoji, "context": context}


def log_energy(score: int, context: str = "") -> dict:
    score = max(1, min(10, score))
    today = str(date.today())
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM mood_logs WHERE date = ?", (today,)).fetchone()
        if existing:
            conn.execute("UPDATE mood_logs SET energy_score = ? WHERE date = ?", (score, today))
            action = "updated"
        else:
            conn.execute("INSERT INTO mood_logs (energy_score) VALUES (?)", (score,))
            action = "logged"
    return {"action": action, "energy": score}


def query_mood(days: int = 7) -> dict:
    start = str(date.today() - timedelta(days=days))
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, mood_score, energy_score, context FROM mood_logs WHERE date >= ? ORDER BY date DESC",
            (start,)
        ).fetchall()
    logs = [{"date": r["date"], "mood": r["mood_score"], "energy": r["energy_score"], "context": r["context"]} for r in rows]
    moods = [r["mood"] for r in rows if r["mood_score"]]
    energies = [r["energy_score"] for r in rows if r["energy_score"]]
    return {
        "days": days,
        "entries": len(logs),
        "avg_mood": round(sum(moods) / len(moods), 1) if moods else None,
        "avg_energy": round(sum(energies) / len(energies), 1) if energies else None,
        "logs": logs
    }


def analyze_mood_patterns(days: int = 30) -> dict:
    start = str(date.today() - timedelta(days=days))
    with get_conn() as conn:
        mood_rows = conn.execute(
            "SELECT date, mood_score, energy_score FROM mood_logs WHERE date >= ? AND mood_score IS NOT NULL ORDER BY date",
            (start,)
        ).fetchall()
    if not mood_rows:
        return {"error": "Not enough data for analysis", "logged_days": 0}
    moods = [r["mood_score"] for r in mood_rows]
    energies = [r["energy_score"] for r in mood_rows if r["energy_score"]]
    avg_mood = sum(moods) / len(moods)
    trend = moods[-7:] if len(moods) >= 7 else moods
    recent_avg = sum(trend) / len(trend)
    return {
        "period_days": days,
        "data_points": len(moods),
        "avg_mood": round(avg_mood, 1),
        "avg_energy": round(sum(energies) / len(energies), 1) if energies else None,
        "recent_7d_avg": round(recent_avg, 1),
        "trend": "improving" if recent_avg > avg_mood + 0.3 else "declining" if recent_avg < avg_mood - 0.3 else "stable",
        "low_days": sum(1 for m in moods if m <= 4),
        "high_days": sum(1 for m in moods if m >= 8),
    }


def get_mood_summary() -> dict:
    start = str(date.today() - timedelta(days=7))
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, mood_score, energy_score FROM mood_logs WHERE date >= ? ORDER BY date",
            (start,)
        ).fetchall()
    moods = [r["mood_score"] for r in rows if r["mood_score"]]
    energies = [r["energy_score"] for r in rows if r["energy_score"]]
    return {
        "week_avg_mood": round(sum(moods) / len(moods), 1) if moods else None,
        "week_avg_energy": round(sum(energies) / len(energies), 1) if energies else None,
        "logged_days": len(rows),
        "today_mood": rows[-1]["mood_score"] if rows else None,
        "today_energy": rows[-1]["energy_score"] if rows else None
    }


TOOL_HANDLERS = {
    "log_mood": lambda args: log_mood(**args),
    "log_energy": lambda args: log_energy(**args),
    "query_mood": lambda args: query_mood(**args),
    "analyze_mood_patterns": lambda args: analyze_mood_patterns(**args),
    "get_mood_summary": lambda args: get_mood_summary(),
}
