# Metric definitions

| Metric | Definition |
|---|---|
| **MRR** (monthly recurring revenue) | Sum of the monthly price of every live subscription on the last day of the month. Annual plans count as 1/12 of the annual price. One-off and prorated invoices are not MRR. |
| **ARR** | MRR x 12 |
| **Paying accounts** | Accounts with MRR > 0 at month end |
| **ARPPU** (average revenue per paying account) | MRR / paying accounts |
| **New MRR** | MRR of accounts paying for the first time this month |
| **Expansion MRR** | Increase in MRR of accounts that paid last month and pay more now (seats, plan, price) |
| **Contraction MRR** | Decrease in MRR of accounts that still pay but pay less |
| **Churned MRR** | Last month's MRR of accounts that stopped paying |
| **Reactivation MRR** | MRR of accounts that pay again after at least one month at zero |
| **Net new MRR** | New + expansion + reactivation - contraction - churned = MRR this month - MRR last month (checked every month) |
| **Logo churn rate** | Accounts that stopped paying this month / paying accounts at the start of the month |
| **Gross MRR churn rate** | (Churned + contraction MRR) / MRR at the start of the month |
| **Quick ratio** | (New + expansion + reactivation) / (churned + contraction) |
| **Net revenue retention, 12 months (NRR)** | MRR now from the accounts that paid 12 months ago / their MRR 12 months ago. Includes their expansion; excludes new accounts. |
| **Gross revenue retention, 12 months (GRR)** | Same, but each account counts at most its old MRR, so only losses show |
| **Cohort logo retention** | Share of accounts that signed up in a quarter that still pay k months after their signup month |
| **Involuntary churn** | Subscriptions ended because a payment could not be collected (`end_reason = 'payment_failed'`) |

Notes

- A subscription row is live from `start_date` (inclusive) to `end_date` (exclusive). MRR is measured at
  month end, so a change during a month shows in that month; two changes in one month net out.
- A price increase shows up as expansion MRR. July 2024's expansion spike is the Starter repricing, not
  customers buying more.
- Segment results add up to the company totals every month (checked in `sql/09_checks.sql`).
