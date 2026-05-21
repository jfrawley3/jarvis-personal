import pytest
from unittest.mock import patch, MagicMock


def _mock_response(text: str):
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


class TestClassifier:
    def test_finance_intent(self):
        from classifier import classify

        with patch("classifier._client") as mock_client:
            mock_client.messages.create.return_value = _mock_response('{"categories": ["finances"]}')
            result = classify("I spent $50 on groceries")

        assert "finances" in result

    def test_mood_intent(self):
        from classifier import classify

        with patch("classifier._client") as mock_client:
            mock_client.messages.create.return_value = _mock_response('{"categories": ["mood"]}')
            result = classify("I'm feeling really tired today")

        assert "mood" in result

    def test_desktop_intent(self):
        from classifier import classify

        with patch("classifier._client") as mock_client:
            mock_client.messages.create.return_value = _mock_response('{"categories": ["desktop"]}')
            result = classify("What's on my screen right now?")

        assert "desktop" in result

    def test_multi_category_response(self):
        from classifier import classify

        with patch("classifier._client") as mock_client:
            mock_client.messages.create.return_value = _mock_response('{"categories": ["finances", "mood"]}')
            result = classify("spent $30 and feeling stressed about money")

        assert "finances" in result
        assert "mood" in result

    def test_general_fallback_on_greeting(self):
        from classifier import classify

        with patch("classifier._client") as mock_client:
            mock_client.messages.create.return_value = _mock_response('{"categories": ["general"]}')
            result = classify("hey")

        assert result == ["general"]

    def test_fallback_on_api_error(self):
        from classifier import classify

        with patch("classifier._client") as mock_client:
            mock_client.messages.create.side_effect = Exception("API down")
            result = classify("anything")

        assert result == ["general"]

    def test_fallback_on_malformed_json(self):
        from classifier import classify

        with patch("classifier._client") as mock_client:
            mock_client.messages.create.return_value = _mock_response("not json at all")
            result = classify("anything")

        assert result == ["general"]
