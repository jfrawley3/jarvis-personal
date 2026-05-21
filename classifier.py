import json
import anthropic
from config import ANTHROPIC_API_KEY, CLASSIFIER_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_SYSTEM = """You are an intent classifier for JARVIS, a personal AI assistant.
Given a user message, return a JSON object with the categories that apply.

Categories:
- fitness: exercise, workouts, steps, sleep, Garmin, running, gym, calories burned
- finances: expenses, spending, budget, money, cost, purchase, income
- todos: tasks, todo, to-do, goals, complete, done, finish, add task
- mood: feeling, mood, emotion, energy, stress, happy, tired, anxious
- calendar: schedule, event, appointment, meeting, today's plan
- habits: habit, streak, daily routine, meditation, reading, practice
- reminders: remind me, set reminder, notification, alert
- weather: weather, temperature, forecast, rain
- news: news, headlines, what's happening
- media: movie, show, book, watched, read, recommend
- vocab: word, vocabulary, definition, learn word, quiz
- life_log: idea, decision, thought, realized, social, met with, learned, insight
- personality: personality, tone, mode, style
- desktop: screen, click, type, move mouse, open app, take screenshot, what's on my screen, control computer
- general: greeting, status, how are you, help, what can you do

Return ONLY valid JSON like: {"categories": ["finances", "mood"]}
Pick 1-3 most relevant categories. If truly general/greeting, return ["general"]."""


def classify(message: str) -> list[str]:
    try:
        resp = _client.messages.create(
            model=CLASSIFIER_MODEL,
            max_tokens=64,
            system=_SYSTEM,
            messages=[{"role": "user", "content": message}]
        )
        text = resp.content[0].text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])
        return data.get("categories", ["general"])
    except Exception:
        return ["general"]
