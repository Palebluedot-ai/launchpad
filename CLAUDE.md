# launchpad-skill — 项目上下文

## 项目简介
这是一个 Claude Code Skill，提供「零到一」项目脚手架功能：
新项目执行 /launchpad 即可一键完成对话固化、敏感信息防护、文档结构初始化。

## 项目结构
- `SKILL.md` — Skill 主定义文件（触发条件、执行步骤）
- `detectors/project-type.sh` — 自动检测项目类型（Python/Node/Go等）
- `templates/save-session.py` — Stop hook 脚本，将对话转为 Markdown 并脱敏
- `templates/env-example.py` — 从 .env 生成 .env.example
- `templates/check-secrets.sh` — pre-commit 密钥扫描脚本

## 项目状态
- 当前阶段：开发中
- GitHub: Palebluedot-ai/launchpad-skill
- 上次更新：2026-04-12
- 最近进展：独立 repo + GitHub 上传，配置 Telegram 远程通道（待验证连通）
- 最新快照：docs/snapshots/2026-04-12-164725.md

## 开发规则
1. **不在自己身上装 Stop hook** — 避免开发 save-session.py 时递归崩溃
2. **改 save-session.py 后手动测试** — 用真实 transcript 跑一遍再提交
3. **保持 SKILL.md 和 templates/ 同步** — SKILL.md 里引用的文件路径不能写错
4. **敏感信息脱敏** — 测试时不写入真实 token

## 对话固化
- 本项目暂未启用 Stop hook（开发自身 skill 时避免递归依赖）
- Hermes 会话使用 `/snapshot-save` 触发项目快照，写入 `docs/snapshots/`
- 内置 `/snapshot` 保留给 Hermes 系统快照语义，不用于项目上下文沉淀
