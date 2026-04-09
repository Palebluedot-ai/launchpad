#!/usr/bin/env python3
"""
Stop hook script: parse Claude Code transcript JSONL → readable Markdown.

Called by Claude Code's Stop hook after every assistant response.
Reads transcript_path from stdin JSON, outputs to docs/sessions/<session_id>.md

Usage (called automatically by hook):
    echo '{"transcript_path":"...","session_id":"..."}' | python3 scripts/save-session.py
"""

import json
import sys
import os
import re
from datetime import datetime
from pathlib import Path


SECRET_PATTERNS = [
    # Telegram bot tokens: digits:AAxxxxx
    (re.compile(r'\b\d{8,12}:[A-Za-z0-9_-]{30,50}\b'), '***TELEGRAM_TOKEN***'),
    # Anthropic API keys
    (re.compile(r'sk-ant-[A-Za-z0-9_-]{20,}'), '***ANTHROPIC_KEY***'),
    # Azure AD / Microsoft Graph secrets (client secrets typically start with ~ or contain ~)
    (re.compile(r'[A-Za-z0-9_~]{8,}~[A-Za-z0-9_~]{20,}'), '***GRAPH_CLIENT_SECRET***'),
    # Azure AD tenant/client IDs (GUIDs)
    (re.compile(r'(?i)(tenant[_-]?id|client[_-]?id)[=:|\s]*[`"]*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'), lambda m: m.group(1) + '=***REDACTED_GUID***'),
    # Generic API keys / Bearer tokens
    (re.compile(r'(?i)(api[_-]?key|token|password|secret|bearer)\s*[=:]\s*\S+'), lambda m: m.group().split('=')[0] + '=***REDACTED***' if '=' in m.group() else m.group().split(':')[0] + ': ***REDACTED***'),
    # Email passwords in .env format
    (re.compile(r'EMAIL_PASSWORD=\S+'), 'EMAIL_PASSWORD=***REDACTED***'),
    # GRAPH env vars with values
    (re.compile(r'MICROSOFT_GRAPH_CLIENT_SECRET=\S+'), 'MICROSOFT_GRAPH_CLIENT_SECRET=***REDACTED***'),
    (re.compile(r'MICROSOFT_GRAPH_TENANT_ID=\S+'), 'MICROSOFT_GRAPH_TENANT_ID=***REDACTED***'),
]


def redact_secrets(text: str) -> str:
    """Replace API keys, tokens, and passwords with placeholders."""
    for pattern, replacement in SECRET_PATTERNS:
        if callable(replacement):
            text = pattern.sub(replacement, text)
        else:
            text = pattern.sub(replacement, text)
    return text


def strip_system_tags(text: str) -> str:
    """Remove <system-reminder>, <local-command-*>, and other system tags."""
    # Remove system-reminder blocks
    text = re.sub(r'<system-reminder>.*?</system-reminder>', '', text, flags=re.DOTALL)
    # Remove local-command blocks
    text = re.sub(r'<local-command-caveat>.*?</local-command-caveat>', '', text, flags=re.DOTALL)
    text = re.sub(r'<local-command-stdout>.*?</local-command-stdout>', '', text, flags=re.DOTALL)
    # Remove command-name/args/message tags
    text = re.sub(r'<command-name>.*?</command-name>', '', text, flags=re.DOTALL)
    text = re.sub(r'<command-message>.*?</command-message>', '', text, flags=re.DOTALL)
    text = re.sub(r'<command-args>.*?</command-args>', '', text, flags=re.DOTALL)
    return text.strip()


