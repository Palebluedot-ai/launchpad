#!/usr/bin/env python3
"""Create a project-local structured snapshot markdown in docs/snapshots/.

Designed for Hermes manual trigger phrase: `snapshot`.

Examples:
  python3 templates/save-snapshot.py --topic "hermes snapshot workflow" \
    --context "Confirmed root and path" --decisions "Use docs/snapshots" \
    --next-actions "Implement skill"

  # JSON payload mode (recommended for automation):
  cat payload.json | python3 templates/save-snapshot.py --stdin-json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

REDACTION_TOKEN = "[REDACTED]"

SECRET_PATTERNS: list[tuple[re.Pattern[str], str | Any]] = [
    (re.compile(r"(?i)\b(sk-[a-z0-9_-]{16,}|xox[baprs]-[a-z0-9-]{10,}|ghp_[A-Za-z0-9]{20,}|glpat-[A-Za-z0-9_-]{20,})\b"), REDACTION_TOKEN),
    (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"), r"\1" + REDACTION_TOKEN),
    (re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd|cookie|session)\b\s*[:=]\s*[^\s,;]+"), lambda m: re.sub(r"([:=]).*", r"\1 " + REDACTION_TOKEN, m.group(0))),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), REDACTION_TOKEN),
    (re.compile(r"(?m)^([A-Z0-9_]{2,})=(.+)$"), lambda m: f"{m.group(1)}={REDACTION_TOKEN}" if any(k in m.group(1).lower() for k in ["key", "token", "secret", "password", "passwd", "cookie"]) else m.group(0)),
]


def redact(text: str) -> tuple[str, int]:
    total = 0
    out = text
    for pattern, repl in SECRET_PATTERNS:
        out, n = pattern.subn(repl, out)
        total += n
    return out, total


def slugify(topic: str) -> str:
    topic = topic.strip().lower()
    topic = re.sub(r"[^a-z0-9\u4e00-\u9fff\s-]", "", topic)
    topic = re.sub(r"\s+", "-", topic)
    topic = re.sub(r"-+", "-", topic).strip("-")
    return topic[:64] or "snapshot"


def run_git(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return ""


def detect_project_root(start: Path) -> Path:
    root = run_git(["rev-parse", "--show-toplevel"], start)
    return Path(root) if root else start.resolve()


@dataclass
class SnapshotData:
    topic: str
    summary: str
    context: str
    decisions: str
    progress: str
    open_questions: str
    next_actions: str
    references: str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", default="")
    p.add_argument("--topic", default="")
    p.add_argument("--summary", default="")
    p.add_argument("--context", default="")
    p.add_argument("--decisions", default="")
    p.add_argument("--progress", default="")
    p.add_argument("--open-questions", default="")
    p.add_argument("--next-actions", default="")
    p.add_argument("--references", default="")
    p.add_argument("--stdin-json", action="store_true")
    return p.parse_args()


def build_data(args: argparse.Namespace) -> SnapshotData:
    payload: dict[str, Any] = {}
    if args.stdin_json:
        raw = os.sys.stdin.read().strip()
        if raw:
            payload = json.loads(raw)

    def g(key: str, fallback: str = "") -> str:
        val = payload.get(key, getattr(args, key.replace('-', '_'), fallback))
        if val is None:
            return ""
        if isinstance(val, list):
            return "\n".join(f"- {x}" for x in val)
        return str(val).strip()

    topic = g("topic") or "session snapshot"
    return SnapshotData(
        topic=topic,
        summary=g("summary") or "Snapshot captured for current Hermes session.",
        context=g("context") or "(pending)",
        decisions=g("decisions") or "(pending)",
        progress=g("progress") or "(pending)",
        open_questions=g("open_questions") or "(none)",
        next_actions=g("next_actions") or "(pending)",
        references=g("references") or "(none)",
    )


def render_markdown(data: SnapshotData, project_root: Path) -> tuple[str, int, str]:
    now = datetime.now()
    topic_slug = slugify(data.topic)
    ts = now.strftime("%Y%m%d-%H%M%S")
    file_name = f"{ts}-{topic_slug}.md"

    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], project_root) or "unknown"
    repo_name = project_root.name

    md = f"""---
type: hermes-snapshot
topic: {data.topic}
created_at: {now.isoformat(timespec='seconds')}
project_root: {project_root}
project: {repo_name}
branch: {branch}
source: hermes
status: active
---

# Snapshot: {data.topic}

## Summary
{data.summary}

## Context
{data.context}

## Key Decisions
{data.decisions}

## Progress
{data.progress}

## Open Questions / Risks
{data.open_questions}

## Next Actions
{data.next_actions}

## References
{data.references}
"""

    redacted, hits = redact(md)
    return redacted, hits, file_name


def main() -> int:
    args = parse_args()
    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else detect_project_root(Path.cwd())

    data = build_data(args)
    markdown, redaction_hits, file_name = render_markdown(data, project_root)

    out_dir = project_root / "docs" / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / file_name

    if out_file.exists():
        suffix = datetime.now().strftime("%f")
        out_file = out_dir / f"{out_file.stem}-{suffix}{out_file.suffix}"

    out_file.write_text(markdown, encoding="utf-8")

    result = {
        "ok": True,
        "path": str(out_file),
        "topic": data.topic,
        "redaction_hits": redaction_hits,
        "project_root": str(project_root),
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
