# /analyze - 分析银行账单

## 触发方式
用户输入 `/analyze` 或 `/analyze <PDF路径>`

## 执行步骤

1. **确认 PDF 文件**
   - 如果用户提供了路径，使用该路径
   - 如果没有提供路径，检查 `statements/` 目录下最新的 PDF 文件
   - 如果 `statements/` 为空，提示用户提供 PDF

2. **读取上下文**
   - 读取 `context/` 下所有 5 个 YAML 文件，获取最新的家庭财务上下文

3. **解析账单**
   - 读取 PDF 中的每笔交易
   - 按 CLAUDE.md 中的交易分类规则进行自动分类
   - 按月份分组

4. **生成分析**
   - 按分类汇总支出金额和占比
   - 如果有上期数据（在 `context/assumptions.yaml` 中），进行环比对比
   - 标出异常交易（单笔 > $200 或同类别环比增长 > 30%）

5. **生成报告**
   - 使用 Python (openpyxl) 生成 Excel 报告，存入 `reports/` 对应目录
   - 报告格式遵循 CLAUDE.md 中的报告生成规范

6. **更新上下文**
   - 更新 `context/assumptions.yaml` 中的 `monthly_spending` 实际数据

7. **输出摘要**
   - 在终端输出关键发现的文字摘要，包括：
     - 本期总支出 / 总收入 / 净现金流
     - 各分类支出 TOP 5
     - 异常交易提醒
     - 优化建议（附预计节省金额）
