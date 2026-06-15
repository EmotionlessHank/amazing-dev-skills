# /summary - Current Financial Snapshot

## Trigger

User types `/summary`

## Execution Steps

1. **Load All Context**
   - Read all YAML files under `context/`

2. **Output a One-Page Snapshot**
   Display a quick overview of the current financial picture — no deep analysis:

   ```
   ═══════════════════════════════════════════
     Household Financial Snapshot - YYYY-MM-DD
   ═══════════════════════════════════════════

   👤 Household: Hang & Yilin | Melbourne, VIC
   🏠 Address: South Yarra

   💰 Accounts
   ├ ANZ Joint:    $XX,XXX.XX
   └ Safety Floor: $X,XXX (currently [Safe / Warning])

   📤 Monthly Spending (estimated)
   ├ Rent:               $X,XXX
   ├ Living Expenses:    $X,XXX
   ├ Fixed Costs Total:  $X,XXX
   └ Total Monthly Avg:  $X,XXX

   🎯 Active Goals
   ├ [Priority] Goal Name - Amount - Deadline
   └ ...

   💱 Exchange Rates (updated YYYY-MM-DD)
   ├ USD → AUD: X.XX
   └ RMB → AUD: X.XX

   🏦 Overseas Reserves
   ├ Living Reserve:  ¥XXX,XXX (approx. $XX,XXX AUD)
   └ Available Runway: XX months
   ```

3. **Flag Stale Information**
   - If exchange rates have not been updated in over 30 days, prompt the user to refresh them
   - If any goal has passed its deadline, highlight it prominently
