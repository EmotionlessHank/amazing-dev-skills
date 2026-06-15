# /update - Update Financial Information

## Trigger

User types `/update` or `/update <specific content>`

## Execution Steps

1. **Determine Update Type**
   Automatically infer which YAML file to modify based on user input:

   | User Says | Target File | Action |
   |-----------|-------------|--------|
   | income / salary / pay rise | `context/income.yaml` | Update income data |
   | rent / housing | `context/fixed_expenses.yaml` | Update rent amount |
   | subscription / Netflix / cancel | `context/fixed_expenses.yaml` | Add or mark as cancelled |
   | goal / PR / completed / cancelled | `context/goals.yaml` | Update goal status |
   | exchange rate / inflation | `context/assumptions.yaml` | Update assumption parameters |
   | moving / visa / address | `context/profile.yaml` | Update household profile |

2. **If the User Provides No Specific Content**
   Display an interactive menu:
   ```
   What would you like to update?
   1. Income changes (salary, new income source)
   2. Fixed expenses (rent, subscriptions, insurance)
   3. Goal status (completed, cancelled, new goal)
   4. Exchange rates & assumption parameters
   5. Household profile information
   ```

3. **Apply the Update**
   - Read the relevant YAML file
   - Apply the changes as directed by the user
   - For a completed goal: set `status` → `completed` and fill in `completed_date`
   - For a cancelled goal: set `status` → `cancelled` and record the cancellation reason
   - Write changes directly to the file — no additional confirmation required

4. **Confirm the Update**
   ```
   ✅ Updated context/xxx.yaml
   Changes: [description of what changed]
   ```
