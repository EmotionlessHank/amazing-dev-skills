---
name: mac-cleanup
description: macOS 系统清理审计。当用户说 "/mac-cleanup"、"清理电脑"、"系统清理"、"磁盘清理"、"清理软件" 时触发。先只读扫描，再按风险和可恢复性分级执行清理，并输出结构化报告。
version: 1.2.0
---

# /mac-cleanup：macOS 系统清理审计

用于定位长期未使用应用、开发缓存、包管理器缓存和 Docker 资源。默认只读扫描，任何删除都必须经过用户对精确目标的确认。

## 触发条件

- `/mac-cleanup`
- 清理电脑、系统清理、磁盘清理、清理软件
- mac cleanup、disk cleanup

## 核心安全边界

- 应用上次使用时间仅是候选信号，不能单独作为删除依据。
- 缓存必须同时说明大小、用途、重建成本和删除影响。
- 浏览器 Profile、聊天媒体、应用数据、Docker volume、数据库目录均不属于默认清理项。
- 不在运行中的应用上直接清理其缓存目录。应用仍运行时，先说明缓存可能立即重建，并等待用户选择退出后清理或跳过。
- 不执行包含多个不可恢复操作的长脚本。每一类操作完成后必须核验，再继续下一类。
- 不克隆或安装第三方清理工具作为默认兜底。只有本地审计能力确实不足时，才可按不明仓库审计流程评估外部工具。

## Step 0：预检与基线

先判定用户的问题是空间不足还是性能问题，并保存清理前基线。

```bash
df -h / /System/Volumes/Data
uptime
memory_pressure -Q
sysctl vm.swapusage
```

如果可用空间充足但 CPU、WindowServer、swap 或压缩内存异常，空间清理不是卡顿的直接修复。应转入 `/Users/hang/.codex/skills/macos-performance-triage/SKILL.md`。

报告必须说明：

- 磁盘是否接近满载
- 本次属于紧急修复还是日常维护
- 清理预期是回收空间，还是能直接改善性能

## Step 1：扫描应用并进行权限预检

```bash
find /Applications -maxdepth 2 -name '*.app' -exec mdls -name kMDItemLastUsedDate -name kMDItemDisplayName -name kMDItemPhysicalSize {} \; 2>/dev/null | paste - - - | sort
find /Applications -maxdepth 2 -name '*.app' -exec du -sm {} + 2>/dev/null | sort -rn
```

对用户选择删除的每个应用，删除前执行：

```bash
stat -f '%N %Su:%Sg %Sp' '/Applications/{APP}.app'
ls -ldeO '/Applications/{APP}.app'
pgrep -ifl '{APP}' || true
```

处理规则：

- 当前用户拥有且未运行的应用，优先移入废纸篓。
- root 拥有或带限制 ACL 的应用，标记为“需要管理员交互”。非交互式命令环境无法读取 `sudo` 密码时，不要反复执行 `sudo`，改为让用户在真实终端或 Finder 中完成认证。
- 应用正在运行时，先等待用户选择是否退出。禁止强制结束用户应用。
- `kMDItemLastUsedDate` 为 null 或明显与实际使用不符时，标记为“使用记录不可靠”，不得据此推荐删除。
- 系统应用和当前工作流已知依赖的应用，默认排除。

## Step 2：扫描 Homebrew、npm、pip 与 pnpm

```bash
brew list --formula
brew list --cask
brew autoremove --dry-run
brew cleanup --dry-run
du -sh "$(brew --cache)"
du -sh /opt/homebrew/Cellar/* 2>/dev/null | sort -rh | head -15

npm list -g --depth=0
du -sh "$(npm root -g)" ~/.npm 2>/dev/null

python3 -m pip list
du -sh ~/Library/Caches/pip 2>/dev/null

pnpm store status 2>/dev/null
pnpm store path 2>/dev/null | xargs -I{} du -sh '{}' 2>/dev/null
```

缓存分级：

| 等级 | 典型项目 | 删除影响 |
|---|---|---|
| 低风险 | Homebrew 已淘汰版本、明确旧更新安装包、npm 临时下载 | 可重新下载 |
| 有重下载成本 | npm `_cacache`、pip 缓存、Homebrew 下载缓存、pnpm store | 下次安装耗时增加 |
| 有重建成本 | Xcode DerivedData、IDE 索引、Playwright 浏览器 | 下次构建或测试耗时增加 |
| 高重建成本 | Hugging Face 模型、Codex runtimes、Puppeteer 浏览器、uv 包缓存 | 可能需要大量下载或构建 |
| 逐项确认 | Docker 资源、数据库目录、浏览器 Service Worker | 可能丢失工作数据或登录状态 |

## Step 3：扫描用户缓存与开发缓存

