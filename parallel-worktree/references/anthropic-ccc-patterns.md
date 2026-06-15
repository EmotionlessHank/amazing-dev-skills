# Anthropic C Compiler Parallel Patterns Reference

> Source: Engineering practices from Nicholas Carlini (Anthropic) building a 100k-line Rust C compiler using 16 parallel Claude agents.

## Core Architecture Patterns

### 1. Git File Locking (Distributed Mutual Exclusion)

```
current_tasks/
  parse_if_statement.txt      ← Claimed by Agent A
  codegen_function_def.txt    ← Claimed by Agent B
```

- Claim: write file + git push
- Conflict: second push fails → pull → sees the lock → picks a different task
- Release: delete file + push code

**Adaptation for this project**: Use markdown files in `.progress/tasks/` to implement a similar mechanism — each worktree agent claims an independent todo item.

### 2. Role Specialization

Not every agent does the same work:

| Role | Project Equivalent |
|------|--------------------|
| Core implementation agent | Page/component development |
| Deduplication expert | Code reuse review |
| Performance optimizer | Bundle / rendering performance |
| Design reviewer | Review Agent |
| Documentation maintainer | DD document updates |

### 3. RALPH Loop (Infinite loop + fresh context each iteration)

```bash
while true; do
    claude --dangerously-skip-permissions \
           -p "$(cat AGENT_PROMPT.md)" &> "agent_logs/agent_${COMMIT}.log"
done
```

Each iteration starts a fresh session; "memory" is passed via external files. Useful for overnight batch processing.

### 4. Context Management Strategy

- Keep console output minimal (a few lines)
- Write detailed information to log files
- Use aggregated summaries instead of raw output
- Fresh context each session; pass state via README/progress files

### 5. Solving the "GCC Oracle" Anti-Pattern

Problem: Multiple agents simultaneously discover and fix the same bug (herd behavior).

Solution: Break the overall debugging problem into independently claimable sub-problems, with each agent responsible for a different file/module.

**Adaptation for this project**: Naturally isolated by route directory — each worktree is responsible for the file scope of exactly one page.

## Key Lessons

1. **Design the environment, not the solution** — Invest effort in the test suite and feedback mechanisms
2. **Near-perfect validators** — If tests have gaps, agents will "solve the wrong problem"
3. **Specialized roles > general-purpose agents** — Dedicated refactorer, optimizer, and critic roles
4. **Context rotation** — Fresh session each iteration prevents context window exhaustion
5. **Parallelism requires creative decomposition** — Not all tasks are naturally parallelizable; it takes engineering to split them correctly
