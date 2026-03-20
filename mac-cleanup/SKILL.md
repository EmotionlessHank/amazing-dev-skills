---
name: mac-cleanup
description: macOS 系统清理审计。当用户说 "/mac-cleanup"、"清理电脑"、"系统清理"、"磁盘清理"、"清理软件" 时触发。自动扫描 Applications、Homebrew、npm、pip、系统缓存等，输出结构化清理建议报告，等用户确认后执行删除操作。
version: 1.0.0
---

# /mac-cleanup — macOS 系统清理审计

自动扫描本机已安装应用、包管理器、系统缓存，输出结构化清理建议，用户确认后执行清理。

---

## 触发条件

用户说出以下任意关键词：
- `/mac-cleanup`
- `清理电脑`、`系统清理`、`磁盘清理`、`清理软件`
- `mac cleanup`、`disk cleanup`

---

## 执行步骤

### Step 1：扫描已安装应用（/Applications）

查找超过 1 个月未打开的应用，以及占用空间较大的应用：

```bash
# 获取所有 app 的名称、最后使用日期、物理大小
find /Applications -maxdepth 2 -name "*.app" -exec mdls -name kMDItemLastUsedDate -name kMDItemDisplayName -name kMDItemPhysicalSize {} \; 2>/dev/null | paste - - - | sort

# 获取所有 app 按磁盘占用排序
find /Applications -maxdepth 2 -name "*.app" -exec du -sm {} + 2>/dev/null | sort -rn
```

分析维度：
- **超过 1 个月未打开**的应用（根据 kMDItemLastUsedDate 判断）
- **从未记录使用时间**的应用（kMDItemLastUsedDate 为 null）
- **占用空间大但使用频率低**的应用

### Step 2：扫描 Homebrew

```bash
# 已安装 formula 和 cask
brew list --formula
brew list --cask

# 孤立依赖检查
brew autoremove --dry-run

# 旧版本和缓存
brew cleanup --dry-run

# 缓存大小
du -sh $(brew --cache)

# 最大的 formula 安装
du -sh /opt/homebrew/Cellar/* 2>/dev/null | sort -rh | head -15
```

### Step 3：扫描 npm

```bash
# 全局包
npm list -g --depth=0

# 全局包占用空间
du -sh $(npm root -g)

# npm 缓存大小
du -sh ~/.npm
```

### Step 4：扫描 pip

```bash
# 已安装包
python3 -m pip list

# pip 缓存大小
du -sh ~/Library/Caches/pip
```

### Step 5：扫描系统缓存和其他

```bash
# ~/Library/Caches 各目录占用（Top 15）
du -sh ~/Library/Caches/* 2>/dev/null | sort -rh | head -15

# ~/.cache 大小
du -sh ~/.cache

# Xcode DerivedData 和 Archives
du -sh ~/Library/Developer/Xcode/DerivedData ~/Library/Developer/Xcode/Archives 2>/dev/null

# Docker（如果已安装）
which docker &>/dev/null && docker system df 2>/dev/null || echo "Docker 未安装"

# pnpm store
pnpm store status 2>/dev/null; du -sh ~/Library/Caches/pnpm 2>/dev/null

# yarn 全局包
which yarn &>/dev/null && yarn global list 2>/dev/null
```

### Step 6：输出清理报告

将以上数据整理为结构化中文报告，格式如下：

---

#### 报告模板

```
# macOS 系统清理报告（{日期}）

## 1. 应用程序（/Applications）

### 超过 1 个月未打开
| 应用 | 上次使用 | 占用空间 | 建议 |
|------|----------|----------|------|

### 从未记录使用时间
| 应用 | 占用空间 | 建议 |
|------|----------|------|

### 其他值得关注
| 应用 | 上次使用 | 占用空间 | 理由 |
|------|----------|----------|------|

## 2. Homebrew
| 项目 | 可回收空间 | 清理命令 |
|------|-----------|---------|

### 值得关注的大包
| 包 | 大小 | 建议 |
|---|------|------|

## 3. npm
| 项目 | 大小 | 说明 |
|------|------|------|

## 4. pip
| 包 | 说明 |
|---|------|

## 5. 系统缓存（~/Library/Caches）
| 缓存目录 | 大小 | 建议 |
|----------|------|------|

## 6. 其他（Xcode / Docker / pnpm 等）
| 项目 | 大小 | 清理命令 |
|------|------|---------|

## 汇总
| 类别 | 预估可回收 | 风险等级 |
|------|-----------|---------|

### 一键安全清理命令（低风险项）
（列出所有无风险的清理命令）
```

---

### Step 7：等待用户确认

输出报告后，**不要自动执行任何清理操作**。等待用户回复指定需要清理的项目，然后逐一执行。

执行删除时注意：
- `/Applications` 下的 app：先尝试 `rm -rf`，如遇权限问题（Mac App Store 安装的应用），提示用户手动在 Launchpad 长按删除
- Homebrew 包：使用 `brew uninstall <package>` 或 `brew cleanup`
- npm 全局包：使用 `npm uninstall -g <package>`
- 缓存目录：使用 `rm -rf <path>`
- pip 包：使用 `pip3 uninstall <package>`

---

## 注意事项

- 所有扫描步骤尽量**并行执行**以提高效率
- 报告中标注每项清理的**风险等级**（无风险 / 低风险 / 需确认）
- **绝不自动执行删除**，必须等用户明确指示
- 对于无法判断用途的应用或包，标记为"需确认"而非建议删除
