# Anthropic C 编译器并行模式参考

> 来源：Nicholas Carlini (Anthropic) 用 16 并行 Claude Agent 构建 10 万行 Rust C 编译器的工程实践。

## 核心架构模式

### 1. Git 文件锁（分布式互斥）

```
current_tasks/
  parse_if_statement.txt      ← Agent A 认领
  codegen_function_def.txt    ← Agent B 认领
```

- 认领：写文件 + git push
- 冲突：第二个 push 失败 → pull → 看到锁 → 换任务
- 释放：删文件 + push 代码

**本项目适配**：用 `.progress/tasks/` 中的 markdown 文件实现类似机制，每个 worktree Agent 认领独立 todo 条目。

### 2. 角色分工

不是每个 Agent 都做相同的事：

| 角色 | 本项目对应 |
|------|-----------|
| 核心实现 Agent | 页面/组件开发 |
| 去重专家 | 代码复用审查 |
| 性能优化师 | Bundle / 渲染性能优化 |
| 设计评审员 | Review Agent |
| 文档维护者 | DD 文档更新 |

### 3. RALPH 循环（无限循环 + 全新上下文）

```bash
while true; do
    claude --dangerously-skip-permissions \
           -p "$(cat AGENT_PROMPT.md)" &> "agent_logs/agent_${COMMIT}.log"
done
```

每轮全新 session，通过外部文件传递"记忆"。适用于过夜批处理场景。

### 4. 上下文管理策略

- 控制台输出极简（几行）
- 详细信息写日志文件
- 聚合统计代替原始输出
- 每轮 session 全新上下文，靠 README/进度文件传递记忆

### 5. "GCC 预言机"反模式解决

问题：多个 Agent 同时发现并修复同一个 bug（羊群效应）。

解法：将整体调试问题拆成可独立认领的小问题，每个 Agent 负责不同的文件/模块。

**本项目适配**：按路由目录天然隔离，每个 worktree 只负责一个页面的文件范围。

## 关键教训

1. **设计环境，不设计解决方案** — 精力花在测试套件和反馈机制上
2. **近乎完美的验证器** — 如果测试有缺口，Agent 会"解决错误的问题"
3. **专门角色 > 通用 Agent** — 有专门的 refactorer、optimizer、critic
4. **上下文轮转** — 每轮全新 session 避免上下文窗口耗尽
5. **并行需要创造性分解** — 不是所有任务天然可并行，需要工程化拆分
