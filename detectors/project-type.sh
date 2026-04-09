#!/usr/bin/env bash
# Detect project type, framework, and build/test commands.
# Outputs JSON to stdout for consumption by SKILL.md instructions.
#
# Usage: bash project-type.sh [project_dir]

set -euo pipefail

DIR="${1:-.}"
cd "$DIR"

# --- Helpers ---
has_file() { [ -f "$1" ]; }
has_dir()  { [ -d "$1" ]; }
json_escape() { printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()), end="")'; }

# --- Detect project type ---
type="unknown"
name=""
framework=""
python_version=""
node_version=""
build_cmd=""
test_cmd=""
lint_cmd=""
dev_cmd=""
has_ci="false"
has_docker="false"
has_env="false"
extra_info=""

# Python detection
if has_file "pyproject.toml"; then
  type="python"
  name=$(python3 -c "
import tomllib, sys
try:
    with open('pyproject.toml','rb') as f: d=tomllib.load(f)
    print(d.get('project',{}).get('name',''))
except: pass
" 2>/dev/null || true)
  python_version=$(python3 -c "
import tomllib
with open('pyproject.toml','rb') as f: d=tomllib.load(f)
print(d.get('project',{}).get('requires-python',''))
" 2>/dev/null || true)

  # Detect test framework
  if grep -q 'pytest' pyproject.toml 2>/dev/null; then
    test_cmd="uv run pytest"
  elif has_file "tests/" || has_dir "tests/"; then
    test_cmd="uv run python -m pytest"
  fi

  # Detect linter
  if grep -q 'ruff' pyproject.toml 2>/dev/null; then
    lint_cmd="uv run ruff check ."
  elif grep -q 'flake8' pyproject.toml 2>/dev/null; then
    lint_cmd="uv run flake8"
  fi

  # Detect type checker
  if grep -q 'mypy' pyproject.toml 2>/dev/null; then
    extra_info="mypy configured"
  fi

  build_cmd="uv sync"

elif has_file "setup.py" || has_file "requirements.txt"; then
  type="python"
  name=$(basename "$PWD")
  build_cmd="pip install -e ."
  test_cmd="python -m pytest"
fi

# Node.js detection
if has_file "package.json"; then
  if [ "$type" = "unknown" ]; then
    type="node"
  else
    type="${type}+node"
  fi

  node_name=$(python3 -c "
import json
with open('package.json') as f: d=json.load(f)
print(d.get('name',''))
" 2>/dev/null || true)
  [ -z "$name" ] && name="$node_name"

  # Detect scripts
  scripts=$(python3 -c "
import json
with open('package.json') as f: d=json.load(f)
s=d.get('scripts',{})
for k in ['dev','start','build','test','lint']:
    if k in s: print(f'{k}={s[k]}')
" 2>/dev/null || true)

  if echo "$scripts" | grep -q '^dev='; then
    dev_cmd="npm run dev"
  fi
  if echo "$scripts" | grep -q '^build='; then
    build_cmd="npm run build"
  fi
  if echo "$scripts" | grep -q '^test='; then
    test_cmd="npm test"
  fi
  if echo "$scripts" | grep -q '^lint='; then
    lint_cmd="npm run lint"
  fi

  # Detect framework
  deps=$(python3 -c "
import json
with open('package.json') as f: d=json.load(f)
all_deps = list(d.get('dependencies',{}).keys()) + list(d.get('devDependencies',{}).keys())
print(' '.join(all_deps))
" 2>/dev/null || true)

  if echo "$deps" | grep -q 'next'; then
    framework="Next.js"
  elif echo "$deps" | grep -q 'nuxt'; then
    framework="Nuxt"
  elif echo "$deps" | grep -q 'vite'; then
    framework="Vite"
  elif echo "$deps" | grep -q 'express'; then
    framework="Express"
  elif echo "$deps" | grep -q 'fastify'; then
    framework="Fastify"
  elif echo "$deps" | grep -q 'react'; then
    framework="React"
  elif echo "$deps" | grep -q 'vue'; then
    framework="Vue"
  elif echo "$deps" | grep -q 'svelte'; then
    framework="Svelte"
  fi
fi

# Go detection
if has_file "go.mod"; then
  [ "$type" = "unknown" ] && type="go" || type="${type}+go"
  [ -z "$name" ] && name=$(head -1 go.mod | awk '{print $2}' | xargs basename)
  build_cmd="go build ./..."
  test_cmd="go test ./..."
  lint_cmd="golangci-lint run"
fi

# Rust detection
if has_file "Cargo.toml"; then
  [ "$type" = "unknown" ] && type="rust" || type="${type}+rust"
  [ -z "$name" ] && name=$(grep '^name' Cargo.toml | head -1 | sed 's/.*= *"\(.*\)"/\1/')
  build_cmd="cargo build"
  test_cmd="cargo test"
  lint_cmd="cargo clippy"
fi

# Fallback name
[ -z "$name" ] && name=$(basename "$PWD")

# Makefile / justfile
if has_file "Makefile"; then
  extra_info="${extra_info:+$extra_info, }Makefile present"
fi
if has_file "justfile"; then
  extra_info="${extra_info:+$extra_info, }justfile present"
fi

# CI detection
if has_dir ".github/workflows" || has_file ".gitlab-ci.yml" || has_file ".circleci/config.yml"; then
  has_ci="true"
fi

# Docker detection
if has_file "Dockerfile" || has_file "docker-compose.yml" || has_file "compose.yml"; then
  has_docker="true"
fi

# .env detection
if has_file ".env"; then
  has_env="true"
fi

# --- Output JSON ---
cat <<ENDJSON
{
  "type": $(json_escape "$type"),
  "name": $(json_escape "$name"),
  "framework": $(json_escape "$framework"),
  "python_version": $(json_escape "$python_version"),
  "build_cmd": $(json_escape "$build_cmd"),
  "test_cmd": $(json_escape "$test_cmd"),
  "lint_cmd": $(json_escape "$lint_cmd"),
  "dev_cmd": $(json_escape "$dev_cmd"),
  "has_ci": $has_ci,
  "has_docker": $has_docker,
  "has_env": $has_env,
  "extra_info": $(json_escape "$extra_info")
}
ENDJSON
