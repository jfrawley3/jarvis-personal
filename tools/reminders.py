import uuid
from datetime import datetime
from database import get_conn

TOOL_DEFINITIONS = [
    {
        "name": "add_reminder",
        "description": "Set a recurring or one-time reminder that fires via Telegram",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Reminder message to send"},
                "time": {"type": "string", "description": "HH:MM (24h format)"},
                "schedule": {"type": "string", "description": "daily, weekdays, or once"},
                "date": {"type": "string", "description": "YYYY-MM-DD — required if schedule is 'once'"}
            },
            "required": ["message", "time", "schedule"]
        }
    },
    {
        "name": "list_reminders",
        "description": "List all active reminders",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "delete_reminder",
        "description": "Delete a reminder by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "reminder_id": {"type": "integer"}
            },
            "required": ["reminder_id"]
        }
    }
]

_scheduler_ref = None


def set_scheduler(scheduler):
    global _scheduler_ref
    _scheduler_ref = scheduler


def _register_with_scheduler(job_id: str, message: str, schedule_type: str, fire_time: str, fire_date: str = None):
    if not _scheduler_ref:
        return
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from config import TELEGRAM_USER_ID
    hour, minute = map(int, fire_time.split(":"))

    async def send_reminder():
        from telegram_bot import send_message
        await send_message(TELEGRAM_USER_ID, f"⏰ {message}")

    if schedule_type == "daily":
        trigger = CronTrigger(hour=hour, minute=minute)
    elif schedule_type == "weekdays":
        trigger = CronTrigger(day_of_week="mon-fri", hour=hour, minute=minute)
    elif schedule_type == "once" and fire_date:
        from datetime import datetime
        dt = datetime.strptime(f"{fire_date} {fire_time}", "%Y-%m-%d %H:%M")
        trigger = DateTrigger(run_date=dt)
    else:
        return

    try:
        _scheduler_ref.add_job(send_reminder, trigger=trigger, id=job_id, replace_existing=True)
    except Exception:
        pass


def add_reminder(message: str, time: str, schedule: str, date: str = None) -> dict:
    job_id = f"reminder_{uuid.uuid4().hex[:8]}"
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (job_id, message, schedule_type, fire_time, fire_date) VALUES (?,?,?,?,?)",
            (job_id, message, schedule, time, date)
        )
        rid = cur.lastrowid
    _register_with_scheduler(job_id, message, schedule, time, date)
    return {"added": True, "id": rid, "message": message, "time": time, "schedule": schedule}


def list_reminders() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, message, schedule_type, fire_time, fire_date, active FROM reminders WHERE active = 1 ORDER BY fire_time"
        ).fetchall()
    reminders = [
        {"id": r["id"], "message": r["message"], "schedule": r["schedule_type"], "time": r["fire_time"], "date": r["fire_date"]}
        for r in rows
    ]
    return {"count": len(reminders), "reminders": reminders}


def delete_reminder(reminder_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT job_id, message FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
        if not row:
            return {"error": "Reminder not found"}
        conn.execute("UPDATE reminders SET active = 0 WHERE id = ?", (reminder_id,))
        job_id = row["job_id"]
    if _scheduler_ref:
        try:
            _scheduler_ref.remove_job(job_id)
        except Exception:
            pass
    return {"deleted": True, "id": reminder_id}


TOOL_HANDLERS = {
    "add_reminder": lambda args: add_reminder(**args),
    "list_reminders": lambda args: list_reminders(),
    "delete_reminder": lambda args: delete_reminder(**args),
}