```bash
du -sh ~/Library/Caches/* 2>/dev/null | sort -rh | head -30
du -sh ~/.cache 2>/dev/null
du -sh ~/Library/Developer/Xcode/DerivedData ~/Library/Developer/Xcode/Archives ~/Library/Developer/CoreSimulator 2>/dev/null
```

对应用缓存执行前检查进程：

```bash
pgrep -ifl '{APP_NAME}' || true
```

对 Chrome 必须区分 Profile 和纯缓存：

```bash
chrome_root="$HOME/Library/Application Support/Google/Chrome"
du -sh "$chrome_root" 2>/dev/null
find "$chrome_root" -maxdepth 1 -type d \( -name 'Default' -o -name 'Profile *' \) -print
du -sh "$chrome_root"/Default/{Service\ Worker,Extensions,Sessions,GPUCache} 2>/dev/null
ps -axo pid,ppid,%cpu,%mem,rss,etime,state,command | grep '/Google Chrome' | grep -v grep || true
```

禁止整目录删除 Chrome Profile、Service Worker、项目自定义 `chrome-profile` 或其他保存登录态的目录。

## Step 4：Docker 专项审计

Docker 未运行时，先报告状态。只有用户确认后，才启动 Docker Desktop 进行进一步审计。

Docker 可用后按以下顺序执行：

```bash
docker context show
docker ps -a --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Labels}}'
docker volume ls
docker network ls
docker system df -v
```

处理规则：

- 通过 Compose 标签、项目目录、容器名和镜像共同确认资源归属。
- 已确认项目的停止容器与专属网络可以作为一组候选项。
- volume，尤其数据库 volume，必须单独展示名称、挂载点、风险和预计空间。只有用户明确点名该 volume 后才能删除。
- 镜像、Build Cache 和未使用匿名卷另列为独立清理项，不从“删除容器”推断删除权限。
- Docker Desktop 的虚拟磁盘可能不会立刻缩小。报告 Docker 逻辑可回收空间与宿主文件系统实际可用空间，不混为一谈。

## Step 5：输出结构化清理报告

报告至少包含：

```text
# macOS 系统清理报告（{日期}）

## 基线
| 项目 | 清理前 | 清理后 | 说明 |

## 长期未使用应用候选
| 应用 | 最后使用 | 大小 | 权限状态 | 风险 | 建议 |

## 可重建缓存
| 路径或工具 | 大小 | 重建成本 | 应用是否运行 | 建议 |

## 应用数据与浏览器数据
| 路径 | 大小 | 可能内容 | 风险 | 处理方式 |

## Docker
| 类型 | 名称 | 项目归属证据 | 大小或可回收空间 | 风险 | 建议 |

## 待确认操作
| 精确目标 | 动作 | 是否可恢复 | 预估影响 |

## 执行结果
| 目标 | 动作 | 状态 | 实际回收或暂存空间 |

## 汇总
| 已永久释放 | 废纸篓暂存 | 待确认可回收 | 当前可用空间 |
```

必须区分：

- 已永久释放空间
- 已移入废纸篓，尚未释放的空间
- Docker 逻辑可回收空间
- 仅为候选、尚未执行的空间

## Step 6：确认与执行

得到用户确认后，先生成操作台账。每项至少包含来源路径或 Docker 资源名、动作、大小、可恢复性和执行结果。

执行顺序：

1. 使用包管理器的官方清理命令处理明确可重建缓存。
2. 将用户拥有的应用和缓存移入带时间戳的废纸篓子目录。
3. 逐项验证来源路径已不存在、废纸篓目标存在，或包管理器缓存大小已变化。
4. 只有用户明确确认精确废纸篓目录后，才永久清空该目录。
5. Docker 按“容器和网络”“镜像和 Build Cache”“volume”三组独立执行和验证。

禁止：

- 对 `$HOME`、`~`、工作区根目录、未展开变量执行递归删除。
- 在同一条长脚本中混合废纸篓清空、多个应用删除和 Docker volume 删除。
- 因一次操作失败而继续执行后续不可恢复操作。

## Step 7：后置核验与闭环

每轮执行后使用同一命令复测：

```bash
df -h / /System/Volumes/Data
```

并核验：

```bash
[ -e '{SOURCE_PATH}' ] && echo PRESENT || echo ABSENT
[ -e '{TRASH_PATH}' ] && echo IN_TRASH || true
docker ps -a --format '{{.Names}}'
docker volume ls
docker network ls
```

报告真实文件系统变化，不以目录标称大小代替实际释放空间。APFS 统计可能延迟或受可清除空间影响，需如实说明。

当用户目标是解决卡顿时，还必须重新采样 CPU、内存和 swap，不能用“清出了多少空间”代替性能结论。
