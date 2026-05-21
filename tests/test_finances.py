import pytest
from tools.finances import (
    add_expense, query_expenses, update_category_budget,
    get_budget_status, get_spending_summary, get_daily_projection, add_income,
)


def test_add_expense_logs_and_returns_amount():
    result = add_expense(25.50, "food", "lunch")
    assert result["logged"] is True
    assert result["amount"] == 25.50
    assert result["category"] == "food"


def test_add_expense_normalises_category_to_lowercase():
    result = add_expense(10, "FOOD")
    assert result["category"] == "food"


def test_add_expense_tracks_month_to_date():
    add_expense(20, "food")
    result = add_expense(30, "food")
    assert result["mtd_food"] == pytest.approx(50.0)


def test_add_expense_budget_alert_at_90_percent():
    update_category_budget("food", 100)
    add_expense(50, "food")
    result = add_expense(45, "food")
    assert "alert" in result
    assert "90" in result["alert"]


def test_add_expense_budget_alert_over_100_percent():
    update_category_budget("food", 50)
    result = add_expense(60, "food")
    assert result["alert"] == "OVER BUDGET"


def test_add_expense_no_alert_under_75_percent():
    update_category_budget("food", 100)
    result = add_expense(50, "food")
    assert "alert" not in result


def test_query_expenses_returns_logged_items():
    add_expense(15, "food", "coffee")
    add_expense(40, "transport", "uber")
    result = query_expenses(start_date="this_month")
    assert result["count"] == 2
    assert result["total"] == pytest.approx(55.0)


def test_query_expenses_filters_by_category():
    add_expense(15, "food")
    add_expense(40, "transport")
    result = query_expenses(start_date="this_month", category="food")
    assert result["count"] == 1
    assert result["expenses"][0]["category"] == "food"


def test_query_expenses_empty_when_nothing_logged():
    result = query_expenses(start_date="this_month")
    assert result["count"] == 0
    assert result["total"] == 0


def test_update_category_budget_sets_limit():
    result = update_category_budget("food", 500)
    assert result["updated"] is True
    assert result["monthly_limit"] == 500


def test_update_category_budget_overwrites_existing():
    update_category_budget("food", 200)
    update_category_budget("food", 400)
    status = get_budget_status()
    # Add a spend to make the category appear in budget status
    add_expense(10, "food")
    status = get_budget_status()
    assert status["categories"]["food"]["budget"] == 400


def test_get_budget_status_shows_ok_under_75():
    update_category_budget("food", 100)
    add_expense(50, "food")
    result = get_budget_status()
    assert result["categories"]["food"]["status"] == "ok"


def test_get_budget_status_shows_warning_at_75():
    update_category_budget("food", 100)
    add_expense(80, "food")
    result = get_budget_status()
    assert result["categories"]["food"]["status"] == "warning"


def test_get_budget_status_shows_over():
    update_category_budget("food", 100)
    add_expense(110, "food")
    result = get_budget_status()
    assert result["categories"]["food"]["status"] == "OVER"


def test_get_spending_summary_groups_by_category():
    add_expense(20, "food")
    add_expense(30, "food")
    add_expense(50, "transport")
    result = get_spending_summary()
    cats = {c["category"]: c["total"] for c in result["by_category"]}
    assert cats["food"] == pytest.approx(50.0)
    assert cats["transport"] == pytest.approx(50.0)
    assert result["total"] == pytest.approx(100.0)


def test_get_daily_projection_returns_expected_keys():
    add_expense(30, "food")
    result = get_daily_projection()
    assert "mtd_spend" in result
    assert "daily_avg" in result
    assert "projected_month_total" in result
    assert result["mtd_spend"] == pytest.approx(30.0)


def test_add_income_logs_correctly():
    result = add_income(2000, "salary", "may paycheck")
    assert result["logged"] is True
    assert result["amount"] == 2000
    assert result["source"] == "salary"
