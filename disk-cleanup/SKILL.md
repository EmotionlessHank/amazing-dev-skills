---
name: disk-cleanup
description: 开发存储磁盘清理。当用户说 "/disk-cleanup"、"磁盘满了"、"硬盘占用太多"、"清理 worktree"、"空间不足" 时触发。分层调研定位大头（worktree/Docker/缓存/用户文件），逐类安全核查后清理，全程零数据丢失。与 mac-cleanup（系统应用审计）配套。
version: 1.0.0
---

# /disk-cleanup — 开发存储磁盘清理

四阶段流程：**分层调研定位大头 → 安全核查 → 分类清理 → 验证释放效果**。

核心原则：
- 调研和清理是两个独立步骤，**调研先出报告，用户点头后才动手删**
- 每一类删除前都有对应的安全核查，宁可少删不可误删
- 与 [mac-cleanup](../mac-cleanup) 分工：本技能管**开发存储**（git worktree、Docker、开发缓存、用户媒体、临时仓库）；mac-cleanup 管**系统层**（应用、Homebrew/npm/pip、Xcode DerivedData）。磁盘告急时两个连跑覆盖最全。

---

## 触发条件

用户说出以下任意关键词：
- `/disk-cleanup`
- `磁盘满了`、`硬盘占用`、`空间不足`、`清理 worktree`
- `disk full`、`worktree cleanup`

---

## 阶段 1：分层调研（只读，先出报告）

```bash
df -h /                                          # 总盘 + 可用（APFS 看 Avail，不看 Capacity 百分比）
du -xsh ~/* 2>/dev/null | sort -rh | head -20    # 用户目录大头
du -xsh ~/Library/* | sort -rh | head -20        # 通常 Library 最大
du -xsh ~/Library/"Application Support"/* ~/Library/Containers/* ~/Library/Caches/* | sort -rh
du -xsh {WORK_DIR}/* | sort -rh                  # 各项目目录
```

常见大头（按实测经验，前端项目尤甚）：
- **`<项目>/.claude/worktrees/`** — Claude Code worktree 堆积，前端项目每个自带 1.5~2G 的 `node_modules` + `.next`，往往是单项最大可回收源（实测一个项目 32 个 worktree 占 22G）
- **`~/Library/Containers/com.docker.docker`** — Docker 构建缓存 + 无用镜像（实测可回收 19G）
- **`~/Library/Caches/`** — Spotify / JetBrains / go-build / ms-playwright / Homebrew，全部可安全重建
- **`~/Movies`、`~/Downloads`、名字带 temp 的项目目录** — 需用户决定

报告按「可回收大小 × 安全度」排序，标明哪些可自动清、哪些需用户拍板，**等用户确认范围后再进入阶段 2**。

---

## 阶段 2：安全核查（删除前的硬性门槛）

### Git worktree

1. `git worktree list` 找出**注册的** worktree；目录数往往多于注册数（存在孤儿目录）
2. ⚠️ **陷阱：孤儿目录的 git 读数会撒谎** —— 对非注册目录跑 `git -C <dir> status/log` 会 fallback 到主仓，显示「main / 今天有提交 / 0 改动」，全是主仓的数据。孤儿目录的活跃度只能看**文件 mtime**
3. ⚠️ **陷阱：squash 合并下 `git merge-base --is-ancestor` 永远报「未合并」**，不能作为清理依据。改用三条判定：
   - `git -C <wt> status --porcelain` 为空（无未提交改动）
   - `git rev-list --count origin/<branch>..<branch>` 检查未推送提交（报「无远程分支」= 从未推过，需注意）
   - `git worktree remove` 只删工作副本，**分支引用永远保留在主仓**，可随时重建
4. 活跃度判定：feature 分支看 `git log -1 --format=%cs`；main 上的 worktree 和孤儿目录看实际文件 mtime（排除 node_modules）
5. 孤儿目录（`git worktree remove` 报 "is not a working tree"）：逐一 `ls -A` 检查，**只含 `.next` / `node_modules` / `.omc` / `.progress` / `tsconfig.tsbuildinfo` 等构建产物和会话状态才可 `rm -rf`**，发现源码立即停手报告

### Docker

```bash
docker system df            # 看 RECLAIMABLE 列
docker builder prune -af    # 构建缓存（通常是大头）
docker image prune -af      # 无用镜像
# 卷（Volumes）不动 —— 含数据库数据
```

`Docker.raw` 是稀疏文件，prune 后空间逐步归还系统；想立即回收就重启 Docker Desktop。

### 应用缓存

删除前 `pgrep -fl <app>` 确认应用没在运行（JetBrains 运行中删缓存可能索引损坏）。可安全清：`~/Library/Caches/` 下的 JetBrains、com.spotify.client、go-build、ms-playwright、Homebrew。

### 用户文件（Movies / Downloads / temp 项目）

1. **删前必须 `ls -lhR` 看实际内容**，不能凭目录名删 —— 实测案例：「personal movie」实际是下载的动漫（可删），但同目录的剪映工程文件是用户创作内容（必须保留并说明）
2. 下载的影视/媒体可删（可重新下载）；**用户创作的素材（剪映工程、录屏、照片）保留**，不确定就问
3. **临时 git 仓库**：先 `git branch -vv` + `git log --branches --not --remotes` 检查未推送分支；有则 `git push <remote> --all` 全量归档到远程，**确认推送成功后才删本地**
4. push 报 `Repository not found` / 403 / 404 → 多账号场景：`gh auth status` 列账号 → 切到能看到仓库的账号 → 重试 → **成功后切回原默认账号**

---

## 阶段 3：执行

- 大体积 `rm -rf` 和 docker prune 后台并行跑
- worktree 批量删：保留名单用 case 跳过，`git worktree remove` 失败回退 `--force`（前提：已核查无未提交改动），最后 `git worktree prune`

---

## 阶段 4：验证与汇报

```bash
df -h /                # 对比清理前后 Avail
du -xsh <各清理目标>    # 分项核对
```

汇报格式：总释放量 + 分项明细（每项：释放多少、做了什么安全核查、保留了什么及原因）。

---

## 成功标准

- 磁盘可用空间显著回升，且与分项明细加总一致
- 零数据丢失：所有删除项事先通过对应核查（无未提交 / 未推送 / 非用户创作）
- 用户拍板项（媒体文件、temp 仓库）均先报告内容再执行

## 复发预防

worktree 堆积会复发。建议：功能合并后顺手 `git worktree remove`，或每隔几周重跑本技能的调研阶段。

## 实测战绩

首次执行（2026-06）：磁盘可用空间 35G → 97G，释放约 62G（worktree 20G + Docker 19G + 缓存 9G + 媒体/temp 仓库 24G），零数据丢失（15 个未推送分支先归档到远程私有仓再删本地）。
