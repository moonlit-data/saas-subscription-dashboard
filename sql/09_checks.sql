-- 09  Reconciliation checks on the metrics. The pipeline stops if any check fails.
-- Output: result_checks (source checks from step 01 + metric checks)

CREATE OR REPLACE TABLE result_checks AS
SELECT check_name, passed, detail FROM result_source_checks
UNION ALL
SELECT 'one row per account and month',
       COUNT(*) = COUNT(DISTINCT (account_id, month)), format('{} rows', COUNT(*))
FROM account_month
UNION ALL
SELECT 'no account has two live subscriptions at a month end',
       MAX(live_subscriptions) <= 1, format('max {}', MAX(live_subscriptions))
FROM account_month
UNION ALL
SELECT 'MRR bridge: start + movements = end, every month and segment',
       COUNT(*) FILTER (WHERE ABS(mrr_start + net_new_mrr - mrr) > 0.01) = 0,
       format('{} months off', COUNT(*) FILTER (WHERE ABS(mrr_start + net_new_mrr - mrr) > 0.01))
FROM kpi_monthly
UNION ALL
SELECT 'accounts: start + new + reactivated - churned = end',
       COUNT(*) FILTER (WHERE accounts_start + new_accounts + reactivated_accounts - churned_accounts
                              <> paying_accounts) = 0,
       format('{} months off', COUNT(*) FILTER (WHERE accounts_start + new_accounts + reactivated_accounts
                                                      - churned_accounts <> paying_accounts))
FROM kpi_monthly
UNION ALL
SELECT 'segments add up to the company total',
       COUNT(*) FILTER (WHERE ABS(seg_mrr - all_mrr) > 0.01 OR seg_accounts <> all_accounts) = 0,
       format('{} months off', COUNT(*) FILTER (WHERE ABS(seg_mrr - all_mrr) > 0.01 OR seg_accounts <> all_accounts))
FROM (
    SELECT month,
           SUM(mrr) FILTER (WHERE segment <> 'All')             AS seg_mrr,
           SUM(mrr) FILTER (WHERE segment = 'All')              AS all_mrr,
           SUM(paying_accounts) FILTER (WHERE segment <> 'All') AS seg_accounts,
           SUM(paying_accounts) FILTER (WHERE segment = 'All')  AS all_accounts
    FROM kpi_monthly GROUP BY month
)
UNION ALL
SELECT 'every cohort starts at 100% logo retention',
       COUNT(*) FILTER (WHERE logo_retention_pct <> 100) = 0, format('{} cohorts', COUNT(*))
FROM result_cohort_retention WHERE months_since_signup = 0 AND segment = 'All'
UNION ALL
SELECT 'retention is never above 100% of accounts and GRR never above NRR',
       COUNT(*) FILTER (WHERE logo_retention_t12m_pct > 100 OR grr_t12m_pct > nrr_t12m_pct OR grr_t12m_pct > 100) = 0,
       format('{} rows', COUNT(*))
FROM retention_t12m
UNION ALL
SELECT 'month-end MRR matches the subscriptions table directly (December 2025)',
       ABS((SELECT mrr FROM kpi_monthly WHERE segment = 'All' AND month = DATE '2025-12-01')
           - (SELECT SUM(mrr) FROM subscriptions WHERE start_date <= DATE '2025-12-31'
                                                  AND (end_date IS NULL OR end_date > DATE '2025-12-31'))) < 0.01,
       format('{:.2f}', (SELECT mrr FROM kpi_monthly WHERE segment = 'All' AND month = DATE '2025-12-01'));
