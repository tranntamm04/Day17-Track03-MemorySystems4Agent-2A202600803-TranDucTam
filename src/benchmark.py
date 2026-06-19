from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    """Student TODO: read JSON conversations from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def recall_points(answer: str, expected: list[str]) -> float:
    """Student TODO: return 0 / 0.5 / 1 depending on how many expected facts appear."""

    if not expected:
        return 1.0
    answer_lower = answer.lower()
    hits = sum(1 for item in expected if item.lower() in answer_lower)
    if hits == len(expected):
        return 1.0
    if hits > 0:
        return 0.5
    return 0.0


def heuristic_quality(answer: str, expected: list[str]) -> float:
    """Student TODO: add a lightweight quality score for offline mode."""

    if not answer.strip():
        return 0.0
    score = 0.4
    score += 0.4 * recall_points(answer, expected)
    if len(answer.split()) >= 6:
        score += 0.1
    if len(answer) < 700:
        score += 0.1
    return round(min(score, 1.0), 3)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    """Student TODO: evaluate one agent over many conversations.

    Pseudocode:
    1. Feed all turns to the agent.
    2. Track `agent tokens only`.
    3. Track `prompt tokens processed`.
    4. Ask recall questions in a fresh thread.
    5. Compute average recall and quality.
    6. Record memory file growth and compaction count.
    """

    user_ids = sorted({conversation["user_id"] for conversation in conversations})
    before_sizes = {
        user_id: agent.memory_file_size(user_id) if hasattr(agent, "memory_file_size") else 0
        for user_id in user_ids
    }

    recall_scores: list[float] = []
    quality_scores: list[float] = []
    compactions = 0
    thread_ids: list[str] = []

    for conversation in conversations:
        thread_id = f"{agent_name}-{conversation['id']}"
        thread_ids.append(thread_id)
        user_id = conversation["user_id"]
        for turn in conversation.get("turns", []):
            agent.reply(user_id, thread_id, turn)

        for index, question in enumerate(conversation.get("recall_questions", [])):
            recall_thread_id = f"{thread_id}-recall-{index}"
            thread_ids.append(recall_thread_id)
            result = agent.reply(user_id, recall_thread_id, question["question"])
            answer = result["answer"]
            expected = question.get("expected_contains", [])
            recall_scores.append(recall_points(answer, expected))
            quality_scores.append(heuristic_quality(answer, expected))

    after_sizes = {
        user_id: agent.memory_file_size(user_id) if hasattr(agent, "memory_file_size") else 0
        for user_id in user_ids
    }

    for thread_id in thread_ids:
        compactions += agent.compaction_count(thread_id)

    agent_tokens = sum(agent.token_usage(thread_id) for thread_id in thread_ids)
    prompt_tokens = sum(agent.prompt_token_usage(thread_id) for thread_id in thread_ids)
    memory_growth = sum(after_sizes[user_id] - before_sizes[user_id] for user_id in user_ids)

    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=agent_tokens,
        prompt_tokens_processed=prompt_tokens,
        recall_score=round(sum(recall_scores) / max(1, len(recall_scores)), 3),
        response_quality=round(sum(quality_scores) / max(1, len(quality_scores)), 3),
        memory_growth_bytes=memory_growth,
        compactions=compactions,
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    """Student TODO: print a markdown table or tabulated output."""

    headers = [
        "Agent",
        "Agent tokens only",
        "Prompt tokens processed",
        "Cross-session recall",
        "Response quality",
        "Memory growth (bytes)",
        "Compactions",
    ]
    values = [
        [
            row.agent_name,
            row.agent_tokens_only,
            row.prompt_tokens_processed,
            f"{row.recall_score:.3f}",
            f"{row.response_quality:.3f}",
            row.memory_growth_bytes,
            row.compactions,
        ]
        for row in rows
    ]
    try:
        from tabulate import tabulate

        return tabulate(values, headers=headers, tablefmt="github")
    except ImportError:
        lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        lines.extend("| " + " | ".join(str(item) for item in row) + " |" for row in values)
        return "\n".join(lines)


def main() -> None:
    """Student TODO: run both benchmark suites.

    Required benchmark sections:
    - Standard benchmark from `data/conversations.json`
    - Long-context stress benchmark from `data/advanced_long_context.json`

    Compare:
    - Baseline
    - Advanced

    Keep the same output columns as the solved lab:
    - Agent tokens only
    - Prompt tokens processed
    - Cross-session recall
    - Response quality
    - Memory growth (bytes)
    - Compactions
    """

    config = load_config(Path(__file__).resolve().parent.parent)
    config.state_dir = config.base_dir / ".tmp" / f"benchmark-{uuid4().hex}"
    config.state_dir.mkdir(parents=True, exist_ok=True)

    standard = load_conversations(config.data_dir / "conversations.json")
    stress = load_conversations(config.data_dir / "advanced_long_context.json")

    print("## Standard Benchmark")
    print(
        format_rows(
            [
                run_agent_benchmark("Baseline", BaselineAgent(config, force_offline=True), standard, config),
                run_agent_benchmark("Advanced", AdvancedAgent(config, force_offline=True), standard, config),
            ]
        )
    )
    print()
    print("## Long-Context Stress Benchmark")
    print(
        format_rows(
            [
                run_agent_benchmark("Baseline", BaselineAgent(config, force_offline=True), stress, config),
                run_agent_benchmark("Advanced", AdvancedAgent(config, force_offline=True), stress, config),
            ]
        )
    )


if __name__ == "__main__":
    main()
