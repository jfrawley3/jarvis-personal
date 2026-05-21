import sqlite3
import json
from contextlib import contextmanager
from config import DATABASE_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                note TEXT DEFAULT '',
                date DATE DEFAULT (date('now')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                monthly_limit REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                source TEXT DEFAULT 'salary',
                note TEXT DEFAULT '',
                date DATE DEFAULT (date('now')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS mood_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mood_score INTEGER,
                energy_score INTEGER,
                context TEXT DEFAULT '',
                date DATE DEFAULT (date('now')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                completed INTEGER DEFAULT 0,
                due_date DATE,
                week_key TEXT,
                is_goal INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            );

            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_datetime TEXT NOT NULL,
                end_datetime TEXT,
                location TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_name TEXT NOT NULL,
                value TEXT DEFAULT '',
                date DATE DEFAULT (date('now')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS media_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                media_type TEXT DEFAULT 'movie',
                rating REAL,
                notes TEXT DEFAULT '',
                date DATE DEFAULT (date('now')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vocab_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL UNIQUE,
                definition TEXT NOT NULL,
                example TEXT DEFAULT '',
                correct_count INTEGER DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                next_review DATE DEFAULT (date('now')),
                mastered INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS fitness_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL UNIQUE,
                steps INTEGER DEFAULT 0,
                distance_km REAL DEFAULT 0,
                active_calories INTEGER DEFAULT 0,
                body_battery INTEGER DEFAULT 0,
                hrv_ms INTEGER DEFAULT 0,
                resting_hr INTEGER DEFAULT 0,
                sleep_hours REAL DEFAULT 0,
                sleep_quality TEXT DEFAULT '',
                workout_summary TEXT DEFAULT '[]',
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS life_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                date DATE DEFAULT (date('now')),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL UNIQUE,
                message TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                fire_time TEXT NOT NULL,
                fire_date TEXT,
                active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS personalities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                system_prompt TEXT NOT NULL,
                is_active INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0,
                cache_write_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        _seed_defaults(conn)


def _seed_defaults(conn):
    existing = conn.execute("SELECT COUNT(*) FROM personalities").fetchone()[0]
    if existing == 0:
        conn.execute("""
            INSERT INTO personalities (name, description, system_prompt, is_active) VALUES
            ('default', 'Efficient and direct', 'You are JARVIS, a sharp and efficient personal assistant. Be concise.', 1),
            ('friendly', 'Warm and encouraging', 'You are JARVIS, a warm and supportive personal assistant. Be encouraging and personable.', 0),
            ('analyst', 'Data-focused insights', 'You are JARVIS in analyst mode. Lead with data, patterns, and metrics. Surface insights the user might miss.', 0)
        """)


def log_token_usage(model: str, input_t: int, output_t: int, cache_read: int, cache_write: int):
    cost = _calc_cost(model, input_t, output_t, cache_read, cache_write)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO token_usage (model, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, cost_usd) VALUES (?,?,?,?,?,?)",
            (model, input_t, output_t, cache_read, cache_write, cost)
        )


def _calc_cost(model: str, input_t: int, output_t: int, cache_read: int, cache_write: int) -> float:
    if "haiku" in model:
        return (input_t * 0.80 + output_t * 4.0 + cache_read * 0.08 + cache_write * 1.0) / 1_000_000
    if "sonnet" in model:
        return (input_t * 3.0 + output_t * 15.0 + cache_read * 0.30 + cache_write * 3.75) / 1_000_000
    return 0.0


def get_today_cost() -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT SUM(cost_usd) FROM token_usage WHERE date(timestamp) = date('now')"
        ).fetchone()
        return round(row[0] or 0.0, 4)


def get_active_personality() -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT name, description, system_prompt FROM personalities WHERE is_active = 1 LIMIT 1"
        ).fetchone()
        if row:
            return dict(row)
        return {"name": "default", "description": "Default", "system_prompt": "You are JARVIS, a personal AI assistant."}


def get_recent_history(user_id: str, limit: int = 4) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def save_message(user_id: str, role: str, content: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES (?,?,?)",
            (user_id, role, content)
        )


def get_event_count() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()
        return row[0]
