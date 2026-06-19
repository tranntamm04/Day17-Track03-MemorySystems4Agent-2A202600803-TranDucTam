from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens
from model_provider import build_chat_model


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    """Student TODO: implement Agent A.

    Requirements:
    - Within-session memory only
    - No persistent `User.md`
    - Should forget long-term facts across new threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}

        self.langchain_agent = None if force_offline else self._maybe_build_langchain_agent()

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: return the agent response and token accounting.

        Pseudocode:
        - If a live agent exists, call the live path.
        - Otherwise use a deterministic offline path.
        """

        return self._reply_offline(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        # Baseline has no compact memory.
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement a simple offline behavior.

        Suggested behavior:
        - Store the new user message in the session
        - Generate a short deterministic reply
        - Update token counts
        - Never remember facts across different thread ids
        """

        state = self.sessions.setdefault(thread_id, SessionState())
        state.messages.append({"role": "user", "content": message})
        prompt_context = "\n".join(item["content"] for item in state.messages)
        state.prompt_tokens_processed += estimate_tokens(prompt_context)

        answer = self._offline_response_from_thread(state.messages, message)
        state.messages.append({"role": "assistant", "content": answer})
        answer_tokens = estimate_tokens(answer)
        state.token_usage += answer_tokens
        return {
            "answer": answer,
            "agent_tokens": answer_tokens,
            "prompt_tokens": estimate_tokens(prompt_context),
        }

    def _maybe_build_langchain_agent(self):
        """Student TODO: optionally wire `create_agent` + `InMemorySaver` here.

        Use `build_chat_model(self.config.model)` so the baseline can run with any supported provider.
        """

        try:
            return build_chat_model(self.config.model)
        except Exception:
            return None

    def _offline_response_from_thread(self, messages: list[dict[str, str]], message: str) -> str:
        lower = message.lower()
        if any(phrase in lower for phrase in ["tên", "đồ uống", "style", "ở đâu", "nghề", "nuôi", "món ăn"]):
            known = []
            for item in messages:
                if item["role"] == "user" and _looks_like_fact(item["content"]):
                    known.append(item["content"])
            if known:
                return "Trong thread này mình thấy: " + " ".join(known[-3:])
            return "Mình chưa có thông tin đó trong thread hiện tại."
        return "Mình đã ghi nhận trong thread hiện tại."


def _looks_like_fact(text: str) -> bool:
    lower = text.lower()
    markers = [
        "mình tên",
        "mình ở",
        "mình đang ở",
        "mình đang làm",
        "đồ uống yêu thích",
        "món ăn yêu thích",
        "mình thích",
        "muốn bạn trả lời",
        "3 bullet",
        "nuôi",
    ]
    return any(marker in lower for marker in markers)
