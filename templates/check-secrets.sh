#!/usr/bin/env bash
# Pre-commit hook: scan staged files for leaked secrets.
# Install: cp this to .git/hooks/pre-commit (or use with pre-commit framework)
#
# Exit 0 = clean, Exit 1 = secrets found (blocks commit)

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Patterns: name | regex
PATTERNS=(
  "Anthropic API Key|sk-ant-[A-Za-z0-9_-]{20,}"
  "OpenAI API Key|sk-[A-Za-z0-9]{40,}"
  "Telegram Bot Token|[0-9]{8,12}:[A-Za-z0-9_-]{30,50}"
  "Azure Client Secret|[A-Za-z0-9_~]{8,}~[A-Za-z0-9_~]{20,}"
  "Generic Password Assignment|(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{8,}"
  "Generic Secret Assignment|(?i)(secret|token|api_key|apikey)\s*[=:]\s*['\"][^'\"]{8,}"
  "Private Key Block|-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----"
  "AWS Access Key|AKIA[0-9A-Z]{16}"
  "AWS Secret Key|(?i)aws_secret_access_key\s*[=:]\s*\S+"
)

found=0

# Only scan staged files (not the whole repo)
staged_files=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)

if [ -z "$staged_files" ]; then
  exit 0
fi

for entry in "${PATTERNS[@]}"; do
  name="${entry%%|*}"
  pattern="${entry##*|}"

  # Use grep -P for Perl regex, fall back to grep -E
  matches=$(echo "$staged_files" | xargs grep -PnH "$pattern" 2>/dev/null \
    || echo "$staged_files" | xargs grep -EnH "$pattern" 2>/dev/null \
    || true)

  # Filter out common false positives
  matches=$(echo "$matches" | grep -v '\.env\.example' | grep -v 'check-secrets' | grep -v '\.gitignore' || true)

  if [ -n "$matches" ]; then
    if [ "$found" -eq 0 ]; then
      echo -e "${RED}=== Secret Detection: Blocked Commit ===${NC}"
      echo ""
    fi
    echo -e "${YELLOW}[$name]${NC}"
    echo "$matches" | head -5
    echo ""
    found=1
  fi
done

if [ "$found" -eq 1 ]; then
  echo -e "${RED}Commit blocked. Remove secrets before committing.${NC}"
  echo "If this is a false positive, use: git commit --no-verify"
  exit 1
fi

exit 0
