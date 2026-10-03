# scripts

三个通用文件 / Three general-purpose files:

- `run.sh` 加 `prelude.py`：运行浏览器脚本的外壳。`bash run.sh <script.py> [秒数]`。只关闭本次任务自己通过 `new_tab` 打开并登记的标签，用户的标签和运行期间新开的标签不碰。超时发送 SIGINT，让 `finally` 先清理；macOS 需要 `brew install coreutils` 提供 `gtimeout`。权威版本在 skill `revium-browser-test` 的 `templates/browser-harness/`。
  Runs a browser-harness script. It closes only the tabs this job opened through `new_tab`, never the user's own or ones opened mid-run, and the time limit sends SIGINT so the `finally` block runs.
- `jev.py`：调用 Jev（TypeSafe System One）的最小封装，需要环境变量 `TYPESAFE_API_KEY`，请求头里只放占位符，运行时展开。
  A minimal Jev client; the key comes from `TYPESAFE_API_KEY` and the header holds only a placeholder expanded at run time.

2026-10 South Yarra 案例的完整流水线脚本（取数、筛选、打分、拼图、报告和 PPT 生成）依赖当时的数据文件，不是通用库，不随插件发布。
The full pipeline scripts from the South Yarra run depend on that case's data files and are not a general library, so they are not shipped in the plugin.
