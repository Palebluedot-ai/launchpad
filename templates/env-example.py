#!/usr/bin/env python3
"""
Generate .env.example from an existing .env file.

Reads .env, strips all values (keeps keys + comments), writes .env.example.
Safe to run multiple times — always overwrites .env.example.

Usage:
    python3 env-example.py                    # reads .env in CWD
    python3 env-example.py /path/to/.env      # reads specific file
"""

import re
import sys
from pathlib import Path


def generate_example(env_path: Path) -> str:
    """Read .env and return sanitized .env.example content."""
    lines = []
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()

        # Preserve blank lines and comments as-is
        if not line or line.startswith('#'):
            lines.append(raw_line)
            continue

        # Match KEY=VALUE (with optional export prefix)
        match = re.match(r'^(export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
        if match:
            prefix = match.group(1) or ''
            key = match.group(2)
            lines.append(f'{prefix}{key}=')
        else:
            # Non-standard line, keep as-is
            lines.append(raw_line)

    return '\n'.join(lines) + '\n'


def main():
    if len(sys.argv) > 1:
        env_path = Path(sys.argv[1])
    else:
        env_path = Path('.env')

    if not env_path.exists():
        print(f"No {env_path} found — skipping .env.example generation.")
        sys.exit(0)

    example_content = generate_example(env_path)
    output_path = env_path.parent / '.env.example'
    output_path.write_text(example_content)
    print(f"Generated {output_path} ({sum(1 for l in example_content.splitlines() if '=' in l)} keys)")


if __name__ == '__main__':
    main()
