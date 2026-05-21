import httpx
import logging
import asyncio
import threading
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, OPENAI_API_KEY

logger = logging.getLogger(__name__)
_application: Application | None = None


def _is_authorized(user_id: int) -> bool:
    if not TELEGRAM_USER_ID:
        return True
    return str(user_id) == str(TELEGRAM_USER_ID)


async def send_message(user_id: str | int, text: str):
    if _application:
        await _application.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")


async def _transcribe_voice(file_path: str) -> str | None:
    if not OPENAI_API_KEY:
        return None
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        with open(file_path, "rb") as f:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
        return transcript.text
    except Exception as e:
        logger.error(f"Whisper error: {e}")
        return None


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text(
        "JARVIS online.\n\n"
        "I can help with:\n"
        "• 💪 Fitness — log workouts, check Garmin\n"
        "• 💰 Finances — track expenses, budgets\n"
        "• ✅ Todos — tasks, goals\n"
        "• 😊 Mood — log feelings and energy\n"
        "• 📅 Calendar — events and schedule\n"
        "• 📚 Vocab — learning and spaced repetition\n"
        "• 💡 Life log — ideas, decisions, learning\n\n"
        "Just send a natural language message or voice note."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    await update.message.reply_text(
        "Commands:\n"
        "/start — Initialize\n"
        "/help — This message\n"
        "/status — System status\n"
        "/cost — Today's API cost\n\n"
        "Or just talk naturally:\n"
        "\"ran 5km today\"\n"
        "\"spent $45 on groceries\"\n"
        "\"feeling tired, mood 4/10\"\n"
        "\"add dentist appointment Thursday 2pm\""
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    from database import get_event_count, get_today_cost
    count = get_event_count()
    cost = get_today_cost()
    from tools import ALL_TOOL_DEFINITIONS
    await update.message.reply_text(
        f"✅ JARVIS online\n"
        f"🔧 {len(ALL_TOOL_DEFINITIONS)} tools ready\n"
        f"💬 {count} total messages\n"
        f"💵 Today's cost: ${cost:.4f}"
    )


async def cmd_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    from database import get_conn
    with get_conn() as conn:
        today = conn.execute(
            "SELECT SUM(cost_usd) as total, COUNT(*) as calls FROM token_usage WHERE date(timestamp) = date('now')"
        ).fetchone()
        month = conn.execute(
            "SELECT SUM(cost_usd) as total, COUNT(*) as calls FROM token_usage WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')"
        ).fetchone()
    await update.message.reply_text(
        f"💵 API Cost\n"
        f"Today: ${(today['total'] or 0):.4f} ({today['calls']} calls)\n"
        f"This month: ${(month['total'] or 0):.4f} ({month['calls']} calls)"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    user_id = str(update.effective_user.id)
    message = update.message.text
    await update.message.chat.send_action("typing")
    try:
        from classifier import classify
        from agent import process_message
        categories = classify(message)
        logger.info(f"Categories: {categories}")
        response = process_message(user_id, message, categories)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Message handling error: {e}", exc_info=True)
        await update.message.reply_text(f"Something went wrong: {str(e)[:200]}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update.effective_user.id):
        return
    user_id = str(update.effective_user.id)
    await update.message.chat.send_action("typing")

    if not OPENAI_API_KEY:
        await update.message.reply_text("Voice notes require OPENAI_API_KEY. Set it in .env to enable transcription.")
        return

    import tempfile, os
    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        await voice_file.download_to_drive(tmp_path)
        transcript = await _transcribe_voice(tmp_path)
    finally:
        os.unlink(tmp_path)

    if not transcript:
        await update.message.reply_text("Could not transcribe voice note.")
        return

    try:
        from classifier import classify
        from agent import process_message
        categories = classify(transcript)
        response = process_message(user_id, transcript, categories)
        await update.message.reply_text(f"[{transcript}]\n\n{response}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Voice handling error: {e}", exc_info=True)
        await update.message.reply_text(f"Error processing voice note: {str(e)[:200]}")


def start_bot_in_thread():
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")
        return

    def run():
        global _application
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        _application = app

        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("help", cmd_help))
        app.add_handler(CommandHandler("status", cmd_status))
        app.add_handler(CommandHandler("cost", cmd_cost))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(MessageHandler(filters.VOICE, handle_voice))

        logger.info("Telegram bot starting...")
        app.run_polling(stop_signals=None)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    logger.info("Telegram bot thread launched")
