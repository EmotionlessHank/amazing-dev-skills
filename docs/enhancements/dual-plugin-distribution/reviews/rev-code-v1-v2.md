# 代码审查 v1 和 v2

初始结论：请求修复。

- v1 发现 release gate 错误读取工作树、SemVer 不严格、回滚说明不完整、DeepSeek 复核条件表述不准确。
- v2 发现 `--base --head` 模式仍有结构检查读取工作树，且发布内容在相邻提交中没有提高版本。

处理：`validate-distribution.py` 现在从 `--head` 指向的 Git tree 读取全部 metadata、marketplace entry、skills 与 executable mode；版本 parser 拒绝前导零；README 改为按授权和安全扫描条件执行 DeepSeek 独立复核。
