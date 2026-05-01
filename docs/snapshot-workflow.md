# Hermes Snapshot Workflow (Project-local)

## Goal
When user inputs `snapshot` in Hermes workflow, create a structured markdown snapshot under current project root:

- Output directory: `<repo>/docs/snapshots/`
- Filename: `YYYYMMDD-HHMMSS-<topic-slug>.md`

## Execution Script
- Script path: `templates/save-snapshot.py`
- Runs from current project root (or auto-detects via git root)

## Trigger Contract (Hermes side)
Use slash-skill trigger **`/snapshot-save`**.

Why:
- avoids ambiguity from plain text `snapshot`
- avoids semantic conflict with Hermes built-in `/snapshot`
- command-style invocation is stricter and more deterministic in gateway chats

Recommended behavior:
1. User invokes `/snapshot-save` (optional topic argument allowed).
2. Build payload from recent conversation summary.
3. Pipe JSON payload to script with `--stdin-json`.

Example payload:

```json
{
  "topic": "hermes launchpad snapshot workflow",
  "summary": "Aligned trigger/path and implemented project-local snapshot flow.",
  "context": "User requires Hermes-internal usage and docs/snapshots under current repo.",
  "decisions": "Use plain text snapshot trigger; avoid built-in /snapshot semantics conflict.",
  "progress": "save-snapshot.py implemented and validated.",
  "open_questions": "Whether to auto-enable lifecycle hooks after manual phase.",
  "next_actions": [
    "Integrate trigger router",
    "Add restore helper"
  ],
  "references": [
    "templates/save-snapshot.py",
    "docs/snapshot-workflow.md"
  ]
}
```

Execution:

```bash
cat payload.json | python3 templates/save-snapshot.py --stdin-json
```

Or direct args:

```bash
python3 templates/save-snapshot.py \
  --topic "hermes snapshot" \
  --summary "manual run" \
  --context "..." \
  --decisions "..." \
  --progress "..." \
  --open-questions "..." \
  --next-actions "..." \
  --references "..."
```

## Redaction Rules
Script performs mandatory redaction before write:
- API keys/tokens/secrets/passwords
- Bearer auth values
- Private key blocks
- `.env`-style sensitive key values

Replacement marker: `[REDACTED]`

## Output Contract
Script prints JSON:

```json
{
  "ok": true,
  "path": "/abs/path/to/<repo>/docs/snapshots/20260501-123456-topic.md",
  "topic": "...",
  "redaction_hits": 3,
  "project_root": "/abs/path/to/<repo>"
}
```

## Failure Behavior
- On parse/runtime failure: non-zero exit
- No partial malformed output expected
- If target filename exists, script appends a suffix to avoid overwrite
