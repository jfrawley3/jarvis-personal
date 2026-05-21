# JARVIS — Personal AI Assistant

A single-user AI assistant running on Claude. Tracks finances, fitness, mood, habits, todos, and more. Interfaces via Telegram bot with a local web dashboard. Includes desktop vision and computer control.

## Features

- **Telegram bot** — message from anywhere, JARVIS responds
- **Finance tracking** — expenses, budgets, alerts at 50/75/90/100%
- **Fitness** — Garmin integration, workout logging
- **Mood & habits** — daily logging, streaks, pattern analysis
- **Todos & goals** — task management with weekly goal setting
- **Life log** — ideas, decisions, social, learnings
- **Desktop vision** — screenshot + webcam capture, Claude sees your screen
- **Computer control** — mouse, keyboard, window automation via PyAutoGUI
- **Scheduler** — morning briefs, budget alerts, smart reminders
- **Web dashboard** — live token usage and event feed

## Stack

- Python 3.11+
- [Anthropic Claude](https://anthropic.com) — Haiku for classification, Sonnet for agent
- FastAPI + Uvicorn — dashboard server
- python-telegram-bot — Telegram interface
- APScheduler — scheduled jobs
- SQLite — persistent storage
- PyAutoGUI + mss + Pillow — desktop tools

## Quick Start

```bash
git clone https://github.com/jfrawley3/jarvis-personal
cd jarvis-personal
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
pip install mss pyautogui pyperclip opencv-python Pillow
cp .env.example .env        # fill in your keys
python main.py
```

## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `TELEGRAM_BOT_TOKEN` | Yes | From @BotFather |
| `TELEGRAM_USER_ID` | Yes | Your Telegram user ID |
| `LOCATION` | No | City for weather (default: New York) |
| `TIMEZONE` | No | pytz string (default: US/Eastern) |
| `CURRENCY` | No | Currency code (default: USD) |

## Desktop Tools

`tools/desktop.py` adds two Claude tools:

- **`capture_screen`** — captures your screen or webcam as a JPEG, returns it to Claude as an image block so it can see what's on screen
- **`computer_control`** — dispatches mouse/keyboard actions (click, type, hotkey, scroll, drag, focus_window, etc.)

Trigger with messages like: *"What's on my screen?"* or *"Click the Start button"*.
