import pytest
from unittest.mock import patch, MagicMock


def _fake_results():
    return [
        {"title": "Result One", "href": "https://example.com/1", "body": "First result snippet."},
        {"title": "Result Two", "href": "https://example.com/2", "body": "Second result snippet."},
    ]


class TestWebSearch:
    def test_returns_results_structure(self):
        from tools.web_search import web_search

        with patch("tools.web_search.DDGS") as MockDDGS:
            MockDDGS.return_value.__enter__.return_value.text.return_value = _fake_results()
            result = web_search("test query")

        assert result["query"] == "test query"
        assert result["count"] == 2
        assert result["results"][0]["title"] == "Result One"
        assert result["results"][0]["url"] == "https://example.com/1"
        assert result["results"][0]["snippet"] == "First result snippet."

    def test_max_results_capped_at_10(self):
        from tools.web_search import web_search

        with patch("tools.web_search.DDGS") as MockDDGS:
            mock_ddgs = MockDDGS.return_value.__enter__.return_value
            mock_ddgs.text.return_value = _fake_results()
            web_search("query", max_results=50)

        _, kwargs = mock_ddgs.text.call_args
        assert kwargs["max_results"] <= 10

    def test_timelimit_passed_through(self):
        from tools.web_search import web_search

        with patch("tools.web_search.DDGS") as MockDDGS:
            mock_ddgs = MockDDGS.return_value.__enter__.return_value
            mock_ddgs.text.return_value = _fake_results()
            web_search("news query", timelimit="d")

        _, kwargs = mock_ddgs.text.call_args
        assert kwargs["timelimit"] == "d"

    def test_empty_results_returns_empty_list(self):
        from tools.web_search import web_search

        with patch("tools.web_search.DDGS") as MockDDGS:
            MockDDGS.return_value.__enter__.return_value.text.return_value = []
            result = web_search("obscure query")

        assert result["count"] == 0
        assert result["results"] == []

    def test_ddgs_exception_returns_error(self):
        from tools.web_search import web_search

        with patch("tools.web_search.DDGS") as MockDDGS:
            MockDDGS.return_value.__enter__.return_value.text.side_effect = Exception("rate limited")
            result = web_search("query")

        assert "error" in result
        assert "rate limited" in result["error"]

    def test_ddgs_unavailable_returns_error(self):
        from tools.web_search import web_search

        with patch("tools.web_search._DDGS", False):
            result = web_search("query")

        assert "error" in result
