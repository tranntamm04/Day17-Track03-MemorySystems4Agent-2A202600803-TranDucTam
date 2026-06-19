from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from agent_advanced import AdvancedAgent
from config import load_config


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    with TemporaryDirectory() as tmp:
        config = load_config(Path(__file__).resolve().parent.parent)
        config.state_dir = Path(tmp) / "state"
        config.state_dir.mkdir(parents=True, exist_ok=True)

        agent = AdvancedAgent(config, force_offline=True)
        user_id = "demo-user"
        turns = [
            "Mình tên là DũngCT Demo.",
            "Mình đang làm MLOps engineer.",
            "Mình đang ở Huế.",
            "Mình muốn bạn trả lời 3 bullet ngắn, có ví dụ thực chiến.",
            "Mình đùa là hay chuyển sang product manager cho vui thôi.",
            "Mình đính chính: hiện tại mình đang ở Đà Nẵng.",
            "Mình vẫn thích Python, AI agent và benchmark memory.",
        ]

        for turn in turns:
            agent.reply(user_id, "demo-thread", turn)

        print("## User.md")
        print(agent.profile_store.read_text(user_id).strip())
        print()
        print("## Decay report")
        for key, score in agent.profile_store.decay_report(user_id).items():
            print(f"- {key}: {score:.3f}")
        print()
        print("## Cross-session recall")
        answer = agent.reply(user_id, "new-thread", "Nhắc lại tên, nghề, nơi ở và style trả lời mình thích.")[
            "answer"
        ]
        print(answer)


if __name__ == "__main__":
    main()
