# 自动化验证

- `python3 plugins/hank-dev/scripts/validate-distribution.py` 通过。
- `python3 plugins/hank-dev/scripts/validate-distribution.py --base HEAD~1 --head HEAD` 通过。
- `claude plugin validate . --strict` 通过。
- `claude plugin validate ./plugins/hank-dev --strict` 通过。
- `bash plugins/hank-dev/scripts/validate-review-security.sh` 通过。
- `python3 -m unittest discover -s worktree-cleanup/tests -p 'test_*.py'`，14 项通过。
- 临时 Codex marketplace 安装 `hank-dev` 0.2.0 成功，5 个 skills 与 3 个可执行 scripts 均在缓存中存在。
- 临时 plugin 与 marketplace 已删除，`hank-dev@personal` 保持启用、版本 `0.1.12+codex.e6b3e8e`、来源 `/Users/hang/plugins/hank-dev`。
