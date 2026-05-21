import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_USER_ID = os.getenv("TELEGRAM_USER_ID", "")

DATABASE_PATH = os.getenv("DATABASE_PATH", "jarvis.db")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8000"))
CURRENCY = os.getenv("CURRENCY", "USD")
LOCATION = os.getenv("LOCATION", "New York")
TIMEZONE = os.getenv("TIMEZONE", "US/Eastern")

GARMIN_USERNAME = os.getenv("GARMIN_USERNAME", "")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")
GOOGLE_SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID", "")

CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"
AGENT_MODEL = "claude-sonnet-4-6"

MAX_HISTORY_MESSAGES = 4
MAX_AGENT_TOKENS = 1024
MAX_TOOL_ITERATIONS = 10
