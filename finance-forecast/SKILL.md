# /forecast - Cash Flow Forecast

## Trigger

User types `/forecast` or `/forecast <months>`

## Execution Steps

1. **Load Context**
   - Read all YAML files under `context/`
   - Focus on: `assumptions.yaml` (monthly spending baseline, exchange rates), `income.yaml` (income), `goals.yaml` (upcoming goal payments), `fixed_expenses.yaml` (fixed costs)

2. **Build the Forecast Model**
   - Default forecast horizon: 6 months (user may specify a different number)
   - Baseline monthly spending = `total_with_rent` from `assumptions.yaml → monthly_spending`
   - Monthly income = aggregated income from `income.yaml` plus planned transfer amounts
   - Apply inflation: compound monthly using the `inflation` parameter
   - Deduct one-time goal payments (e.g., PR application fees) in their respective projected months

3. **Identify Key Milestones**
   - When does the ANZ balance first hit `warning_balance`?
   - When do overseas reserves run out?
   - When does net cash flow turn positive or negative?

4. **Output Forecast Table**
   ```
   ═══════════════════════════════════════════════
     Cash Flow Forecast - Next 6 Months
   ═══════════════════════════════════════════════

   Month     Income    Spending  Net Flow  ANZ Balance  Overseas Reserves
   ─────────────────────────────────────────────────────────────────────
   2026-04   $X,XXX   $X,XXX   +$XXX    $XX,XXX      ¥XXX,XXX
   2026-05   ...
   ...

   ⚠️ Risk Alerts:
   • [List any identified risk milestones here]

   💡 Recommendations:
   • [Action items based on the forecast]
   ```
