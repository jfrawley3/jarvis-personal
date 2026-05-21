from datetime import date, timedelta
from database import get_conn

TOOL_DEFINITIONS = [
    {
        "name": "add_vocab_word",
        "description": "Add a new word to the vocabulary learning deck",
        "input_schema": {
            "type": "object",
            "properties": {
                "word": {"type": "string"},
                "definition": {"type": "string"},
                "example": {"type": "string", "description": "Example sentence (optional)"}
            },
            "required": ["word", "definition"]
        }
    },
    {
        "name": "check_vocab_answer",
        "description": "Check a vocabulary quiz answer and update spaced repetition schedule",
        "input_schema": {
            "type": "object",
            "properties": {
                "word": {"type": "string"},
                "answer": {"type": "string", "description": "User's answer/definition"},
                "correct": {"type": "boolean", "description": "Whether the answer was correct"}
            },
            "required": ["word", "correct"]
        }
    },
    {
        "name": "get_vocab_due",
        "description": "Get words due for review today based on spaced repetition schedule",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_vocab_stats",
        "description": "Get vocabulary deck statistics: total words, mastered, due today",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_daily_vocab_word",
        "description": "Get today's featured vocabulary word for learning",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


def add_vocab_word(word: str, definition: str, example: str = "") -> dict:
    word = word.lower().strip()
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO vocab_words (word, definition, example) VALUES (?,?,?)",
                (word, definition, example)
            )
            action = "added"
        except Exception:
            conn.execute(
                "UPDATE vocab_words SET definition = ?, example = ? WHERE word = ?",
                (definition, example, word)
            )
            action = "updated"
    return {"action": action, "word": word}


def check_vocab_answer(word: str, correct: bool, answer: str = "") -> dict:
    today = str(date.today())
    word = word.lower().strip()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, correct_count, review_count, mastered FROM vocab_words WHERE word = ?",
            (word,)
        ).fetchone()
        if not row:
            return {"error": f"Word '{word}' not in deck"}
        new_correct = row["correct_count"] + (1 if correct else 0)
        new_reviews = row["review_count"] + 1
        mastered = 1 if new_correct >= 3 else 0
        interval = 1 if not correct else (2 if new_correct < 3 else 7)
        next_review = str(date.today() + timedelta(days=interval))
        conn.execute(
            "UPDATE vocab_words SET correct_count = ?, review_count = ?, mastered = ?, next_review = ? WHERE word = ?",
            (new_correct, new_reviews, mastered, next_review, word)
        )
    return {
        "word": word,
        "correct": correct,
        "correct_streak": new_correct,
        "mastered": bool(mastered),
        "next_review": next_review
    }


def get_vocab_due() -> dict:
    today = str(date.today())
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT word, definition, example, correct_count FROM vocab_words WHERE next_review <= ? AND mastered = 0 ORDER BY next_review LIMIT 10",
            (today,)
        ).fetchall()
    words = [{"word": r["word"], "definition": r["definition"], "example": r["example"], "correct_so_far": r["correct_count"]} for r in rows]
    return {"due_count": len(words), "words": words}


def get_vocab_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM vocab_words").fetchone()[0]
        mastered = conn.execute("SELECT COUNT(*) FROM vocab_words WHERE mastered = 1").fetchone()[0]
        today = str(date.today())
        due = conn.execute("SELECT COUNT(*) FROM vocab_words WHERE next_review <= ? AND mastered = 0", (today,)).fetchone()[0]
    return {"total": total, "mastered": mastered, "learning": total - mastered, "due_today": due}


def get_daily_vocab_word() -> dict:
    today = str(date.today())
    with get_conn() as conn:
        row = conn.execute(
            "SELECT word, definition, example FROM vocab_words WHERE next_review <= ? AND mastered = 0 ORDER BY RANDOM() LIMIT 1",
            (today,)
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT word, definition, example FROM vocab_words ORDER BY RANDOM() LIMIT 1"
            ).fetchone()
    if not row:
        return {"note": "No words in deck. Use add_vocab_word to start building your vocabulary."}
    return {"word": row["word"], "definition": row["definition"], "example": row["example"]}


TOOL_HANDLERS = {
    "add_vocab_word": lambda args: add_vocab_word(**args),
    "check_vocab_answer": lambda args: check_vocab_answer(**args),
    "get_vocab_due": lambda args: get_vocab_due(),
    "get_vocab_stats": lambda args: get_vocab_stats(),
    "get_daily_vocab_word": lambda args: get_daily_vocab_word(),
}
