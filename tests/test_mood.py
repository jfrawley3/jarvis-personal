import pytest
from tools.mood import log_mood, log_energy, query_mood, analyze_mood_patterns, get_mood_summary


def test_log_mood_returns_score_and_emoji():
    result = log_mood(8, "good day")
    assert result["mood"] == 8
    assert result["emoji"] == "🟢"
    assert result["action"] == "logged"


def test_log_mood_clamps_below_1():
    result = log_mood(-5)
    assert result["mood"] == 1


def test_log_mood_clamps_above_10():
    result = log_mood(15)
    assert result["mood"] == 10


def test_log_mood_yellow_emoji_mid_range():
    result = log_mood(5)
    assert result["emoji"] == "🟡"


def test_log_mood_red_emoji_low():
    result = log_mood(3)
    assert result["emoji"] == "🔴"


def test_log_mood_updates_on_same_day():
    log_mood(5)
    result = log_mood(8)
    assert result["action"] == "updated"
    summary = get_mood_summary()
    assert summary["today_mood"] == 8


def test_log_energy_returns_score():
    log_mood(7)  # create the row first
    result = log_energy(6)
    assert result["energy"] == 6
    assert result["action"] == "updated"


def test_log_energy_creates_new_row_if_no_mood_today():
    result = log_energy(5)
    assert result["action"] == "logged"


def test_query_mood_returns_logged_entries():
    log_mood(7)
    log_energy(6)
    result = query_mood(days=7)
    assert result["entries"] == 1
    assert result["avg_mood"] == 7.0


def test_query_mood_empty_returns_none_averages():
    result = query_mood(days=7)
    assert result["entries"] == 0
    assert result["avg_mood"] is None
    assert result["avg_energy"] is None


def test_analyze_mood_patterns_insufficient_data():
    result = analyze_mood_patterns(days=30)
    assert "error" in result


def test_analyze_mood_patterns_with_data():
    for score in [6, 7, 5, 8, 7, 6, 8]:
        log_mood(score)
    result = analyze_mood_patterns(days=30)
    assert "avg_mood" in result
    assert result["data_points"] == 1  # same day, updates in place


def test_get_mood_summary_empty():
    result = get_mood_summary()
    assert result["week_avg_mood"] is None
    assert result["logged_days"] == 0


def test_get_mood_summary_after_logging():
    log_mood(7)
    log_energy(8)
    result = get_mood_summary()
    assert result["week_avg_mood"] == 7.0
    assert result["week_avg_energy"] == 8.0
    assert result["logged_days"] == 1
    assert result["today_mood"] == 7