def extract_text_content(message: dict) -> str:
    """Extract human-readable text from a message's content field."""
    content = message.get('content', '')
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get('type') == 'text':
                    parts.append(block.get('text', ''))
                elif block.get('type') == 'tool_use':
                    tool = block.get('name', 'unknown')
                    inp = block.get('input', {})
                    # Summarize tool calls concisely
                    if tool == 'Read':
                        parts.append(f"> [Tool: Read `{inp.get('file_path', '?')}`]")
                    elif tool == 'Write':
                        parts.append(f"> [Tool: Write `{inp.get('file_path', '?')}`]")
                    elif tool == 'Edit':
                        parts.append(f"> [Tool: Edit `{inp.get('file_path', '?')}`]")
                    elif tool == 'Bash':
                        cmd = inp.get('command', '?')
                        if len(cmd) > 120:
                            cmd = cmd[:120] + '...'
                        parts.append(f"> [Tool: Bash `{cmd}`]")
                    elif tool == 'Grep':
                        parts.append(f"> [Tool: Grep `{inp.get('pattern', '?')}`]")
                    elif tool == 'Glob':
                        parts.append(f"> [Tool: Glob `{inp.get('pattern', '?')}`]")
                    elif tool == 'Agent':
                        parts.append(f"> [Tool: Agent — {inp.get('description', '?')}]")
                    else:
                        parts.append(f"> [Tool: {tool}]")
                elif block.get('type') == 'tool_result':
                    pass  # Skip tool results to keep output clean
            elif isinstance(block, str):
                parts.append(block)
        return '\n'.join(p for p in parts if p)
    return ''


def parse_transcript(transcript_path: str) -> list[dict]:
    """Parse JSONL transcript into a list of (role, text, timestamp) entries."""
    entries = []
    seen_texts = set()  # deduplicate consecutive identical messages

    with open(transcript_path) as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get('type', '')
            if msg_type not in ('user', 'assistant'):
                continue

            message = obj.get('message', {})
            if not isinstance(message, dict):
                continue

            role = message.get('role', '')
            if role not in ('user', 'assistant'):
                continue

            text = extract_text_content(message)
            if not text:
                continue

            # Clean system tags from user messages
            if role == 'user':
                text = strip_system_tags(text)
                if not text:
                    continue

            # Skip API error messages
            if obj.get('isApiErrorMessage'):
                continue

            # Skip meta messages
            if obj.get('isMeta'):
                continue

            # Deduplicate: skip if same role + same first 200 chars as previous
            dedup_key = f"{role}:{text[:200]}"
            if dedup_key in seen_texts:
                continue
            seen_texts.add(dedup_key)

            timestamp = obj.get('timestamp', '')
            entries.append({
                'role': role,
                'text': text,
                'timestamp': timestamp,
            })

    return entries


def format_markdown(entries: list[dict], session_id: str) -> str:
    """Format parsed entries as readable Markdown."""
    lines = []
    lines.append(f"# Session Log — {session_id[:8]}")
    lines.append("")

    if entries:
        first_ts = entries[0].get('timestamp', '')
        last_ts = entries[-1].get('timestamp', '')
        if first_ts:
            try:
                dt = datetime.fromisoformat(first_ts.replace('Z', '+00:00'))
                lines.append(f"**Started:** {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except (ValueError, TypeError):
                pass
        if last_ts:
            try:
                dt = datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
                lines.append(f"**Last updated:** {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except (ValueError, TypeError):
                pass
        lines.append("")

    lines.append("---")
    lines.append("")

    turn_num = 0
    for entry in entries:
        role = entry['role']
        text = entry['text']

        if role == 'user':
            turn_num += 1
            lines.append(f"## Turn {turn_num}")
            lines.append("")
            lines.append(f"**User:**")
            lines.append("")
            lines.append(text)
            lines.append("")
        elif role == 'assistant':
            lines.append(f"**Assistant:**")
            lines.append("")
            lines.append(text)
            lines.append("")
            lines.append("---")
            lines.append("")

    return '\n'.join(lines)


def main():
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)

    transcript_path = hook_input.get('transcript_path', '')
    session_id = hook_input.get('session_id', '')

    if not transcript_path or not os.path.exists(transcript_path):
        sys.exit(0)

    if not session_id:
        session_id = Path(transcript_path).stem

    # Parse and format
    entries = parse_transcript(transcript_path)
    if not entries:
        sys.exit(0)

    markdown = format_markdown(entries, session_id)
    markdown = redact_secrets(markdown)

    # Write to docs/sessions/ (use CWD — Stop hook runs in project directory)
    project_root = os.getcwd()
    output_dir = os.path.join(project_root, 'docs', 'sessions')
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, f'{session_id[:8]}.md')
    with open(output_file, 'w') as f:
        f.write(markdown)


if __name__ == '__main__':
    main()
