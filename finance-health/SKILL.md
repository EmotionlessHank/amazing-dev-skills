# /health - Financial Health Check

## Trigger

User types `/health`

## Execution Steps

1. **Load All Context**
   - Read all 5 YAML files under `context/`

2. **Calculate Core Metrics**
   - Monthly income vs. monthly spending → net monthly cash flow
   - ANZ account current balance vs. safety threshold (`risk_thresholds` in `assumptions.yaml`)
   - Emergency reserve coverage (months) = current balance ÷ average monthly spending
   - Overseas reserve runway = overseas reserves ÷ monthly transfer amount

3. **Check Goals**
   - Iterate over all goals with `status: active` in `goals.yaml`
   - Verify each goal has sufficient funding
   - Flag any goal whose deadline falls within the next 30 days

4. **Check Risks**
   - Is the balance below `warning_balance`?
   - Is there an upward trend in monthly spending?
   - Are any fixed expenses missing (compare `fixed_expenses.yaml` against actual statements)?

5. **Output Health Report Card**
   Print in the following format:

   ```
   ═══════════════════════════════════
     Household Financial Health Report - YYYY-MM-DD
   ═══════════════════════════════════

   Overall Score: XX/100  [Healthy / Caution / Warning]

   ┌─ Cash Flow ──────────────────────
   │ Monthly Income:   $X,XXX
   │ Monthly Spending: $X,XXX
   │ Monthly Surplus:  $X,XXX (±XX%)
   └──────────────────────────────────

   ┌─ Safety Reserves ────────────────
   │ ANZ Balance:          $XX,XXX [Safe / Warning]
   │ Emergency Coverage:   X.X months
   │ Overseas Runway:      XX months
   └──────────────────────────────────

   ┌─ Goal Progress ──────────────────
   │ [Status] Goal Name - Progress detail
   │ ...
   └──────────────────────────────────

   ┌─ Recommendations ────────────────
   │ 1. Recommendation (estimated impact: $XXX/month)
   │ 2. ...
   └──────────────────────────────────
   ```
