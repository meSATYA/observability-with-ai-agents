"""Load a compact, project-local skill without copying the whole file into prompts."""

from pathlib import Path
import os


def load_context(question: str = "", max_chars: int = 900) -> str:
    configured = Path(os.getenv("SKILLS_DIR", "/workspace/skills"))
    candidates = [configured / "incident-investigation" / "SKILL.md",
                  Path(__file__).parents[1] / "skills" / "incident-investigation" / "SKILL.md"]
    text = None
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
            break
        except OSError:
            continue
    if text is None:
        return "Use supplied evidence only. Keep application root cause separate from model/infrastructure failures."
    body = text.split("---", 2)[-1]
    body = " ".join(line.strip() for line in body.splitlines() if line.strip() and not line.lstrip().startswith("#"))
    return body[:max_chars]
