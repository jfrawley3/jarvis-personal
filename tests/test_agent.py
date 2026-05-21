import pytest
from unittest.mock import patch, MagicMock, call


def _text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp = MagicMock()
    resp.stop_reason = "end_turn"
    resp.content = [block]
    resp.usage = MagicMock(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0)
    return resp


def _tool_use_response(tool_name: str, tool_input: dict, tool_id: str = "tu_1"):
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = tool_id
    tool_block.name = tool_name
    tool_block.input = tool_input

    resp = MagicMock()
    resp.stop_reason = "tool_use"
    resp.content = [tool_block]
    resp.usage = MagicMock(input_tokens=20, output_tokens=10, cache_read_input_tokens=0, cache_creation_input_tokens=0)
    return resp


class TestAgentLoop:
    def test_simple_text_response(self):
        from agent import process_message

        with patch("agent._client") as mock_client:
            mock_client.messages.create.return_value = _text_response("Hello! How can I help?")
            result = process_message("user1", "hi", ["general"])

        assert "Hello" in result

    def test_tool_call_and_followup(self):
        from agent import process_message

        tool_resp = _tool_use_response("add_expense", {"amount": 20, "category": "food"})
        final_resp = _text_response("Logged $20 for food.")

        with patch("agent._client") as mock_client, \
             patch("agent.execute_tool", return_value={"logged": True, "amount": 20}) as mock_tool:
            mock_client.messages.create.side_effect = [tool_resp, final_resp]
            result = process_message("user1", "I spent $20 on food", ["finances"])

        mock_tool.assert_called_once_with("add_expense", {"amount": 20, "category": "food"})
        assert "Logged" in result

    def test_tool_result_passed_back_to_api(self):
        from agent import process_message

        tool_resp = _tool_use_response("get_budget_status", {})
        final_resp = _text_response("You're on track this month.")

        with patch("agent._client") as mock_client, \
             patch("agent.execute_tool", return_value={"month": "2026-05", "categories": {}}):
            mock_client.messages.create.side_effect = [tool_resp, final_resp]
            process_message("user1", "how's my budget?", ["finances"])

        # Second API call should include a tool_result message
        second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        tool_result_msg = second_call_messages[-1]
        assert tool_result_msg["role"] == "user"
        assert tool_result_msg["content"][0]["type"] == "tool_result"

    def test_image_tool_result_passed_as_list(self):
        from agent import process_message

        tool_resp = _tool_use_response("capture_screen", {})
        final_resp = _text_response("I can see Outlook on your screen.")

        image_result = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "abc123"}},
            {"type": "text", "text": "Screenshot captured."},
        ]

        with patch("agent._client") as mock_client, \
             patch("agent.execute_tool", return_value=image_result):
            mock_client.messages.create.side_effect = [tool_resp, final_resp]
            process_message("user1", "what's on my screen?", ["desktop"])

        second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]
        tool_result_content = second_call_messages[-1]["content"][0]["content"]
        # Image results should be passed as a list, not json-serialised
        assert isinstance(tool_result_content, list)
        assert tool_result_content[0]["type"] == "image"

    def test_api_error_returns_friendly_message(self):
        from agent import process_message

        with patch("agent._client") as mock_client:
            mock_client.messages.create.side_effect = Exception("network error")
            result = process_message("user1", "hello", ["general"])

        assert "error" in result.lower()

    def test_saves_conversation_history(self):
        from agent import process_message

        with patch("agent._client") as mock_client, \
             patch("agent.save_message") as mock_save:
            mock_client.messages.create.return_value = _text_response("Done.")
            process_message("user1", "test message", ["general"])

        calls = [c[0] for c in mock_save.call_args_list]
        assert ("user1", "user", "test message") in calls
        assert ("user1", "assistant", "Done.") in calls

    def test_max_iterations_guard(self):
        """Agent should stop after MAX_TOOL_ITERATIONS even if keep getting tool_use."""
        from agent import process_message
        import config

        looping_tool_resp = _tool_use_response("get_budget_status", {})

        with patch("agent._client") as mock_client, \
             patch("agent.execute_tool", return_value={}), \
             patch("agent.save_message"):
            mock_client.messages.create.return_value = looping_tool_resp
            result = process_message("user1", "loop forever", ["finances"])

        assert mock_client.messages.create.call_count == config.MAX_TOOL_ITERATIONS
