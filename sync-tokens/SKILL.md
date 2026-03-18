---
name: sync-tokens
description: 同步 Figma Design Token。当用户说 "/sync-tokens"、"同步 token"、"更新 token"、"sync tokens" 时触发。接收 Figma 导出的 JSON 文件路径，自动复制到 tokens/figma/、运行 pnpm sync-tokens 生成 CSS 变量和 TS 常量、展示 diff。
version: 0.1.0
---

# Sync Figma Design Tokens

从 Figma 导出的 JSON 文件同步 Design Token 到项目代码。

---

## 触发条件

用户说出以下任意关键词：
- `/sync-tokens`
- `同步 token`、`更新 token`、`更新设计变量`
- `sync tokens`、`update tokens`

---

## 参数

用户在调用时需提供 Figma 导出的 JSON 文件路径，支持以下格式：

```
/sync-tokens /path/to/Dark.tokens.json /path/to/Light.tokens.json
/sync-tokens /path/to/Dark.tokens.json          # 只更新 Dark
/sync-tokens /path/to/Light.tokens.json         # 只更新 Light
```

文件名必须包含 `Dark` 或 `Light`（不区分大小写）来判断放入哪个位置。

---

## 无参数时的行为

如果用户调用时**没有提供任何 JSON 文件路径**，必须提醒：

> 请提供 Figma 导出的 JSON 文件路径，例如：
> ```
> /sync-tokens ~/Downloads/Dark.tokens.json ~/Downloads/Light.tokens.json
> ```
>
> **如何获取 JSON 文件：**
> 1. Figma → 右侧面板 → Local variables
> 2. 导出 → 选择 JSON 格式
> 3. 分别导出 Dark 和 Light 集合

提醒后**停止执行**，不要继续后续步骤。

---

## 执行步骤

### Step 1: 验证文件

- 确认提供的文件路径存在
- 通过文件名中的 `Dark` / `Light` 判断类型
- 如果文件名无法判断类型，询问用户

### Step 2: 复制 JSON 到项目

```bash
# 根据类型复制到对应位置
cp <dark-json-path>  tokens/figma/Dark.tokens.json
cp <light-json-path> tokens/figma/Light.tokens.json
```

### Step 3: 运行同步脚本

```bash
pnpm sync-tokens
```

此命令会自动生成：
- `app/design-tokens.css` — CSS 自定义变量（`:root` Dark + `[data-theme="light"]` Light）
- `lib/design-tokens.ts` — TypeScript 常量导出

### Step 4: 展示变更

```bash
git diff --stat
git diff app/design-tokens.css lib/design-tokens.ts
```

向用户展示：
- 变更了多少个 token
- 新增/删除/修改了哪些变量
- 如果 `tailwind.config.ts` 中有 `@deprecated` 的旧 token 需要清理，提醒用户

### Step 5: 确认提交

询问用户是否需要提交变更。如果确认，执行 commit（遵循项目 Git 规范）。

---

## 产物关系图

```
tokens/figma/Dark.tokens.json   ─┐
                                  ├─→ pnpm sync-tokens ─┬─→ app/design-tokens.css (CSS 变量)
tokens/figma/Light.tokens.json  ─┘                      ├─→ lib/design-tokens.ts  (TS 常量)
                                                         └─→ tailwind.config.ts 通过 var() 引用
```

---

## 注意事项

- `app/design-tokens.css` 和 `lib/design-tokens.ts` 是自动生成文件，**禁止手动编辑**
- `tailwind.config.ts` 已通过 `var()` 引用 CSS 变量，通常不需要手动改
- 如果 Figma 新增了全新的 token 类别（不在现有 `CATEGORY_PREFIX_MAP` 中），需要同时更新 `scripts/sync-tokens.ts` 的映射表
