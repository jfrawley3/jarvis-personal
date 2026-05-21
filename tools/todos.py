from datetime import date, datetime
from database import get_conn

TOOL_DEFINITIONS = [
    {
        "name": "add_todo",
        "description": "Add a new todo item or task",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task description"},
                "category": {"type": "string", "description": "Tag/category (optional)"},
                "due_date": {"type": "string", "description": "YYYY-MM-DD (optional)"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "complete_todo",
        "description": "Mark a todo item as completed by ID or title keyword",
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "integer", "description": "Todo ID (preferred)"},
                "title_keyword": {"type": "string", "description": "Keyword from title to find and complete"}
            },
            "required": []
        }
    },
    {
        "name": "list_todos",
        "description": "List todo items, optionally filtered by status or category",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "open, completed, or all (default: open)"},
                "category": {"type": "string", "description": "Filter by category"}
            },
            "required": []
        }
    },
    {
        "name": "delete_todo",
        "description": "Delete a todo item",
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "integer"},
                "title_keyword": {"type": "string"}
            },
            "required": []
        }
    },
    {
        "name": "set_weekly_goals",
        "description": "Set goals for the current week (replaces existing weekly goals)",
        "input_schema": {
            "type": "object",
            "properties": {
                "goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of goal descriptions for the week"
                }
            },
            "required": ["goals"]
        }
    },
    {
        "name": "list_daily_goals",
        "description": "List today's goals and check which are done via habit/todo logs",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_goals_progress",
        "description": "Get progress on all weekly goals with completion status",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


def _week_key() -> str:
    d = date.today()
    return d.strftime("%Y-W%V")


def add_todo(title: str, category: str = "general", due_date: str = None) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO todos (title, category, due_date) VALUES (?,?,?)",
            (title, category or "general", due_date)
        )
    return {"added": True, "id": cur.lastrowid, "title": title}


def complete_todo(todo_id: int = None, title_keyword: str = None) -> dict:
    with get_conn() as conn:
        if todo_id:
            row = conn.execute("SELECT id, title FROM todos WHERE id = ?", (todo_id,)).fetchone()
        elif title_keyword:
            row = conn.execute(
                "SELECT id, title FROM todos WHERE completed = 0 AND title LIKE ? LIMIT 1",
                (f"%{title_keyword}%",)
            ).fetchone()
        else:
            return {"error": "Provide todo_id or title_keyword"}
        if not row:
            return {"error": "Todo not found"}
        conn.execute(
            "UPDATE todos SET completed = 1, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["id"],)
        )
    return {"completed": True, "id": row["id"], "title": row["title"]}


def list_todos(status: str = "open", category: str = None) -> dict:
    with get_conn() as conn:
        if status == "all":
            filter_clause = ""
            params = []
        elif status == "completed":
            filter_clause = "WHERE completed = 1"
            params = []
        else:
            filter_clause = "WHERE completed = 0"
            params = []
        if category:
            filter_clause += " AND category = ?" if "WHERE" in filter_clause else " WHERE category = ?"
            params.append(category)
        rows = conn.execute(
            f"SELECT id, title, category, completed, due_date, created_at FROM todos {filter_clause} ORDER BY created_at DESC LIMIT 30",
            params
        ).fetchall()
    today = str(date.today())
    items = []
    for r in rows:
        item = {"id": r["id"], "title": r["title"], "category": r["category"], "done": bool(r["completed"])}
        if r["due_date"]:
            item["due"] = r["due_date"]
            item["overdue"] = r["due_date"] < today and not r["completed"]
        items.append(item)
    overdue_count = sum(1 for i in items if i.get("overdue"))
    return {"count": len(items), "overdue": overdue_count, "todos": items}


def delete_todo(todo_id: int = None, title_keyword: str = None) -> dict:
    with get_conn() as conn:
        if todo_id:
            row = conn.execute("SELECT id, title FROM todos WHERE id = ?", (todo_id,)).fetchone()
        elif title_keyword:
            row = conn.execute("SELECT id, title FROM todos WHERE title LIKE ? LIMIT 1", (f"%{title_keyword}%",)).fetchone()
        else:
            return {"error": "Provide todo_id or title_keyword"}
        if not row:
            return {"error": "Todo not found"}
        conn.execute("DELETE FROM todos WHERE id = ?", (row["id"],))
    return {"deleted": True, "id": row["id"], "title": row["title"]}


def set_weekly_goals(goals: list) -> dict:
    week = _week_key()
    with get_conn() as conn:
        conn.execute("DELETE FROM todos WHERE week_key = ? AND is_goal = 1", (week,))
        for goal in goals:
            conn.execute(
                "INSERT INTO todos (title, category, week_key, is_goal) VALUES (?,?,?,1)",
                (goal, "weekly_goal", week)
            )
    return {"set": True, "week": week, "goal_count": len(goals), "goals": goals}


def list_daily_goals() -> dict:
    week = _week_key()
    today = str(date.today())
    with get_conn() as conn:
        goals = conn.execute(
            "SELECT id, title, completed FROM todos WHERE (week_key = ? AND is_goal = 1) OR (due_date = ? AND is_goal = 0) ORDER BY id",
            (week, today)
        ).fetchall()
    items = [{"id": r["id"], "goal": r["title"], "done": bool(r["completed"])} for r in goals]
    done_count = sum(1 for i in items if i["done"])
    return {"date": today, "week": week, "total": len(items), "done": done_count, "goals": items}


def get_goals_progress() -> dict:
    week = _week_key()
    with get_conn() as conn:
        goals = conn.execute(
            "SELECT id, title, completed FROM todos WHERE week_key = ? AND is_goal = 1",
            (week,)
        ).fetchall()
    items = [{"id": r["id"], "goal": r["title"], "done": bool(r["completed"])} for r in goals]
    done = sum(1 for i in items if i["done"])
    return {
        "week": week,
        "total": len(items),
        "done": done,
        "remaining": len(items) - done,
        "pct": round((done / len(items)) * 100, 1) if items else 0,
        "goals": items
    }


TOOL_HANDLERS = {
    "add_todo": lambda args: add_todo(**args),
    "complete_todo": lambda args: complete_todo(**args),
    "list_todos": lambda args: list_todos(**args),
    "delete_todo": lambda args: delete_todo(**args),
    "set_weekly_goals": lambda args: set_weekly_goals(**args),
    "list_daily_goals": lambda args: list_daily_goals(),
    "get_goals_progress": lambda args: get_goals_progress(),
}
