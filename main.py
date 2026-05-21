import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import DASHBOARD_PORT, TELEGRAM_BOT_TOKEN
from database import init_db, get_event_count, get_today_cost

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger("jarvis")

_ws_clients: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("JARVIS starting up...")
    init_db()

    from telegram_bot import start_bot_in_thread, send_message
    start_bot_in_thread()

    from scheduler import start_scheduler
    start_scheduler(send_fn=send_message)

    logger.info("✓ JARVIS ready")
    yield
    logger.info("JARVIS shutting down")
    from scheduler import scheduler
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(title="JARVIS", version="1.0.0", lifespan=lifespan)

try:
    app.mount("/static", StaticFiles(directory="dashboard"), name="static")
except Exception:
    pass


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    try:
        with open("dashboard/index.html") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>JARVIS</h1><p>Dashboard not found.</p>"


@app.get("/api/status")
async def status():
    from tools import ALL_TOOL_DEFINITIONS
    from database import get_conn
    with get_conn() as conn:
        today_calls = conn.execute(
            "SELECT COUNT(*) FROM token_usage WHERE date(timestamp) = date('now')"
        ).fetchone()[0]
    return {
        "status": "online",
        "version": "1.0.0",
        "tools": len(ALL_TOOL_DEFINITIONS),
        "messages": get_event_count(),
        "today_api_calls": today_calls,
        "today_cost_usd": get_today_cost(),
        "telegram": bool(TELEGRAM_BOT_TOKEN)
    }


@app.get("/api/dashboard")
async def dashboard_data():
    from database import get_conn
    from tools.finances import get_spending_summary, get_budget_status
    from tools.fitness import get_garmin_summary
    from tools.mood import get_mood_summary
    from tools.habits import list_habits
    from tools.todos import list_todos
    from tools.vocab import get_vocab_stats

    try:
        with get_conn() as conn:
            recent_events = conn.execute(
                "SELECT timestamp, content FROM conversations WHERE role = 'user' ORDER BY timestamp DESC LIMIT 5"
            ).fetchall()
            costs = conn.execute(
                "SELECT date(timestamp) as d, SUM(cost_usd) as c FROM token_usage GROUP BY d ORDER BY d DESC LIMIT 7"
            ).fetchall()
            habit_rows = conn.execute(
                "SELECT habit_name, COUNT(*) as c FROM habits WHERE date >= date('now', '-7 days') GROUP BY habit_name ORDER BY c DESC LIMIT 5"
            ).fetchall()

        return {
            "status": "ok",
            "finances": get_spending_summary(),
            "budget": get_budget_status(),
            "fitness": get_garmin_summary(),
            "mood": get_mood_summary(),
            "habits": {"top": [{"habit": r["habit_name"], "days": r["c"]} for r in habit_rows]},
            "todos": list_todos(),
            "vocab": get_vocab_stats(),
            "cost_7d": [{"date": r["d"], "cost": round(r["c"], 4)} for r in costs],
            "recent_messages": [{"time": r["timestamp"][-8:-3], "msg": r["content"][:60]} for r in recent_events],
        }
    except Exception as e:
        return {"error": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        _ws_clients.remove(websocket) if websocket in _ws_clients else None


async def broadcast(event: dict):
    dead = []
    for ws in _ws_clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=DASHBOARD_PORT,
        reload=False,
        log_level="info"
    )
