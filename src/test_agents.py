from __future__ import annotations

from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config
from memory_store import UserProfileStore, extract_profile_updates


def make_config(tmp_path: Path):
    """Student TODO: build an isolated config for tests."""

    config = load_config(Path(__file__).resolve().parent.parent)
    config.state_dir = tmp_path / "state"
    config.state_dir.mkdir(parents=True, exist_ok=True)
    config.compact_threshold_tokens = 90
    config.compact_keep_messages = 4
    return config


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    """Student TODO: verify `User.md` can be created, updated, and edited."""

    store = UserProfileStore(tmp_path / "profiles")
    assert "Stable facts" in store.read_text("Dung CT")

    path = store.write_text("Dung CT", "# User profile\n\n## Stable facts\n- **Name**: Dung\n")
    assert path.exists()
    assert store.file_size("Dung CT") > 0

    changed = store.edit_text("Dung CT", "Dung", "DungCT")
    assert changed is True
    assert "DungCT" in store.read_text("Dung CT")


def test_compact_trigger(tmp_path: Path) -> None:
    """Student TODO: verify long threads trigger compaction."""

    agent = AdvancedAgent(make_config(tmp_path), force_offline=True)
    for index in range(12):
        agent.reply("u1", "thread-long", f"Đây là một lượt nói khá dài số {index} về memory compaction và token cost.")

    context = agent.compact_memory.context("thread-long")
    assert agent.compaction_count("thread-long") > 0
    assert context["summary"]
    assert len(context["messages"]) <= agent.config.compact_keep_messages


def test_cross_session_recall(tmp_path: Path) -> None:
    """Student TODO: verify advanced remembers across sessions and baseline does not."""

    config = make_config(tmp_path)
    advanced = AdvancedAgent(config, force_offline=True)
    baseline = BaselineAgent(config, force_offline=True)

    advanced.reply("u2", "session-a", "Mình tên là DũngCT.")
    advanced.reply("u2", "session-a", "Mình muốn bạn trả lời ngắn gọn, rõ ý và có ví dụ thực tế.")
    baseline.reply("u2", "session-a", "Mình tên là DũngCT.")

    advanced_answer = advanced.reply("u2", "session-b", "Mình tên gì và thích style trả lời nào?")["answer"]
    baseline_answer = baseline.reply("u2", "session-b", "Mình tên gì?")["answer"]

    assert "DũngCT" in advanced_answer
    assert "ngắn gọn" in advanced_answer
    assert "DũngCT" not in baseline_answer


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    """Student TODO: compare prompt load of baseline vs advanced on a long thread."""

    config = make_config(tmp_path)
    advanced = AdvancedAgent(config, force_offline=True)
    baseline = BaselineAgent(config, force_offline=True)
    long_turn = (
        "Mình đang stress test memory bằng một đoạn dài về Python, AI agent, "
        "benchmark token, recall dài hạn và compact summary để tránh prompt phình to."
    )

    for index in range(30):
        message = f"{long_turn} Lượt {index}."
        advanced.reply("u3", "long", message)
        baseline.reply("u3", "long", message)

    assert advanced.compaction_count("long") > 0
    assert advanced.prompt_token_usage("long") < baseline.prompt_token_usage("long")


def test_bonus_confidence_threshold_skips_uncertain_facts(tmp_path: Path) -> None:
    """Bonus: question-like or uncertain facts should not pollute User.md."""

    config = make_config(tmp_path)
    agent = AdvancedAgent(config, force_offline=True)

    agent.reply("u4", "s1", "Có thể mình tên là Nam, nhưng mình chưa chắc.")
    agent.reply("u4", "s1", "Bạn có biết mình tên gì không?")

    facts = agent.profile_store.facts("u4")
    assert "Name" not in facts
    assert extract_profile_updates("Bạn có biết mình tên gì không?") == {}


def test_bonus_conflict_handling_updates_corrected_fact(tmp_path: Path) -> None:
    """Bonus: a correction replaces stale facts and keeps conflict history."""

    config = make_config(tmp_path)
    agent = AdvancedAgent(config, force_offline=True)

    agent.reply("u5", "s1", "Mình đang ở Huế.")
    agent.reply("u5", "s1", "Mình đính chính: hiện tại mình đang ở Đà Nẵng.")

    facts = agent.profile_store.facts("u5")
    profile = agent.profile_store.read_text("u5")
    assert facts["Location"] == "Đà Nẵng"
    assert "Conflict history" in profile
    assert "Huế" in profile


def test_bonus_structured_metadata_and_decay_report(tmp_path: Path) -> None:
    """Bonus: stored facts expose confidence metadata and decay scores."""

    store = UserProfileStore(tmp_path / "profiles")
    store.upsert_fact("u6", "Name", "DungCT", confidence=0.91, source="test")
    store.upsert_fact("u6", "Interests", "Python và AI", confidence=0.76, source="test")

    records = store.fact_records("u6")
    report = store.decay_report("u6")

    assert records["Name"].confidence == 0.91
    assert records["Name"].source == "test"
    assert "Name" in report
    assert 0 < report["Interests"] <= 1


def test_bonus_noise_does_not_overwrite_stable_profession(tmp_path: Path) -> None:
    """Bonus: jokes or uncertain career changes should not overwrite stable facts."""

    config = make_config(tmp_path)
    agent = AdvancedAgent(config, force_offline=True)

    agent.reply("u7", "s1", "Mình đang làm MLOps engineer.")
    agent.reply("u7", "s1", "Mình đùa với đồng nghiệp là hay là chuyển sang product manager cho vui.")

    facts = agent.profile_store.facts("u7")
    assert facts["Profession"] == "MLOps engineer"
    assert "product manager" not in facts["Profession"]


def test_bonus_corrected_location_recall_uses_latest_fact(tmp_path: Path) -> None:
    """Bonus: recall should use the corrected fact, not the stale one."""

    config = make_config(tmp_path)
    agent = AdvancedAgent(config, force_offline=True)

    agent.reply("u8", "s1", "Mình đang ở Huế.")
    agent.reply("u8", "s1", "Mình đính chính: hiện tại mình đang ở Đà Nẵng.")
    answer = agent.reply("u8", "s2", "Hiện tại mình đang ở đâu?")["answer"]

    assert "Đà Nẵng" in answer
    assert "Huế" not in answer


def test_bonus_repeated_mentions_increase_fact_mentions(tmp_path: Path) -> None:
    """Bonus: repeated stable facts should increase mentions instead of duplicating rows."""

    store = UserProfileStore(tmp_path / "profiles")
    store.upsert_fact("u9", "Favorite drink", "cà phê sữa đá", confidence=0.9, source="test")
    store.upsert_fact("u9", "Favorite drink", "cà phê sữa đá", confidence=0.85, source="test")

    records = store.fact_records("u9")
    profile = store.read_text("u9")
    assert records["Favorite drink"].mentions == 2
    assert profile.count("Favorite drink") == 1
