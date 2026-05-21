import json
from datetime import date, datetime
from database import get_conn
from config import CURRENCY

TOOL_DEFINITIONS = [
    {
        "name": "add_expense",
        "description": "Log a new expense transaction",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": f"Amount in {CURRENCY}"},
                "category": {"type": "string", "description": "Category: food, transport, shopping, entertainment, health, utilities, other"},
                "note": {"type": "string", "description": "Optional description"}
            },
            "required": ["amount", "category"]
        }
    },
    {
        "name": "query_expenses",
        "description": "Query expenses by date range or category",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD, or 'today', 'yesterday', 'this_month'"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD (optional, defaults to today)"},
                "category": {"type": "string", "description": "Filter by category (optional)"}
            },
            "required": []
        }
    },
    {
        "name": "update_category_budget",
        "description": "Set or update the monthly budget limit for a spending category",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "monthly_limit": {"type": "number", "description": f"Monthly limit in {CURRENCY}"}
            },
            "required": ["category", "monthly_limit"]
        }
    },
    {
        "name": "get_budget_status",
        "description": "Get current month's spending vs budget for each category with alert levels",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_spending_summary",
        "description": "Get total spending summary grouped by category for the current month",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "YYYY-MM format (optional, defaults to current month)"}
            },
            "required": []
        }
    },
    {
        "name": "get_daily_projection",
        "description": "Project month-end total spend based on current daily pace",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "add_income",
        "description": "Log an income entry",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "source": {"type": "string", "description": "e.g. salary, freelance, investment"},
                "note": {"type": "string"}
            },
            "required": ["amount"]
        }
    }
]


def _resolve_date(date_str: str) -> str:
    today = date.today()
    if not date_str or date_str == "today":
        return str(today)
    if date_str == "yesterday":
        from datetime import timedelta
        return str(today - timedelta(days=1))
    if date_str == "this_month":
        return f"{today.year}-{today.month:02d}-01"
    return date_str


def add_expense(amount: float, category: str, note: str = "") -> dict:
    category = category.lower().strip()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO expenses (amount, category, note) VALUES (?,?,?)",
            (amount, category, note)
        )
        row = conn.execute(
            "SELECT SUM(amount) FROM expenses WHERE category = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')",
            (category,)
        ).fetchone()
        mtd = row[0] or 0
        budget_row = conn.execute("SELECT monthly_limit FROM budgets WHERE category = ?", (category,)).fetchone()
        budget = budget_row[0] if budget_row else None
    result = {"logged": True, "amount": amount, "category": category, f"mtd_{category}": round(mtd, 2)}
    if budget:
        pct = (mtd / budget) * 100
        result["budget"] = budget
        result["budget_pct"] = round(pct, 1)
        if pct >= 100:
            result["alert"] = "OVER BUDGET"
        elif pct >= 90:
            result["alert"] = "90% used"
        elif pct >= 75:
            result["alert"] = "75% used"
    return result


def query_expenses(start_date: str = "this_month", end_date: str = "", category: str = "") -> dict:
    start = _resolve_date(start_date)
    end = _resolve_date(end_date) if end_date else str(date.today())
    with get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT date, amount, category, note FROM expenses WHERE date BETWEEN ? AND ? AND category = ? ORDER BY date DESC LIMIT 50",
                (start, end, category.lower())
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT date, amount, category, note FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date DESC LIMIT 50",
                (start, end)
            ).fetchall()
    items = [{"date": r["date"], "amount": r["amount"], "category": r["category"], "note": r["note"]} for r in rows]
    total = sum(i["amount"] for i in items)
    return {"period": f"{start} to {end}", "total": round(total, 2), "count": len(items), "expenses": items}


def update_category_budget(category: str, monthly_limit: float) -> dict:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?,?) ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
            (category.lower(), monthly_limit)
        )
    return {"updated": True, "category": category, "monthly_limit": monthly_limit}


def get_budget_status() -> dict:
    today = date.today()
    month_key = f"{today.year}-{today.month:02d}"
    with get_conn() as conn:
        spending = conn.execute(
            "SELECT category, SUM(amount) as total FROM expenses WHERE strftime('%Y-%m', date) = ? GROUP BY category",
            (month_key,)
        ).fetchall()
        budgets = {r["category"]: r["monthly_limit"] for r in conn.execute("SELECT category, monthly_limit FROM budgets").fetchall()}
    result = {}
    for row in spending:
        cat = row["category"]
        spent = round(row["total"], 2)
        limit = budgets.get(cat)
        entry = {"spent": spent}
        if limit:
            pct = round((spent / limit) * 100, 1)
            entry["budget"] = limit
            entry["pct"] = pct
            if pct >= 100:
                entry["status"] = "OVER"
            elif pct >= 90:
                entry["status"] = "critical"
            elif pct >= 75:
                entry["status"] = "warning"
            else:
                entry["status"] = "ok"
        result[cat] = entry
    return {"month": month_key, "categories": result}


def get_spending_summary(month: str = "") -> dict:
    if not month:
        today = date.today()
        month = f"{today.year}-{today.month:02d}"
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT category, SUM(amount) as total, COUNT(*) as count FROM expenses WHERE strftime('%Y-%m', date) = ? GROUP BY category ORDER BY total DESC",
            (month,)
        ).fetchall()
    cats = [{"category": r["category"], "total": round(r["total"], 2), "transactions": r["count"]} for r in rows]
    grand_total = sum(c["total"] for c in cats)
    return {"month": month, "total": round(grand_total, 2), "by_category": cats}


def get_daily_projection() -> dict:
    today = date.today()
    day_of_month = today.day
    import calendar
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    month_key = f"{today.year}-{today.month:02d}"
    with get_conn() as conn:
        row = conn.execute(
            "SELECT SUM(amount) FROM expenses WHERE strftime('%Y-%m', date) = ?",
            (month_key,)
        ).fetchone()
    mtd = row[0] or 0
    daily_avg = mtd / day_of_month if day_of_month > 0 else 0
    projected = daily_avg * days_in_month
    return {
        "mtd_spend": round(mtd, 2),
        "day_of_month": day_of_month,
        "days_remaining": days_in_month - day_of_month,
        "daily_avg": round(daily_avg, 2),
        "projected_month_total": round(projected, 2)
    }


def add_income(amount: float, source: str = "salary", note: str = "") -> dict:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO income (amount, source, note) VALUES (?,?,?)",
            (amount, source, note)
        )
    return {"logged": True, "amount": amount, "source": source}


TOOL_HANDLERS = {
    "add_expense": lambda args: add_expense(**args),
    "query_expenses": lambda args: query_expenses(**args),
    "update_category_budget": lambda args: update_category_budget(**args),
    "get_budget_status": lambda args: get_budget_status(),
    "get_spending_summary": lambda args: get_spending_summary(**args),
    "get_daily_projection": lambda args: get_daily_projection(),
    "add_income": lambda args: add_income(**args),
}
