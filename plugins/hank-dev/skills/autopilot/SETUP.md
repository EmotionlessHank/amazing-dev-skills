# autopilot — Migrating to a New Project (SETUP)

After copying `SKILL.md` into the target project's skills directory, replace all `{placeholders}` with actual project values per the table below, then run the verification steps.

## Placeholder Replacement Checklist

| Placeholder | Meaning | Example (oddfi-frontend) |
|-------------|---------|--------------------------|
| `{DOCS_ROOT}` | Root directory for requirements/plan documents | `.progress` |
| `{type}` | Requirement type subdirectory set | `designs` / `enh` / `bug` / `ud` / `ad` |
| `{ID}` | Requirement ID format | `DD-NNN` / `ENH-NNN` / `BUG-NNN` |
| `{RULES_DIR}` | Project rules directory | `.claude/rules/` |
| `{LESSONS}` | Lessons learned document (optional; delete §0.3 if absent) | `docs/LESSONS.md` |
| `{MAX_FILES_PER_BATCH}` | Max files per batch | `3` |
| `{TYPECHECK}` | Type check command | `pnpm type-check` |
| `{LINT}` | Lint command | `pnpm lint` |
| `{TEST}` | Test command (supports passing file/dir for subset runs) | `pnpm test` |
| `{BUILD}` | Build command | `pnpm build` |
| `{GEN_ASSETS}` | Asset index refresh command (optional; delete related lines if absent) | `pnpm gen-assets` |
| `{QUALITY_SCANNER}` | High-frequency pitfall quick-scan agent (if absent, use a different second agent or fall back to 1) | `quality-scanner` |
| `{DESIGN_IMPL_SKILL}` | UI pixel-perfect implementation workflow (delete Step 1.5 if no UI tasks) | `/figma-impl` |
| `{PROJECT_CONVENTIONS}` | Key conventions injected into review agents | Runtime output in English / decimal.ts / Design Token / testing.md |
| `{EXAMPLE_REQUIREMENT_FOLDER}` | A complete requirement subfolder example path | `.progress/designs/DD-132-invest-page-redesign/` |
| `{SUBAGENT_TRANSCRIPT}` | Persisted subagent transcript path for recovering swallowed reports (delete the fallback sentence if this mechanism is unavailable) | `<session>/subagents/agent-<id>.jsonl` |

> The `ud`/`ad` examples in `{type}` are oddfi-specific types. Remove them for new projects and keep only the generic `designs`/`enh`/`bug` as needed.

## Required Review Agents

Subagent types used in Phase 2 (project must provide these or equivalent substitutes):
- `code-reviewer` (required) — deep code review
- `{QUALITY_SCANNER}` (used as the second agent in default 2-agent mode) — high-frequency pitfall quick scan
- `security-reviewer` / `test-engineer` / `performance-engineer` (for the third agent in 3-agent mode, chosen by domain)

**Minimum requirement**: the project must have at least 1 review subagent that can be spawned in parallel and write its report to a specified absolute path. If none exist → Phase 2 falls back to main-flow self-review + user sign-off (sacrifices the "no self-approval" principle; this must be declared in the report).

> Note: feat uses plan-review perspective agents (critic/architect/design-distiller); autopilot uses code-review perspective agents (code-reviewer/quality-scanner). **They are not interchangeable.**

## Quota-Aware Routing Inputs

迁移后的 Autopilot 必须保留 `scripts/autopilot_quota_router.py` 和唯一 `dispatch_wave()` 调度入口。调用方在每个波次提供以下输入：

- 本次运行 ID 和 Batch 元数据
- 同一额度周期的最新 `/usage` 快照，只包含快照周期、快照时间、周剩余和当天已用
- 当前额度周期通过独立 CLI 参数提供，当前时间由 CLI 使用系统 UTC 时间生成，路由 JSON 内的 `runtime` 不受信
- 实时模型目录中的 Terra、Luna、Spark 模型 ID、可用状态和 reasoning effort
- Luna 或 Spark 的本次运行授权，包含额度周期、Batch 集合、有效期和原始授权文本
- 波次 Batch ID、已完成依赖、独立 worktree、独立分支、文件所有权和运行时资源

The migrated Autopilot must retain `scripts/autopilot_quota_router.py` and the sole `dispatch_wave()` entry. For each wave, provide the run ID, Batch metadata, a fresh `/usage` snapshot, the current quota period as a separate CLI argument, the live model catalog, run-scoped Luna or Spark authorization when required, completed dependencies, isolated worktrees and branches, file ownership, and runtime resources. The CLI generates current time from the system UTC clock and does not trust `runtime` fields from route JSON.

插件不得抓取浏览器会话、Cookie 或非公开账户接口。没有官方机器可读用量时，只接受用户在本次运行提供的 `/usage` 快照。任何缺失、过期或不匹配输入都必须默认拒绝，worker 启动次数为零。主流程必须执行 `python3 scripts/autopilot_quota_router.py --input {ROUTE_REQUEST_FILE} --current-period-id {CURRENT_PERIOD_ID}`。退出码 0 时，只把 `launch_results` 交给 Codex 原生 Agent 工具。顶层 `PARTIAL_BLOCKED` 只允许执行清单中的合格 Batch，并禁止完整门禁、Review、归档和验收。非零退出码必须保持零次 Agent 调用。CLI 还必须校验真实 Git 根目录、common directory 和当前分支，要求同一波次的 linked worktree 属于同一协调仓库，消解符号链接与 macOS 路径别名，并把文件所有权规范成仓库相对路径。

The plugin must not inspect browser sessions, cookies, or private account endpoints. Without official machine-readable usage, accept only a `/usage` snapshot supplied during the current run. Missing, stale, or mismatched inputs must deny by default and start zero workers. Run the router CLI with `--current-period-id {CURRENT_PERIOD_ID}`. On exit code 0, pass only `launch_results` to the Codex native Agent tool. Top-level `PARTIAL_BLOCKED` permits only the eligible listed Batches and blocks the full gate, Review, archive, and acceptance. A nonzero exit must produce zero Agent calls. The CLI also verifies the real Git root, common directory, and branch, requires linked worktrees in one wave to share a coordinating repository, resolves symbolic links and macOS path aliases, and normalizes ownership to repository-relative paths.

## Optional Modules (trim per project)

- No UI/design workflow → delete §0.4 UI detection + §1.3 Step 1.5
- No lessons learned document → delete §0.3
- No asset index script → delete the `{GEN_ASSETS}` line in §1.4
- Not using worktree → simplify §4.2 cleanup to in-branch commits, delete "sync docs back to main workspace"
- **No test infrastructure** (early prototype / pure static site) → §1.3 Step 2 falls back to `{TYPECHECK}` only; delete `{TEST}` from §1.4; declare "this project has no automated tests; all acceptance is manual" in ACCEPTANCE.md
- No output hook report-swallowing issue → delete the `{SUBAGENT_TRANSCRIPT}` recovery fallback sentence in §2.2 item 6

## Verification

1. All placeholders replaced (`grep -n "{.*}" SKILL.md` should only show indicative runtime quantities like `{ID}`/`{platform}`, no unresolved config placeholders)
2. Run the executable router tests:

   `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/hank-dev/tests -v`

3. Run through an existing requirement end-to-end: confirm Phase 1 refreshed the snapshot before every wave, only `ALLOW` decisions reached the fake or real launcher, Phase 2 truly spawned 1–3 subagents that each wrote their own REV file, and Phase 4 produced all three artifacts and surfaced the acceptance checklist in the conversation
4. Confirm the cleanup step **did not auto-push/merge to remote**
