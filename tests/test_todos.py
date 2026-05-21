import pytest
from tools.todos import (
    add_todo, complete_todo, list_todos, delete_todo,
    set_weekly_goals, get_goals_progress,
)


def test_add_todo_returns_id_and_title():
    result = add_todo("buy groceries")
    assert result["added"] is True
    assert result["id"] is not None
    assert result["title"] == "buy groceries"


def test_add_todo_defaults_category_to_general():
    add_todo("some task")
    result = list_todos()
    assert result["todos"][0]["category"] == "general"


def test_list_todos_shows_open_by_default():
    add_todo("task one")
    add_todo("task two")
    result = list_todos()
    assert result["count"] == 2


def test_list_todos_excludes_completed():
    r = add_todo("task to complete")
    complete_todo(todo_id=r["id"])
    result = list_todos()
    assert result["count"] == 0


def test_list_todos_completed_filter():
    r = add_todo("done task")
    complete_todo(todo_id=r["id"])
    result = list_todos(status="completed")
    assert result["count"] == 1
    assert result["todos"][0]["done"] is True


def test_complete_todo_by_id():
    r = add_todo("finish report")
    result = complete_todo(todo_id=r["id"])
    assert result["completed"] is True
    assert result["id"] == r["id"]


def test_complete_todo_by_title_keyword():
    add_todo("send the invoice")
    result = complete_todo(title_keyword="invoice")
    assert result["completed"] is True
    assert "invoice" in result["title"]


def test_complete_todo_missing_both_args_returns_error():
    result = complete_todo()
    assert "error" in result


def test_complete_todo_not_found_returns_error():
    result = complete_todo(todo_id=9999)
    assert "error" in result


def test_delete_todo_by_id():
    r = add_todo("delete me")
    result = delete_todo(todo_id=r["id"])
    assert result["deleted"] is True
    assert list_todos()["count"] == 0


def test_delete_todo_by_keyword():
    add_todo("remove this item")
    result = delete_todo(title_keyword="remove this")
    assert result["deleted"] is True


def test_delete_todo_not_found_returns_error():
    result = delete_todo(todo_id=9999)
    assert "error" in result


def test_list_todos_filters_by_category():
    add_todo("work task", category="work")
    add_todo("home task", category="home")
    result = list_todos(category="work")
    assert result["count"] == 1
    assert result["todos"][0]["category"] == "work"


def test_set_weekly_goals_creates_goals():
    result = set_weekly_goals(["exercise", "read 30 min", "no junk food"])
    assert result["set"] is True
    assert result["goal_count"] == 3


def test_set_weekly_goals_replaces_existing():
    set_weekly_goals(["old goal"])
    set_weekly_goals(["new goal one", "new goal two"])
    progress = get_goals_progress()
    assert progress["total"] == 2


def test_get_goals_progress_starts_at_zero():
    set_weekly_goals(["goal a", "goal b"])
    result = get_goals_progress()
    assert result["done"] == 0
    assert result["remaining"] == 2
    assert result["pct"] == 0


def test_get_goals_progress_updates_on_complete():
    set_weekly_goals(["finish tests"])
    goals = get_goals_progress()
    complete_todo(todo_id=goals["goals"][0]["id"])
    result = get_goals_progress()
    assert result["done"] == 1
    assert result["pct"] == 100.0
