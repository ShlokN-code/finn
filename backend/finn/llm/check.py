"""List the Gemini models this key can use and confirm the configured cheap/strong models exist.

python -m finn.llm.check
"""

from __future__ import annotations

from finn.db import load_dotenv
from finn.llm.gemini import Gemini


def main() -> None:
    load_dotenv()
    g = Gemini()
    if not g.available():
        raise SystemExit("GEMINI_API_KEY not set")
    names = g.list_models()
    for tier in ("cheap", "strong"):
        m = g.model_for(tier)
        print(f"{tier:6} {m:32} {'OK' if m in names else 'NOT AVAILABLE'}")
    print("\nflash models available:", ", ".join(sorted(n for n in names if "flash" in n)))


if __name__ == "__main__":
    main()
