# /update - 更新财务信息

## 触发方式
用户输入 `/update` 或 `/update <具体内容>`

## 执行步骤

1. **判断更新类型**
   根据用户输入自动判断需要修改哪个 YAML 文件：

   | 用户说的 | 对应文件 | 操作 |
   |---------|---------|------|
   | 收入/工资/涨薪 | `context/income.yaml` | 更新收入数据 |
   | 租金/房租 | `context/fixed_expenses.yaml` | 更新租金 |
   | 订阅/Netflix/取消 | `context/fixed_expenses.yaml` | 新增或标记取消 |
   | 目标/PR/完成/取消 | `context/goals.yaml` | 更新目标状态 |
   | 汇率/通胀 | `context/assumptions.yaml` | 更新假设参数 |
   | 搬家/签证/地址 | `context/profile.yaml` | 更新家庭信息 |

2. **如果用户没有提供具体内容**
   展示交互式菜单：
   ```
   请选择要更新的信息：
   1. 收入变动（工资、新增收入）
   2. 固定支出（租金、订阅、保险）
   3. 目标状态（完成、取消、新增）
   4. 汇率 & 假设参数
   5. 家庭基本信息
   ```

3. **执行更新**
   - 读取对应 YAML 文件
   - 根据用户指示修改
   - 如果是目标完成：`status` → `completed`，填入 `completed_date`
   - 如果是目标取消：`status` → `cancelled`，填入取消原因
   - 直接写入文件，不需要额外确认

4. **输出确认**
   ```
   ✅ 已更新 context/xxx.yaml
   变更：[具体变更内容]
   ```
