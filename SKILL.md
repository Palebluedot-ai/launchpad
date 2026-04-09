---
name: launchpad
version: 0.2.0
description: |
  Zero-to-one project scaffolding — smart CLAUDE.md, conversation persistence,
  secret safety, and doc-driven development from day one.
  Use when starting a new project, or when the user says
  "初始化", "set up project", "launchpad", "setup hooks", "bootstrap".
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
---

# Launchpad — Project Scaffolding

You are setting up a new project with the user's standard work habits.
This is a **document-driven development** scaffolding — every project should
have conversation persistence, structured docs, and clean git hygiene from day one.

## Step 1: Detect project state

Before creating anything, check what already exists:

```bash
echo "=== Project State ==="
echo "CWD: $(pwd)"
echo "Git: $(git rev-parse --is-inside-work-tree 2>/dev/null || echo 'no')"
echo "CLAUDE.md: $([ -f CLAUDE.md ] && echo 'exists' || echo 'missing')"
echo "Settings: $([ -f .claude/settings.local.json ] && echo 'exists' || echo 'missing')"
echo ".gitignore: $([ -f .gitignore ] && echo 'exists' || echo 'missing')"
echo ".env: $([ -f .env ] && echo 'exists' || echo 'missing')"
echo ".env.example: $([ -f .env.example ] && echo 'exists' || echo 'missing')"
echo "docs/: $([ -d docs ] && echo 'exists' || echo 'missing')"
echo "pre-commit: $([ -f .git/hooks/pre-commit ] && echo 'exists' || echo 'missing')"
```

Then run the project type detector to understand the project:

```bash
bash ${CLAUDE_SKILL_DIR}/detectors/project-type.sh
```

Tell the user what already exists and what will be created. Ask for confirmation before proceeding.

## Step 2: Configure Stop hook

If `.claude/settings.local.json` does not exist, create it. If it exists, merge the hooks config into it (do not overwrite existing permissions or other hooks).

The hook config should be:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_SKILL_DIR}/templates/save-session.py"
          }
        ]
      }
    ]
  }
}
```

The save-session script lives in the skill directory (shared by all projects).
It uses CWD to find the project root, so it works correctly from any project.

**Do NOT copy save-session.py into the project.** The hook runs the global copy directly.

## Step 3: Create CLAUDE.md (smart detection)

If `CLAUDE.md` does not exist, create a lean one (under 200 lines).

Use the output from the project type detector (Step 1) to populate build/test/lint commands.
Do not use placeholder commands — only include commands that actually exist in the project.

Structure:

```markdown
# {Project Name} — 项目上下文

## 构建命令
- `{detected build_cmd}` — 安装依赖
- `{detected test_cmd}` — 运行测试
- `{detected lint_cmd}` — 代码检查
{if dev_cmd: - `{detected dev_cmd}` — 开发服务器}

{if framework: ## 技术栈\n- 框架：{framework}}

## 项目状态
- 当前阶段：初始化
- 上次更新：{today's date}

## 开发规则
1. 先确认再写代码 — 涉及外部服务时先确认权限和配置
2. 所有上下文固化 — 关键决策写入此文件或 docs/snapshots/
3. 敏感信息脱敏 — session log 自动脱敏，不在文档中写密码/token

## 对话固化
- Stop hook 自动保存对话到 `docs/sessions/`
- 手动快照：`/snapshot`
- 敏感信息自动脱敏
```

**Rules for CLAUDE.md generation:**
- Only include sections with real data (no empty placeholders)
- Detect project name from `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, or directory name
- If CI is detected, note it: `CI：GitHub Actions / GitLab CI`
- If Docker is detected, add relevant commands

## Step 4: Create .gitignore

If `.gitignore` does not exist, create one. If it exists, check and append only missing entries.

Required entries:
```
# Secrets
.env
*.env
.token_cache.json

# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/

# Logs & Data
logs/
*.log
*.db
*.sqlite

# OS
.DS_Store

# IDE
.idea/
.vscode/

# Claude Code
.claude/
*.save
```

## Step 5: Create docs structure

```bash
mkdir -p docs/sessions docs/snapshots
```

Then create `docs/sessions/.gitignore` to prevent session logs from being committed:

```
# Session logs are local — do not commit
*
!.gitignore
```

## Step 6: Generate .env.example

If `.env` exists but `.env.example` does not:

```bash
python3 ${CLAUDE_SKILL_DIR}/templates/env-example.py
```

This strips all values from `.env` and writes a clean `.env.example` with only keys and comments.

If `.env` does not exist, skip this step.

## Step 7: Install pre-commit secret scanner

If `.git/hooks/pre-commit` does not exist and this is a git repo:

```bash
cp ${CLAUDE_SKILL_DIR}/templates/check-secrets.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

If a pre-commit hook already exists, tell the user about `check-secrets.sh` and suggest they integrate it manually.

## Step 8: Summary

After everything is set up, print a summary:

```
✅ Launchpad 完成！

已配置：
- [x] Stop hook — 对话自动保存到 docs/sessions/
- [x] CLAUDE.md — 项目上下文（智能检测）
- [x] .gitignore — 排除敏感文件
- [x] docs/ — sessions/（已 gitignore）+ snapshots/
- [x] .env.example — 环境变量模板（如果有 .env）
- [x] pre-commit hook — 提交前 secret 扫描

使用方式：
- 对话自动保存，无需手动操作
- 关键节点输入 /snapshot 拍快照
- 项目状态更新到 CLAUDE.md
- 提交代码时自动扫描敏感信息
```

Use `[x]` for items that were created, `[ ]` for items that were skipped (already existed or not applicable).

## Important rules

- **Never overwrite** existing files without asking. If a file exists, show the diff and ask.
- **Language**: Follow the user's language (Chinese or English).
- **No secrets**: Never write real credentials into any created file.
- **Idempotent**: Running /launchpad twice should be safe — skip what's already there.
- **Smart defaults**: Use detected project info, never hardcode placeholder commands.
