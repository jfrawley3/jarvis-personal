from database import get_conn

TOOL_DEFINITIONS = [
    {
        "name": "switch_personality",
        "description": "Switch JARVIS to a different personality profile (changes tone and response style)",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Personality name: default, friendly, analyst"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "list_personalities",
        "description": "List all available personality profiles",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]


def switch_personality(name: str) -> dict:
    name = name.lower().strip()
    with get_conn() as conn:
        row = conn.execute("SELECT id, description FROM personalities WHERE name = ?", (name,)).fetchone()
        if not row:
            return {"error": f"Personality '{name}' not found. Use list_personalities to see options."}
        conn.execute("UPDATE personalities SET is_active = 0")
        conn.execute("UPDATE personalities SET is_active = 1 WHERE name = ?", (name,))
    return {"switched": True, "active": name, "description": row["description"]}


def list_personalities() -> dict:
    with get_conn() as conn:
        rows = conn.execute("SELECT name, description, is_active FROM personalities ORDER BY id").fetchall()
    profiles = [{"name": r["name"], "description": r["description"], "active": bool(r["is_active"])} for r in rows]
    active = next((p["name"] for p in profiles if p["active"]), "default")
    return {"active": active, "profiles": profiles}


TOOL_HANDLERS = {
    "switch_personality": lambda args: switch_personality(**args),
    "list_personalities": lambda args: list_personalities(),
}
