import logging
from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

_send_fn = None


def set_send_fn(fn):
    global _send_fn
    _send_fn = fn


async def _send(text: str):
    from config import TELEGRAM_USER_ID
    if _send_fn and TELEGRAM_USER_ID:
        try:
            await _send_fn(TELEGRAM_USER_ID, text)
        except Exception as e:
            logger.error(f"Scheduler send error: {e}")


async def morning_brief():
    try:
        from tools.weather import get_weather, get_literature_quote
        from tools.calendar_tools import query_calendar
        from tools.todos import list_todos
        from tools.finances import get_spending_summary
        from tools.fitness import get_garmin_summary
        from tools.mood import get_mood_summary

        now = datetime.now()
        lines = [f"☀️ Good morning — {now.strftime('%A, %b %d')}"]

        weather = get_weather()
        if "temp_f" in weather:
            lines.append(f"🌡 {weather['temp_f']}°F · {weather['condition']} · {weather['location']}")

        calendar = query_calendar(start_date="today")
        if calendar["events"]:
            lines.append(f"📅 {calendar['count']} event(s) today:")
            for e in calendar["events"][:3]:
                lines.append(f"  • {e['start'][-5:]} {e['title']}")
        else:
            lines.append("📅 No events today")

        todos = list_todos(status="open")
        open_count = todos["count"]
        overdue = todos["overdue"]
        if open_count:
            lines.append(f"✅ {open_count} open todo(s)" + (f" · ⚠️ {overdue} overdue" if overdue else ""))

        fitness = get_garmin_summary()
        if fitness.get("body_battery"):
            lines.append(f"💪 Body battery: {fitness['body_battery']} · Sleep: {fitness.get('sleep_hours', '?')}h")

        summary = get_spending_summary()
        if summary["total"]:
            lines.append(f"💰 MTD spend: ${summary['total']:.2f}")

        quote = get_literature_quote()
        lines.append(f'\n💬 "{quote["quote"]}" — {quote["author"]}')

        await _send("\n".join(lines))
    except Exception as e:
        logger.error(f"Morning brief error: {e}")


async def evening_reminder():
    try:
        from tools.todos import list_todos
        todos = list_todos(status="open")
        lines = ["🌙 Evening check-in"]
        if todos["todos"]:
            lines.append(f"📋 {todos['count']} open todo(s):")
            for t in todos["todos"][:5]:
                marker = "⚠️" if t.get("overdue") else "→"
                lines.append(f"  {marker} {t['title']}")
        else:
            lines.append("✅ All clear — no open todos!")
        lines.append("\nHow are you feeling? (just reply with a number 1-10)")
        await _send("\n".join(lines))
    except Exception as e:
        logger.error(f"Evening reminder error: {e}")


async def goals_check():
    try:
        from tools.todos import get_goals_progress
        progress = get_goals_progress()
        if not progress["goals"]:
            return
        lines = [f"🎯 Daily goals check — {date.today().strftime('%b %d')}"]
        for g in progress["goals"]:
            mark = "✅" if g["done"] else "❌"
            lines.append(f"  {mark} {g['goal']}")
        pct = progress["pct"]
        lines.append(f"\n{pct}% complete ({progress['done']}/{progress['total']})")
        if pct < 50:
            lines.append("Still time to knock one out before bed 💪")
        await _send("\n".join(lines))
    except Exception as e:
        logger.error(f"Goals check error: {e}")


async def budget_pace():
    try:
        from tools.finances import get_budget_status, get_daily_projection
        status = get_budget_status()
        projection = get_daily_projection()
        alerts = []
        for cat, data in status.get("categories", {}).items():
            if data.get("status") in ("OVER", "critical", "warning"):
                pct = data.get("pct", 0)
                alerts.append(f"  {'🔴' if pct >= 90 else '🟡'} {cat}: {pct}% of budget used")
        if alerts:
            lines = ["💸 Budget alert:"] + alerts
            lines.append(f"Projected month-end: ${projection['projected_month_total']:.2f}")
            await _send("\n".join(lines))
    except Exception as e:
        logger.error(f"Budget pace error: {e}")


async def weekly_digest():
    try:
        from tools.finances import get_spending_summary
        from tools.habits import query_habits
        from tools.mood import analyze_mood_patterns
        from tools.fitness import get_fitness_trends
        from tools.todos import get_goals_progress

        lines = [f"📊 Weekly Digest — week of {date.today().strftime('%b %d')}"]

        summary = get_spending_summary()
        if summary["total"]:
            lines.append(f"\n💰 Finances\nMTD: ${summary['total']:.2f}")
            for c in summary["by_category"][:3]:
                lines.append(f"  {c['category']}: ${c['total']:.2f}")

        mood = analyze_mood_patterns(days=7)
        if mood.get("avg_mood"):
            lines.append(f"\n😊 Mood avg: {mood['avg_mood']}/10 · Trend: {mood.get('trend', 'n/a')}")

        habits = query_habits("all", days=7)
        if habits["logs"]:
            habit_names = list({l["habit"] for l in habits["logs"]})
            lines.append(f"\n🔁 Habits logged: {', '.join(habit_names[:5])}")

        fitness = get_fitness_trends()
        if fitness.get("avg_steps"):
            lines.append(f"\n💪 Avg steps: {fitness['avg_steps']:,} · Sleep: {fitness.get('avg_sleep_h')}h")

        goals = get_goals_progress()
        if goals["total"]:
            lines.append(f"\n🎯 Weekly goals: {goals['done']}/{goals['total']} complete")

        await _send("\n".join(lines))
    except Exception as e:
        logger.error(f"Weekly digest error: {e}")


