from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_updates
from model_provider import build_chat_model


@dataclass
class AgentContext:
    user_id: str
    memory_path: str


class AdvancedAgent:
    """Student TODO: implement Agent B / Advanced Agent.

    Required memory layers:
    1. within-session memory
    2. persistent `User.md`
    3. compact memory for long threads
    """

    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}

        self.langchain_agent = None if force_offline else self._maybe_build_langchain_agent()

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: route between offline mode and live mode."""

        return self._reply_offline(user_id, thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        """Student TODO: implement the deterministic advanced path.

        Pseudocode:
        1. Extract stable profile facts from the incoming message.
        2. Persist those facts into `User.md`.
        3. Append the message into compact memory.
        4. Estimate prompt-context load from `User.md` + summary + recent messages.
        5. Generate a response that can answer long-term recall questions.
        6. Append the assistant reply and update token counters.
        """

        for key, update in extract_profile_updates(message).items():
            self.profile_store.upsert_fact(
                user_id,
                _fact_label(key),
                update.value,
                confidence=update.confidence,
                source=update.source,
                is_correction=update.is_correction,
            )

        self.compact_memory.append(thread_id, "user", message)
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id)
        self.thread_prompt_tokens[thread_id] = self.thread_prompt_tokens.get(thread_id, 0) + prompt_tokens

        answer = self._offline_response(user_id, thread_id, message)
        self.compact_memory.append(thread_id, "assistant", answer)
        answer_tokens = estimate_tokens(answer)
        self.thread_tokens[thread_id] = self.thread_tokens.get(thread_id, 0) + answer_tokens

        return {
            "answer": answer,
            "agent_tokens": answer_tokens,
            "prompt_tokens": prompt_tokens,
            "memory_path": str(self.profile_store.path_for(user_id)),
        }

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        """Student TODO: estimate the context carried into one turn.

        Hint:
        - Include `User.md`
        - Include compact summary text
        - Include recent kept messages
        """

        profile = self.profile_store.read_text(user_id)
        context = self.compact_memory.context(thread_id)
        messages = context.get("messages", [])
        recent_text = "\n".join(
            f"{item.get('role')}: {item.get('content')}" for item in messages  # type: ignore[union-attr]
        )
        summary = str(context.get("summary", ""))
        return estimate_tokens(profile) + estimate_tokens(summary) + estimate_tokens(recent_text)

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        """Student TODO: return a deterministic answer using persisted memory.

        Make sure the advanced agent can answer questions like:
        - "Mình tên gì?"
        - "Hiện tại mình làm nghề gì?"
        - "Nhắc lại style trả lời mình thích"
        - questions in the long stress dataset
        """

        facts = self.profile_store.facts(user_id)
        lower = message.lower()

        if not facts:
            return "Mình đã ghi nhận. Hiện chưa có fact dài hạn nào đủ chắc để nhắc lại."

        requested: list[str] = []
        if "tên" in lower or "biết" in lower:
            requested.append("Name")
        if "nghề" in lower or "làm gì" in lower or "là ai" in lower:
            requested.append("Profession")
        if "ở đâu" in lower or "nơi ở" in lower or "hiện tại" in lower:
            requested.append("Location")
        if "style" in lower or "kiểu trả lời" in lower or "trả lời" in lower or "3 bullet" in lower:
            requested.append("Response style")
        if "đồ uống" in lower or "uống" in lower:
            requested.append("Favorite drink")
        if "món ăn" in lower or "ăn" in lower:
            requested.append("Favorite food")
        if "nuôi" in lower or "con gì" in lower:
            requested.append("Pet")
        if "quan tâm" in lower or "thích" in lower or "mối quan tâm" in lower:
            requested.append("Interests")

        if not requested:
            requested = ["Name", "Profession", "Location", "Response style", "Interests"]

        parts = [f"{label}: {facts[label]}" for label in requested if label in facts]
        if not parts:
            parts = [f"{key}: {value}" for key, value in list(facts.items())[:4]]
        return "Mình nhớ các điểm chính: " + "; ".join(parts) + "."

    def _maybe_build_langchain_agent(self):
        """Student TODO: wire a live agent with tools and compact middleware.

        High-level design:
        - `build_chat_model(self.config.model)` for the selected provider
        - `InMemorySaver` for short-term thread state
        - tool to read `User.md`
        - tool to write/edit `User.md`
        - dynamic prompt that injects profile memory
        - summarization middleware for long threads
        """

        try:
            return build_chat_model(self.config.model)
        except Exception:
            return None


def _fact_label(key: str) -> str:
    labels = {
        "name": "Name",
        "location": "Location",
        "profession": "Profession",
        "response_style": "Response style",
        "favorite_drink": "Favorite drink",
        "favorite_food": "Favorite food",
        "pet": "Pet",
        "interests": "Interests",
    }
    return labels.get(key, key.replace("_", " ").title())
