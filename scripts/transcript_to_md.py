#!/usr/bin/env python3
"""Convert a Claude Code session transcript (.jsonl) into a readable markdown AI log.

Keeps: user messages, Claude's text replies, one-line summaries of tool calls (✗ on errors),
and the end-of-turn recaps. Drops: internal reasoning, raw tool output, system/harness records.

Usage (from the repo root; stdlib only):

    python3 scripts/transcript_to_md.py --out docs/ai-logs/phase-1-brief.md \\
        --title "Phase 1 — Brief" --summary "What the phase delivered…"

By default the newest transcript for this repo in ~/.claude/projects/ is used; pass --transcript
to pick another. --until-turn N stops after the Nth user message. After writing, the output is
scanned for emails, local paths and secret-like strings; the script exits 2 if any are found, so
review before committing (the repo is public).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()

PRIVACY_PATTERNS = {
    "email address": r"[\w.+-]+@[\w-]+\.(?:com|in|org|net|io|co)\b",
    "local path": r"/(?:Users|home)/[^/\s]+/",
    "temp path": r"/(?:private/)?tmp/claude-",
    "DB URL with password": r"postgres(?:ql)?://[^\s:@]+:[^\s@]+@",
    "GitHub token": r"\b(?:ghp|gho|ghs|github_pat)_[A-Za-z0-9_]{10,}",
    "API key": r"\bsk-[A-Za-z0-9-]{16,}",
    "system reminder": r"<system-reminder>",
}


def default_transcript() -> Path:
    slug = str(REPO).replace("/", "-")
    folder = HOME / ".claude" / "projects" / slug
    files = sorted(folder.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        sys.exit(f"No transcripts found in {folder}")
    return files[-1]


def rel(text: str) -> str:
    text = text.replace(str(REPO) + "/", "").replace(str(HOME) + "/", "~/")
    text = re.sub(r"/(?:private/)?tmp/claude-[^\s'\"]*/scratchpad/", "<scratchpad>/", text)
    text = re.sub(r"/(?:private/)?tmp/claude-[^\s'\"]*/tasks/", "<tasks>/", text)
    return text


def clean_user(s: str) -> str:
    s = re.sub(r"<system-reminder>.*?</system-reminder>", "", s, flags=re.DOTALL)
    s = re.sub(r"</?pasted_content[^>]*>", "", s)
    if s.lstrip().startswith(("<local-command", "<command-name>")):
        return ""  # slash commands like /export, run outside the conversation
    return s.strip()


def summarize(name: str, inp: dict) -> str | None:
    short = name.split("__")[-1]
    if name == "Bash":
        bg = " (background)" if inp.get("run_in_background") else ""
        return f"**Bash** — {inp.get('description') or rel(inp.get('command', ''))[:80]}{bg}"
    if name in ("Read", "Write", "Edit"):
        return f"**{name}** `{rel(inp.get('file_path', ''))}`"
    if short == "update_plan":
        if "items" in inp:
            return "**Task list** — " + "; ".join(i["content"] for i in inp["items"])
        return None  # progress ticks are noise
    if short == "wrap_up":
        return None  # rendered separately as the recap
    if name == "ToolSearch":
        return f"**ToolSearch** — load `{inp.get('query', '').replace('select:', '')}`"
    if name == "TaskStop":
        return "**TaskStop** — stop a background task"
    if name == "Agent":
        return f"**Agent** — {inp.get('description', '')}"
    if short == "browser_batch":
        acts = [
            a["name"] + (f" {a['input'].get('url')}" if a["name"] == "navigate" else "") for a in inp.get("actions", [])
        ]
        return "**Browser** — " + ", ".join(acts)
    if short.startswith(("navigate", "resize_window", "computer", "get_page_text", "read_page", "find")):
        detail = inp.get("url") or inp.get("preset") or inp.get("action") or inp.get("query") or ""
        return f"**Browser** — {short} {detail}".rstrip()
    return f"**{short}**"


def convert(src: Path, out_path: Path, until_turn: int | None, from_turn: int | None = None) -> tuple[str, int, str]:
    records = [json.loads(line) for line in src.open()]
    errors = {
        b["tool_use_id"]
        for d in records
        if d.get("type") == "user" and isinstance(d["message"]["content"], list)
        for b in d["message"]["content"]
        if b.get("type") == "tool_result" and b.get("is_error")
    }
    link_prefix = os.path.relpath(REPO, out_path.resolve().parent).replace(os.sep, "/") + "/"

    out: list[str] = []
    seen: set[str] = set()
    tools: list[str] = []
    recap: list[str] = []
    turn = 0
    first_ts = ""
    start = 0  # index in `out` where the log begins (--from-turn)

    def flush_tools() -> None:
        if tools:
            out.extend(["", *(f"- {t}" for t in tools), ""])
            tools.clear()

    def flush_recap() -> None:
        flush_tools()
        if recap:
            out.extend(["", *recap, ""])
            recap.clear()

    for d in records:
        kind = d.get("type")
        msg = d.get("message") or {}
        content = msg.get("content")
        if kind == "user" and d.get("isCompactSummary"):
            flush_recap()
            out += ["", "*(The session's context was compacted here; the conversation continues.)*", ""]
            continue
        user_text = None
        if kind == "user" and isinstance(content, str):
            user_text = clean_user(content)
        elif kind == "user" and isinstance(content, list) and not any(b.get("type") == "tool_result" for b in content):
            # A message sent with an image: its text blocks plus a marker (the image itself isn't kept).
            texts = [b.get("text", "") for b in content if b.get("type") == "text" and not b.get("text", "").startswith("[Image")]
            images = sum(1 for b in content if b.get("type") == "image")
            user_text = clean_user("\n".join(texts))
            if images:
                user_text = (user_text + "\n\n" if user_text else "") + f"*[{images} image{'s' if images > 1 else ''} attached]*"
        if user_text is not None:
            text = user_text
            if not text:
                continue
            flush_recap()
            if until_turn is not None and turn >= until_turn:
                break
            turn += 1
            ts = d.get("timestamp", "")[:16].replace("T", " ")
            if from_turn and turn == from_turn:
                start, first_ts = len(out), ts
            first_ts = first_ts or ts
            quoted = [("> " + ln) if ln else ">" for ln in text.splitlines()]
            out += ["", "---", "", f"## {turn}. You  <sub>{ts} UTC</sub>", "", *quoted, "", "### Claude", ""]
            continue
        # Some assistant messages exist only inside api-request-blob records (the whole message,
        # text + tool calls), so read both and de-duplicate by tool-call id / full text.
        is_assistant = kind == "assistant" or (kind == "api-request-blob" and msg.get("role") == "assistant")
        if not is_assistant or not isinstance(content, list) or turn == 0:
            continue
        for b in content:
            if b.get("type") not in ("text", "tool_use"):
                continue
            key = b.get("id") or "text:" + b.get("text", "")
            if key in seen:
                continue
            seen.add(key)
            if b["type"] == "text" and b["text"].strip():
                flush_tools()
                txt = rel(b["text"].strip())
                # Demote headings below the log's own "## n. You" / "### Claude" levels.
                txt = re.sub(r"^(#{1,4}) ", lambda m: "#" * min(len(m.group(1)) + 2, 6) + " ", txt, flags=re.MULTILINE)
                # Repo-relative links → relative to the output file.
                txt = re.sub(r"\]\((?!https?://|#|\.\./|mailto:)([^)\s]+)\)", rf"]({link_prefix}\1)", txt)
                out += [txt, ""]
            elif b["type"] == "tool_use":
                if b["name"].split("__")[-1] == "wrap_up":
                    flush_tools()
                    box = f"> **Recap:** {b['input'].get('recap', '')}"
                    if b["input"].get("ask"):
                        box += f"  \n> **Question:** {b['input']['ask']}"
                    recap.append(box)
                    continue
                s = summarize(b["name"], b["input"])
                if s:
                    tools.append(s + (" ✗" if b["id"] in errors else ""))
    flush_recap()
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(out[start:])).rstrip()
    return body, turn, first_ts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path, help="output markdown path, e.g. docs/ai-logs/phase-1.md")
    ap.add_argument("--title", required=True, help='e.g. "Phase 1 — Brief"')
    ap.add_argument("--summary", default="", help="one-paragraph outcome shown under the header")
    ap.add_argument("--transcript", type=Path, help="session .jsonl (default: newest for this repo)")
    ap.add_argument("--until-turn", type=int, help="stop after the Nth user message")
    ap.add_argument("--from-turn", type=int, help="start at the Nth user message (a forked session's own part)")
    ap.add_argument("--note", default="", help="extra line under the header, e.g. where a forked session's history is")
    args = ap.parse_args()

    src = args.transcript or default_transcript()
    body, turns, first_ts = convert(src, args.out, args.until_turn, args.from_turn)
    date = datetime.strptime(first_ts, "%Y-%m-%d %H:%M").strftime("%-d %b %Y") if first_ts else "?"
    header = f"""# {args.title}

AI log of a Claude Code session on FINN (started {date} UTC). Converted from the session transcript \
(`{src.name}`) by `scripts/transcript_to_md.py`.

- **You** = the developer's messages (pasted prompts shown as quotes). **Claude** = replies, in order.
- Tool calls are summarised one per line (the command's own description, or the file touched); ✗ marks a call \
that returned an error. Raw tool output and internal reasoning are omitted.
- "Recap" lines are the end-of-turn summary shown in the app.
- The transcript does not always store short mid-turn progress notes; each turn's main reply is present.
"""
    if args.note:
        header += f"\n{args.note}\n"
    if args.summary:
        header += f"\n**Outcome:** {args.summary}\n"
    text = header + body + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    print(f"{turns} user turns → {args.out} ({len(text.splitlines())} lines)")

    hits = [(label, m.group(0)) for label, pat in PRIVACY_PATTERNS.items() for m in re.finditer(pat, text)]
    if hits:
        print("\nPRIVACY CHECK — review before committing (the repo is public):", file=sys.stderr)
        for label, match in hits[:20]:
            print(f"  {label}: {match[:60]}", file=sys.stderr)
        sys.exit(2)
    print("Privacy check: clean.")


if __name__ == "__main__":
    main()