async def vocab_quiz():
    try:
        from tools.vocab import get_vocab_due, get_daily_vocab_word
        due = get_vocab_due()
        if due["due_count"] > 0:
            word = due["words"][0]
            await _send(f"📚 Vocab review: What does **{word['word']}** mean?\n(Reply: check_vocab_answer {word['word']} true/false)")
        else:
            word = get_daily_vocab_word()
            if "word" in word:
                await _send(f"📚 Word of the day: **{word['word']}**\n{word['definition']}\n_{word.get('example', '')}_")
    except Exception as e:
        logger.error(f"Vocab quiz error: {e}")


async def evening_summary():
    try:
        from tools.habits import query_habits
        from tools.finances import query_expenses
        habits = query_habits("all", days=1)
        expenses = query_expenses(start_date="today")
        lines = ["🌙 Day wrap-up"]
        if habits["logs"]:
            names = list({l["habit"] for l in habits["logs"]})
            lines.append(f"✅ Habits: {', '.join(names)}")
        if expenses["total"]:
            lines.append(f"💰 Today's spend: ${expenses['total']:.2f}")
        lines.append("\nHow was your mood today? (1-10)")
        await _send("\n".join(lines))
    except Exception as e:
        logger.error(f"Evening summary error: {e}")


async def garmin_auto_log():
    try:
        from tools.fitness import get_garmin_summary, log_fitness_activity
        from tools.habits import query_habits
        summary = get_garmin_summary()
        if summary.get("distance_km") and summary["distance_km"] > 0:
            today = str(date.today())
            existing = query_habits("run", days=1)
            if not existing["logs"]:
                log_fitness_activity("run", distance_km=summary["distance_km"])
                await _send(f"🏃 Auto-logged: {summary['distance_km']}km run from Garmin")
    except Exception:
        pass


async def weekly_mood_review():
    try:
        from tools.mood import analyze_mood_patterns
        analysis = analyze_mood_patterns(days=7)
        if analysis.get("data_points", 0) < 3:
            return
        lines = [
            "🧠 Weekly mood review",
            f"Avg: {analysis['avg_mood']}/10 · Trend: {analysis.get('trend', 'stable')}",
            f"High days: {analysis['high_days']} · Low days: {analysis['low_days']}",
        ]
        if analysis.get("avg_energy"):
            lines.append(f"Energy avg: {analysis['avg_energy']}/10")
        await _send("\n".join(lines))
    except Exception as e:
        logger.error(f"Mood review error: {e}")


async def study_checkin():
    try:
        from tools.life_log import get_recent_decisions
        from tools.habits import query_habits
        learning = query_habits("study", days=7)
        lines = ["📖 Weekly study check-in"]
        if learning["logged_count"] > 0:
            lines.append(f"✅ Studied {learning['logged_count']} day(s) this week")
        else:
            lines.append("⚠️ No study sessions logged this week")
        lines.append("What did you learn this week? (log_learning to capture it)")
        await _send("\n".join(lines))
    except Exception as e:
        logger.error(f"Study checkin error: {e}")


def _restore_db_reminders():
    try:
        from database import get_conn
        from tools.reminders import _register_with_scheduler
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT job_id, message, schedule_type, fire_time, fire_date FROM reminders WHERE active = 1"
            ).fetchall()
        for r in rows:
            _register_with_scheduler(r["job_id"], r["message"], r["schedule_type"], r["fire_time"], r["fire_date"])
        logger.info(f"Restored {len(rows)} reminder(s) from DB")
    except Exception as e:
        logger.error(f"Reminder restore error: {e}")


def start_scheduler(send_fn=None):
    if send_fn:
        set_send_fn(send_fn)

    from tools.reminders import set_scheduler
    set_scheduler(scheduler)

    scheduler.add_job(morning_brief, CronTrigger(hour=7, minute=0), id="morning_brief", replace_existing=True)
    scheduler.add_job(evening_reminder, CronTrigger(hour=18, minute=0), id="evening_reminder", replace_existing=True)
    scheduler.add_job(goals_check, CronTrigger(hour=21, minute=0), id="goals_check", replace_existing=True)
    scheduler.add_job(budget_pace, CronTrigger(hour=9, minute=15), id="budget_pace", replace_existing=True)
    scheduler.add_job(garmin_auto_log, CronTrigger(minute=0), id="garmin_auto_log", replace_existing=True)
    scheduler.add_job(weekly_digest, CronTrigger(day_of_week="sun", hour=21, minute=0), id="weekly_digest", replace_existing=True)
    scheduler.add_job(vocab_quiz, CronTrigger(hour=8, minute=0), id="vocab_morning", replace_existing=True)
    scheduler.add_job(vocab_quiz, CronTrigger(hour=10, minute=0), id="vocab_mid", replace_existing=True)
    scheduler.add_job(vocab_quiz, CronTrigger(hour=16, minute=0), id="vocab_afternoon", replace_existing=True)
    scheduler.add_job(vocab_quiz, CronTrigger(hour=20, minute=0), id="vocab_evening", replace_existing=True)
    scheduler.add_job(evening_summary, CronTrigger(hour=22, minute=0), id="evening_summary", replace_existing=True)
    scheduler.add_job(weekly_mood_review, CronTrigger(day_of_week="sun", hour=19, minute=0), id="mood_review", replace_existing=True)
    scheduler.add_job(study_checkin, CronTrigger(day_of_week="sun", hour=20, minute=0), id="study_checkin", replace_existing=True)

    if not scheduler.running:
        scheduler.start()
        _restore_db_reminders()
        logger.info("Scheduler started with 13 jobs")
