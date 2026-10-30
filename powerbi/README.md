# Power BI model

The interactive dashboard in `docs/index.html` is built with Python. This folder holds the same data as a
star schema for Power BI Desktop (the `.pbix` report is not in the repository yet).

| File | Rows | Grain |
|---|---:|---|
| `fact_account_month.csv` | one per account per month since signup | month-end MRR, previous MRR, change, movement, MRR 12 months earlier |
| `dim_account.csv` | one per account | segment, channel, region, industry, signup date |
| `dim_date.csv` | one per day, 2023-2025 | year, month |
| `measures.dax` | | MRR, ARR, paying accounts, ARPPU, MRR movements, logo churn, NRR and GRR (12 months) |

Build steps:

1. Get Data -> Text/CSV: load the three CSV files.
2. Model view: relate `fact_account_month[month]` to `dim_date[date]` and `fact_account_month[account_id]`
   to `dim_account[account_id]` (both many-to-one, single direction). Mark `dim_date` as the date table.
3. Create the measures in `measures.dax`.
4. Check the totals against `results/kpi_monthly.csv` before building visuals (December 2025, all
   segments: MRR 475,967.25; 2,212 paying accounts; logo churn 2.82%; NRR 12m 98.6%).

Recreate the CSV files with `python src/export_powerbi.py`.
