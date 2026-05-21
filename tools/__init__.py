from tools.finances import TOOL_DEFINITIONS as FINANCE_TOOLS, TOOL_HANDLERS as FINANCE_HANDLERS
from tools.desktop import TOOL_DEFINITIONS as DESKTOP_TOOLS, TOOL_HANDLERS as DESKTOP_HANDLERS
from tools.todos import TOOL_DEFINITIONS as TODO_TOOLS, TOOL_HANDLERS as TODO_HANDLERS
from tools.mood import TOOL_DEFINITIONS as MOOD_TOOLS, TOOL_HANDLERS as MOOD_HANDLERS
from tools.fitness import TOOL_DEFINITIONS as FITNESS_TOOLS, TOOL_HANDLERS as FITNESS_HANDLERS
from tools.habits import TOOL_DEFINITIONS as HABIT_TOOLS, TOOL_HANDLERS as HABIT_HANDLERS
from tools.calendar_tools import TOOL_DEFINITIONS as CALENDAR_TOOLS, TOOL_HANDLERS as CALENDAR_HANDLERS
from tools.life_log import TOOL_DEFINITIONS as LIFELOG_TOOLS, TOOL_HANDLERS as LIFELOG_HANDLERS
from tools.media import TOOL_DEFINITIONS as MEDIA_TOOLS, TOOL_HANDLERS as MEDIA_HANDLERS
from tools.vocab import TOOL_DEFINITIONS as VOCAB_TOOLS, TOOL_HANDLERS as VOCAB_HANDLERS
from tools.weather import TOOL_DEFINITIONS as WEATHER_TOOLS, TOOL_HANDLERS as WEATHER_HANDLERS
from tools.reminders import TOOL_DEFINITIONS as REMINDER_TOOLS, TOOL_HANDLERS as REMINDER_HANDLERS
from tools.personality import TOOL_DEFINITIONS as PERSONALITY_TOOLS, TOOL_HANDLERS as PERSONALITY_HANDLERS

ALL_TOOL_DEFINITIONS: list[dict] = (
    FITNESS_TOOLS +
    FINANCE_TOOLS +
    DESKTOP_TOOLS +
    MOOD_TOOLS +
    TODO_TOOLS +
    CALENDAR_TOOLS +
    HABIT_TOOLS +
    MEDIA_TOOLS +
    VOCAB_TOOLS +
    WEATHER_TOOLS +
    LIFELOG_TOOLS +
    REMINDER_TOOLS +
    PERSONALITY_TOOLS
)

ALL_HANDLERS: dict = {
    **FITNESS_HANDLERS,
    **FINANCE_HANDLERS,
    **DESKTOP_HANDLERS,
    **MOOD_HANDLERS,
    **TODO_HANDLERS,
    **CALENDAR_HANDLERS,
    **HABIT_HANDLERS,
    **MEDIA_HANDLERS,
    **VOCAB_HANDLERS,
    **WEATHER_HANDLERS,
    **LIFELOG_HANDLERS,
    **REMINDER_HANDLERS,
    **PERSONALITY_HANDLERS,
}

CATEGORY_TOOLS: dict[str, list[str]] = {
    "fitness": ["get_garmin_summary", "get_recent_workouts", "suggest_workout", "log_fitness_activity", "get_fitness_trends", "log_habit", "get_habit_streak"],
    "finances": ["add_expense", "query_expenses", "update_category_budget", "get_budget_status", "get_spending_summary", "get_daily_projection", "add_income"],
    "todos": ["add_todo", "complete_todo", "list_todos", "delete_todo", "set_weekly_goals", "list_daily_goals", "get_goals_progress"],
    "mood": ["log_mood", "log_energy", "query_mood", "analyze_mood_patterns", "get_mood_summary"],
    "calendar": ["query_calendar", "add_calendar_event", "list_daily_goals"],
    "habits": ["log_habit", "query_habits", "get_habit_streak", "list_habits"],
    "reminders": ["add_reminder", "list_reminders", "delete_reminder"],
    "weather": ["get_weather", "get_current_time"],
    "news": ["news_digest", "get_literature_quote"],
    "media": ["log_watched", "recommend_media", "get_recently_watched"],
    "vocab": ["add_vocab_word", "check_vocab_answer", "get_vocab_due", "get_vocab_stats", "get_daily_vocab_word"],
    "life_log": ["log_idea", "log_decision", "log_social", "log_learning", "get_recent_ideas", "get_recent_decisions", "search_life_log", "generate_self_portrait"],
    "personality": ["switch_personality", "list_personalities"],
    "desktop": ["capture_screen", "computer_control"],
    "general": ["get_current_time", "list_daily_goals", "get_mood_summary"],
}

ALWAYS_INCLUDE = {"get_current_time"}

_TOOL_DEF_MAP: dict[str, dict] = {t["name"]: t for t in ALL_TOOL_DEFINITIONS}


def get_tools_for_categories(categories: list[str]) -> list[dict]:
    names: set[str] = set(ALWAYS_INCLUDE)
    for cat in categories:
        names.update(CATEGORY_TOOLS.get(cat, []))
    tools = [_TOOL_DEF_MAP[n] for n in names if n in _TOOL_DEF_MAP]
    if tools:
        tools = tools[:-1] + [{**tools[-1], "cache_control": {"type": "ephemeral"}}]
    return tools


def execute_tool(name: str, args: dict) -> any:
    handler = ALL_HANDLERS.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    try:
        return handler(args)
    except Exception as e:
        return {"error": f"{name} failed: {str(e)}"}
