import json
import logging
import anthropic
from config import ANTHROPIC_API_KEY, AGENT_MODEL, MAX_HISTORY_MESSAGES, MAX_AGENT_TOKENS, MAX_TOOL_ITERATIONS
from database import get_active_personality, get_recent_history, save_message, log_token_usage
from tools import get_tools_for_categories, execute_tool

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_BASE_SYSTEM = """You are JARVIS (Just A Rather Very Intelligent System), a personal AI assistant.
You are direct, efficient, and action-oriented. Execute tools to log and retrieve data without asking for confirmation on routine operations.
After tool calls, summarize results concisely in 1-3 lines with key numbers. Be conversational but brief.
For multi-action messages (expenses + mood + habits), fire all relevant tools in parallel where possible.
Never say "I'll do that" — just do it. Never apologize for having capabilities."""


def _build_system_prompt() -> list[dict]:
    personality = get_active_personality()
    extra = f"\n\nPersonality ({personality['name']}): {personality['system_prompt']}"
    return [
        {
            "type": "text",
            "text": _BASE_SYSTEM + extra,
            "cache_control": {"type": "ephemeral"}
        }
    ]


def _serialize_content(content_blocks) -> list[dict]:
    result = []
    for block in content_blocks:
        if hasattr(block, "type"):
            if block.type == "text":
                result.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                result.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })
    return result


def process_message(user_id: str, user_message: str, categories: list[str]) -> str:
    history = get_recent_history(user_id, limit=MAX_HISTORY_MESSAGES)
    messages = history + [{"role": "user", "content": user_message}]
    tools = get_tools_for_categories(categories)
    system_prompt = _build_system_prompt()
    iterations = 0
    final_text = ""

    while iterations < MAX_TOOL_ITERATIONS:
        iterations += 1
        try:
            response = _client.messages.create(
                model=AGENT_MODEL,
                max_tokens=MAX_AGENT_TOKENS,
                system=system_prompt,
                tools=tools,
                messages=messages
            )
        except Exception as e:
            logger.error(f"API error: {e}")
            return f"I hit an error: {str(e)}"

        usage = response.usage
        log_token_usage(
            model=AGENT_MODEL,
            input_t=usage.input_tokens,
            output_t=usage.output_tokens,
            cache_read=getattr(usage, "cache_read_input_tokens", 0),
            cache_write=getattr(usage, "cache_creation_input_tokens", 0)
        )

        if response.stop_reason == "end_turn":
            text_parts = [b.text for b in response.content if hasattr(b, "type") and b.type == "text"]
            final_text = " ".join(text_parts)
            break

        if response.stop_reason == "tool_use":
            serialized = _serialize_content(response.content)
            messages.append({"role": "assistant", "content": serialized})

            tool_use_blocks = [b for b in response.content if hasattr(b, "type") and b.type == "tool_use"]
            tool_results = []

            for block in tool_use_blocks:
                logger.info(f"Calling tool: {block.name} with {block.input}")
                result = execute_tool(block.name, block.input)
                # list means rich content (e.g. image blocks from capture_screen)
                if isinstance(result, list):
                    content = result
                elif isinstance(result, (dict,)):
                    content = json.dumps(result)
                else:
                    content = str(result)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        text_parts = [b.text for b in response.content if hasattr(b, "type") and b.type == "text"]
        final_text = " ".join(text_parts) if text_parts else f"Unexpected stop: {response.stop_reason}"
        break

    if not final_text:
        final_text = "Done."

    save_message(user_id, "user", user_message)
    save_message(user_id, "assistant", final_text)
    return final_text
