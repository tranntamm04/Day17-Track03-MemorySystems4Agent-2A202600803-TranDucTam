from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import unicodedata


MIN_FACT_CONFIDENCE = 0.70
DECAY_PER_MISSED_TURN = 0.03


@dataclass(frozen=True)
class ProfileUpdate:
    key: str
    value: str
    confidence: float
    source: str
    is_correction: bool = False


@dataclass(frozen=True)
class StoredFact:
    key: str
    value: str
    confidence: float
    updated_at: int
    last_seen: int
    mentions: int
    source: str = "heuristic"

    def decayed_confidence(self, current_turn: int) -> float:
        missed_turns = max(0, current_turn - self.last_seen)
        mention_boost = min(0.12, max(0, self.mentions - 1) * 0.03)
        return max(0.0, min(1.0, self.confidence + mention_boost - missed_turns * DECAY_PER_MISSED_TURN))


def estimate_tokens(text: str) -> int:
    """Student TODO: implement a simple token estimator.

    Example idea:
    - Strip whitespace
    - Return 0 for empty text
    - Approximate tokens from character count, e.g. len(text) / 4
    """

    stripped = (text or "").strip()
    if not stripped:
        return 0
    word_count = len(re.findall(r"\w+", stripped, flags=re.UNICODE))
    char_estimate = max(1, len(stripped) // 4)
    return max(word_count, char_estimate)


@dataclass
class UserProfileStore:
    """Persistent storage for `User.md`.

    Student TODO:
    - Map each user id to one markdown file
    - Support read / write / edit operations
    - Optionally expose helpers like `facts()` or `upsert_fact()`
    """

    root_dir: Path
    min_confidence: float = MIN_FACT_CONFIDENCE

    def path_for(self, user_id: str) -> Path:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        normalized = unicodedata.normalize("NFKD", user_id or "default")
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", ascii_text).strip("-._").lower()
        return self.root_dir / (slug or "default") / "User.md"

    def read_text(self, user_id: str) -> str:
        path = self.path_for(user_id)
        if not path.exists():
            return _default_profile(user_id)
        return path.read_text(encoding="utf-8")

    def write_text(self, user_id: str, content: str) -> Path:
        path = self.path_for(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        content = self.read_text(user_id)
        if search_text not in content:
            return False
        self.write_text(user_id, content.replace(search_text, replacement, 1))
        return True

    def file_size(self, user_id: str) -> int:
        path = self.path_for(user_id)
        return path.stat().st_size if path.exists() else 0

    def facts(self, user_id: str) -> dict[str, str]:
        return {
            fact.key: fact.value
            for fact in self.fact_records(user_id).values()
            if fact.confidence >= self.min_confidence
        }

    def fact_records(self, user_id: str) -> dict[str, StoredFact]:
        records: dict[str, StoredFact] = {}
        for line in self.read_text(user_id).splitlines():
            fact = _parse_fact_line(line)
            if fact:
                records[fact.key] = fact
        return records

    def fact_confidence(self, user_id: str, key: str) -> float:
        fact = self.fact_records(user_id).get(key)
        if not fact:
            return 0.0
        return fact.decayed_confidence(self._current_turn(user_id))

    def upsert_fact(
        self,
        user_id: str,
        key: str,
        value: str,
        confidence: float = 1.0,
        source: str = "manual",
        is_correction: bool = False,
    ) -> Path:
        if confidence < self.min_confidence:
            return self.path_for(user_id)

        content = self.read_text(user_id)
        label = key.strip()
        turn = self._next_turn(user_id)
        existing = self.fact_records(user_id).get(label)
        mentions = 1
        updated_at = turn
        last_seen = turn

        if existing and existing.value == value.strip():
            mentions = existing.mentions + 1
            updated_at = existing.updated_at
            confidence = max(confidence, existing.confidence)
        elif existing and existing.value != value.strip():
            content = self._append_conflict(content, label, existing.value, value.strip(), turn)

        metadata = (
            f"confidence={confidence:.2f}; updated_at={updated_at}; "
            f"last_seen={last_seen}; mentions={mentions}; source={source}"
        )
        if is_correction:
            metadata += "; correction=true"
        replacement = f"- **{label}**: {value.strip()} <!-- {metadata} -->"
        pattern = re.compile(rf"^- \*\*{re.escape(label)}\*\*: .*$", flags=re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(replacement, content)
        else:
            if "## Stable facts" not in content:
                content = content.rstrip() + "\n\n## Stable facts\n"
            content = content.rstrip() + f"\n{replacement}\n"
        return self.write_text(user_id, content)

    def decay_report(self, user_id: str) -> dict[str, float]:
        current_turn = self._current_turn(user_id)
        return {
            key: round(fact.decayed_confidence(current_turn), 3)
            for key, fact in self.fact_records(user_id).items()
        }

    def _current_turn(self, user_id: str) -> int:
        records = self.fact_records(user_id)
        if not records:
            return 0
        return max(fact.last_seen for fact in records.values())

    def _next_turn(self, user_id: str) -> int:
        return self._current_turn(user_id) + 1

    def _append_conflict(self, content: str, key: str, old_value: str, new_value: str, turn: int) -> str:
        if "## Conflict history" not in content:
            content = content.rstrip() + "\n\n## Conflict history\n"
        note = f"- {key}: replaced `{old_value}` with `{new_value}` at turn {turn}"
        return content.rstrip() + f"\n{note}\n"


def extract_profile_updates(message: str) -> dict[str, ProfileUpdate]:
    """Student TODO: convert raw user text into stable profile facts.

    Example facts you may want to extract:
    - name
    - location
    - profession
    - preferences / response style
    - favorite food / drink

    Pseudocode:
    1. Build a few regex patterns.
    2. Skip obvious question-only turns.
    3. Return only the facts that are confidently present in the message.
    """

    text = " ".join((message or "").split())
    lower = text.lower()
    if not text or lower.endswith("?"):
        return {}
    if any(marker in lower for marker in ["có biết", "là gì", "ở đâu", "tên gì", "nhắc lại"]):
        return {}

    facts: dict[str, ProfileUpdate] = {}
    is_correction = any(marker in lower for marker in ["đính chính", "thực ra", "cập nhật", "không còn", "sang"])
    uncertainty_penalty = 0.35 if any(marker in lower for marker in ["có thể", "hình như", "chắc là", "đùa", "hay là"]) else 0.0

    patterns = [
        ("name", r"(?:mình|tôi|em)\s+tên\s+(?:là\s+)?([^.,;!?]+)"),
        ("location", r"(?:hiện\s+(?:tại\s+)?)?(?:mình|tôi|em)\s+(?:đang\s+)?(?:ở|sống ở)\s+([^.,;!?]+)"),
        ("profession", r"(?:mình|tôi|em)\s+(?:đang\s+)?(?:làm|là)\s+([^.,;!?]+(?:engineer|developer|manager|researcher|sinh viên|giảng viên|dev|qa|tester)[^.,;!?]*)"),
        ("favorite_drink", r"(?:đồ uống yêu thích|thức uống yêu thích)\s+(?:là\s+)?([^.,;!?]+)"),
        ("favorite_food", r"(?:món ăn yêu thích)\s+(?:là\s+)?([^.,;!?]+)"),
        ("pet", r"(?:nuôi|có)\s+(?:một\s+)?(?:bé\s+)?([^.,;!?]*(?:corgi|chó|mèo)[^.,;!?]*)"),
        ("interests", r"(?:mình|tôi|em)\s+(?:thích|quan tâm(?: nhiều)? đến)\s+([^.!?]+)"),
        ("response_style", r"(?:muốn|thích|hãy)\s+(?:bạn\s+)?(?:trả lời|giải thích)[^.!?]*"),
    ]

    for key, pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.UNICODE)
        if match:
            value = _clean_fact(match.group(1) if match.lastindex else match.group(0))
            confidence = _confidence_for(key, text, is_correction) - uncertainty_penalty
            _maybe_add_update(facts, key, value, confidence, "regex", is_correction)

    if "đính chính" in lower or "thực ra" in lower or "cập nhật" in lower:
        location_match = re.search(r"(?:đang\s+)?(?:làm việc\s+)?ở\s+([^.,;!?]+)", text, flags=re.IGNORECASE)
        if location_match and "không phải" not in location_match.group(0).lower():
            _maybe_add_update(
                facts,
                "location",
                _clean_fact(location_match.group(1)),
                0.96,
                "correction",
                True,
            )
        profession_match = re.search(r"(?:nghề nghiệp|nghề)\s+(?:hiện tại\s+)?(?:vẫn\s+)?(?:là\s+)?([^.,;!?]+)", text, flags=re.IGNORECASE)
        if profession_match:
            _maybe_add_update(
                facts,
                "profession",
                _clean_fact(profession_match.group(1)),
                0.96,
                "correction",
                True,
            )

    if "3 bullet" in lower:
        _maybe_add_update(
            facts,
            "response_style",
            "3 bullet ngắn, có ví dụ thực chiến, nhấn trade-off",
            0.95,
            "explicit_style",
            is_correction,
        )
    elif "ngắn gọn" in lower and ("trả lời" in lower or "style" in lower):
        _maybe_add_update(
            facts,
            "response_style",
            "ngắn gọn, rõ ý, có ví dụ thực tế",
            0.90,
            "explicit_style",
            is_correction,
        )

    return facts


def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    """Student TODO: create a compact summary of older messages.

    This can be heuristic text concatenation first.
    Later, you can replace it with an LLM-based summary if desired.
    """

    if not messages:
        return ""
    snippets = []
    for item in messages[-max_items:]:
        role = item.get("role", "unknown")
        content = " ".join(item.get("content", "").split())
        if len(content) > 180:
            content = content[:177].rstrip() + "..."
        snippets.append(f"{role}: {content}")
    return "Compact summary of earlier turns:\n" + "\n".join(f"- {snippet}" for snippet in snippets)


@dataclass
class CompactMemoryManager:
    """Student TODO: implement compact memory for long threads.

    Goal:
    - Keep recent messages in full
    - When the thread grows too large, move older content into a summary
    - Track how many compactions happened for benchmarking
    """

    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        # TODO:
        # 1. create thread state if missing
        # 2. append the new message
        # 3. trigger compaction if needed
        thread = self.context(thread_id)
        messages = thread["messages"]
        assert isinstance(messages, list)
        messages.append({"role": role, "content": content})

        summary = str(thread.get("summary", ""))
        total_tokens = estimate_tokens(summary) + sum(
            estimate_tokens(str(item.get("content", ""))) for item in messages
        )
        if total_tokens > self.threshold_tokens and len(messages) > self.keep_messages:
            older = messages[:-self.keep_messages]
            recent = messages[-self.keep_messages:]
            summary_items = ([{"role": "summary", "content": summary}] if summary else []) + older
            thread["summary"] = summarize_messages(summary_items, max_items=max(4, self.keep_messages))
            thread["messages"] = recent
            thread["compactions"] = int(thread.get("compactions", 0)) + 1

    def context(self, thread_id: str) -> dict[str, object]:
        if thread_id not in self.state:
            self.state[thread_id] = {"messages": [], "summary": "", "compactions": 0}
        return self.state[thread_id]

    def compaction_count(self, thread_id: str) -> int:
        return int(self.context(thread_id).get("compactions", 0))


def _default_profile(user_id: str) -> str:
    return f"# User profile: {user_id}\n\n## Stable facts\n"


def _clean_fact(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" .,-;:!?")
    value = re.sub(r"\s+(nhé|nha|giúp mình)$", "", value, flags=re.IGNORECASE)
    return value.strip()


def _confidence_for(key: str, text: str, is_correction: bool) -> float:
    if is_correction:
        return 0.95
    if key in {"name", "favorite_drink", "favorite_food", "pet"}:
        return 0.92
    if key in {"location", "profession", "response_style"}:
        return 0.88
    if key == "interests":
        return 0.78 if len(text) < 180 else 0.72
    return 0.75


def _maybe_add_update(
    facts: dict[str, ProfileUpdate],
    key: str,
    value: str,
    confidence: float,
    source: str,
    is_correction: bool,
) -> None:
    if not value:
        return
    confidence = max(0.0, min(1.0, confidence))
    if confidence < MIN_FACT_CONFIDENCE:
        return
    current = facts.get(key)
    update = ProfileUpdate(
        key=key,
        value=value,
        confidence=confidence,
        source=source,
        is_correction=is_correction,
    )
    if current is None or update.confidence >= current.confidence:
        facts[key] = update


def _parse_fact_line(line: str) -> StoredFact | None:
    match = re.match(r"- \*\*(.+?)\*\*: (.*?)(?:\s+<!--\s*(.*?)\s*-->)?$", line)
    if not match:
        return None
    key = match.group(1).strip()
    value = match.group(2).strip()
    metadata = _parse_metadata(match.group(3) or "")
    confidence = float(metadata.get("confidence", "1.0"))
    updated_at = int(metadata.get("updated_at", "0"))
    last_seen = int(metadata.get("last_seen", str(updated_at)))
    mentions = int(metadata.get("mentions", "1"))
    source = metadata.get("source", "legacy")
    return StoredFact(
        key=key,
        value=value,
        confidence=confidence,
        updated_at=updated_at,
        last_seen=last_seen,
        mentions=mentions,
        source=source,
    )


def _parse_metadata(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in raw.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        result[key.strip()] = value.strip()
    return result
