import json
from datetime import date, timedelta
from database import get_conn

TOOL_DEFINITIONS = [
    {
        "name": "get_garmin_summary",
        "description": "Get today's fitness summary from Garmin: steps, sleep, HRV, body battery, distance",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_recent_workouts",
        "description": "List recent workout activities logged (last N days)",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days to look back (default 7)"}
            },
            "required": []
        }
    },
    {
        "name": "suggest_workout",
        "description": "Suggest a workout based on recent activity and recovery status",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "log_fitness_activity",
        "description": "Manually log a workout or fitness activity",
        "input_schema": {
            "type": "object",
            "properties": {
                "activity_type": {"type": "string", "description": "e.g. run, walk, strength, cycling, yoga"},
                "duration_minutes": {"type": "integer"},
                "distance_km": {"type": "number"},
                "notes": {"type": "string"}
            },
            "required": ["activity_type"]
        }
    },
    {
        "name": "get_fitness_trends",
        "description": "Get 7-day fitness trends: steps, sleep, HRV, body battery averages",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


def _get_garmin_data(target_date: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fitness_cache WHERE date = ?", (target_date,)).fetchone()
        if row:
            return dict(row)
    try:
        from garminconnect import Garmin
        from config import GARMIN_USERNAME, GARMIN_PASSWORD
        if not GARMIN_USERNAME or not GARMIN_PASSWORD:
            return None
        client = Garmin(GARMIN_USERNAME, GARMIN_PASSWORD)
        client.login()
        stats = client.get_stats(target_date)
        sleep = client.get_sleep_data(target_date)
        hrv = client.get_hrv_data(target_date)
        data = {
            "date": target_date,
            "steps": stats.get("totalSteps", 0),
            "distance_km": round((stats.get("totalDistanceMeters", 0) or 0) / 1000, 2),
            "active_calories": stats.get("activeKilocalories", 0),
            "body_battery": stats.get("bodyBatteryChargedValue", 0),
            "hrv_ms": hrv.get("lastNight", {}).get("avg5MinHrv", 0) if hrv else 0,
            "resting_hr": stats.get("restingHeartRate", 0),
            "sleep_hours": round((sleep.get("dailySleepDTO", {}).get("sleepTimeSeconds", 0) or 0) / 3600, 1),
        }
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO fitness_cache (date, steps, distance_km, active_calories, body_battery, hrv_ms, resting_hr, sleep_hours)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(date) DO UPDATE SET steps=excluded.steps, distance_km=excluded.distance_km,
                active_calories=excluded.active_calories, body_battery=excluded.body_battery,
                hrv_ms=excluded.hrv_ms, resting_hr=excluded.resting_hr, sleep_hours=excluded.sleep_hours,
                last_updated=CURRENT_TIMESTAMP
            """, (data["date"], data["steps"], data["distance_km"], data["active_calories"],
                  data["body_battery"], data["hrv_ms"], data["resting_hr"], data["sleep_hours"]))
        return data
    except ImportError:
        return None
    except Exception as e:
        return {"error": str(e)}


def get_garmin_summary() -> dict:
    today = str(date.today())
    data = _get_garmin_data(today)
    if not data:
        return {
            "note": "Garmin not configured. Log activity manually with log_fitness_activity.",
            "date": today,
            "steps": None,
            "sleep_hours": None,
            "body_battery": None,
            "hrv_ms": None
        }
    bb = data.get("body_battery", 0)
    recovery = "excellent 🟢" if bb >= 75 else "good 🟢" if bb >= 60 else "moderate 🟡" if bb >= 40 else "low 🔴"
    return {
        "date": today,
        "steps": data.get("steps"),
        "distance_km": data.get("distance_km"),
        "sleep_hours": data.get("sleep_hours"),
        "body_battery": bb,
        "hrv_ms": data.get("hrv_ms"),
        "resting_hr": data.get("resting_hr"),
        "active_calories": data.get("active_calories"),
        "recovery": recovery
    }


def get_recent_workouts(days: int = 7) -> dict:
    start = str(date.today() - timedelta(days=days))
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, habit_name, value FROM habits WHERE habit_name IN ('exercise','run','walk','strength','yoga','cycling') AND date >= ? ORDER BY date DESC",
            (start,)
        ).fetchall()
    workouts = [{"date": r["date"], "type": r["habit_name"], "detail": r["value"]} for r in rows]
    return {"days": days, "workout_count": len(workouts), "workouts": workouts}


def suggest_workout() -> dict:
    today = str(date.today())
    data = _get_garmin_data(today)
    bb = (data or {}).get("body_battery", 70)
    hrv = (data or {}).get("hrv_ms", 50)
    yesterday = str(date.today() - timedelta(days=1))
    with get_conn() as conn:
        recent = conn.execute(
            "SELECT habit_name FROM habits WHERE habit_name IN ('exercise','run','strength') AND date >= ?",
            (yesterday,)
        ).fetchall()
    worked_out_recently = len(recent) > 0
    if bb >= 70 and not worked_out_recently:
        suggestion = {"type": "strength or interval run", "intensity": "high", "note": "Battery high, HRV stable — great time to push."}
    elif bb >= 50 and not worked_out_recently:
        suggestion = {"type": "moderate run or yoga", "intensity": "medium", "note": "Moderate recovery — a steady effort works well."}
    elif worked_out_recently:
        suggestion = {"type": "rest or light walk", "intensity": "low", "note": "You trained recently — active recovery today."}
    else:
        suggestion = {"type": "walk or yoga", "intensity": "low", "note": "Low battery — prioritize recovery."}
    return {"body_battery": bb, "hrv_ms": hrv, "recommendation": suggestion}


def log_fitness_activity(activity_type: str, duration_minutes: int = None, distance_km: float = None, notes: str = "") -> dict:
    detail_parts = []
    if duration_minutes:
        detail_parts.append(f"{duration_minutes}min")
    if distance_km:
        detail_parts.append(f"{distance_km}km")
    if notes:
        detail_parts.append(notes)
    detail = " ".join(detail_parts)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO habits (habit_name, value) VALUES (?,?)",
            (activity_type.lower(), detail)
        )
    return {"logged": True, "activity": activity_type, "detail": detail}


def get_fitness_trends() -> dict:
    rows_data = []
    for i in range(7):
        d = str(date.today() - timedelta(days=i))
        data = _get_garmin_data(d)
        if data and isinstance(data, dict) and "steps" in data:
            rows_data.append(data)
    if not rows_data:
        return {"note": "No Garmin data available. Configure GARMIN_USERNAME and GARMIN_PASSWORD."}
    steps = [r.get("steps", 0) for r in rows_data if r.get("steps")]
    sleep = [r.get("sleep_hours", 0) for r in rows_data if r.get("sleep_hours")]
    hrv = [r.get("hrv_ms", 0) for r in rows_data if r.get("hrv_ms")]
    bb = [r.get("body_battery", 0) for r in rows_data if r.get("body_battery")]
    return {
        "days_with_data": len(rows_data),
        "avg_steps": round(sum(steps) / len(steps)) if steps else None,
        "avg_sleep_h": round(sum(sleep) / len(sleep), 1) if sleep else None,
        "avg_hrv_ms": round(sum(hrv) / len(hrv)) if hrv else None,
        "avg_body_battery": round(sum(bb) / len(bb)) if bb else None,
    }


TOOL_HANDLERS = {
    "get_garmin_summary": lambda args: get_garmin_summary(),
    "get_recent_workouts": lambda args: get_recent_workouts(**args),
    "suggest_workout": lambda args: suggest_workout(),
    "log_fitness_activity": lambda args: log_fitness_activity(**args),
    "get_fitness_trends": lambda args: get_fitness_trends(),
}
