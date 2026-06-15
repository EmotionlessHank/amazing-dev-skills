# /analyze - Analyze Bank Statements

## Trigger

User types `/analyze` or `/analyze <PDF path>`

## Execution Steps

1. **Locate the PDF File**
   - If the user provided a path, use that path
   - If no path was provided, check the `statements/` directory for the most recent PDF
   - If `statements/` is empty, prompt the user to supply a PDF

2. **Load Context**
   - Read all 5 YAML files under `context/` to get the latest household financial context

3. **Parse the Statement**
   - Extract every transaction from the PDF
   - Auto-categorize each transaction using the classification rules defined in CLAUDE.md
   - Group transactions by month

4. **Generate Analysis**
   - Summarize spending by category (amount and percentage)
   - If prior-period data exists (in `context/assumptions.yaml`), compute month-over-month comparisons
   - Flag anomalous transactions (single transaction > $200, or category spending up > 30% MoM)

5. **Generate Report**
   - Use Python (openpyxl) to produce an Excel report and save it to the appropriate subdirectory under `reports/`
   - Follow the report format conventions defined in CLAUDE.md

6. **Update Context**
   - Write actual `monthly_spending` figures back to `context/assumptions.yaml`

7. **Print Summary**
   - Output a plain-text summary of key findings to the terminal, including:
     - Total spending / total income / net cash flow for the period
     - Top 5 spending categories
     - Anomalous transaction alerts
     - Optimization suggestions with estimated monthly savings
