-- 04  Monthly KPIs, for the whole company and for each segment (GROUPING SETS; segment 'All' = total).
-- Definitions are in docs/metric_definitions.md.
-- Input:  mrr_movements, account_month
-- Output: kpi_monthly, result_kpi_monthly, result_retention_t12m

CREATE OR REPLACE TABLE kpi_base AS
SELECT COALESCE(segment, 'All')                                                  AS segment,
       month,
       SUM(mrr)                                                                  AS mrr,
       COUNT(*) FILTER (WHERE mrr > 0)                                           AS paying_accounts,
       SUM(mrr_change) FILTER (WHERE movement = 'new')                           AS new_mrr,
       SUM(mrr_change) FILTER (WHERE movement = 'expansion')                     AS expansion_mrr,
       SUM(mrr_change) FILTER (WHERE movement = 'reactivation')                  AS reactivation_mrr,
       SUM(mrr_change) FILTER (WHERE movement = 'contraction')                   AS contraction_mrr,
       SUM(mrr_change) FILTER (WHERE movement = 'churn')                         AS churned_mrr,
       COUNT(*) FILTER (WHERE movement = 'new')                                  AS new_accounts,
       COUNT(*) FILTER (WHERE movement = 'reactivation')                         AS reactivated_accounts,
       COUNT(*) FILTER (WHERE movement = 'churn')                                AS churned_accounts
FROM mrr_movements
GROUP BY GROUPING SETS ((month), (segment, month));

CREATE OR REPLACE TABLE kpi_monthly AS
SELECT segment,
       month,
       ROUND(mrr, 2)                                                               AS mrr,
       ROUND(12 * mrr, 2)                                                          AS arr,
       paying_accounts,
       ROUND(mrr / NULLIF(paying_accounts, 0), 2)                                  AS arppu,
       ROUND(COALESCE(LAG(mrr) OVER w, 0), 2)                                      AS mrr_start,
       COALESCE(LAG(paying_accounts) OVER w, 0)                                    AS accounts_start,
       ROUND(COALESCE(new_mrr, 0), 2)                                              AS new_mrr,
       ROUND(COALESCE(expansion_mrr, 0), 2)                                        AS expansion_mrr,
       ROUND(COALESCE(reactivation_mrr, 0), 2)                                     AS reactivation_mrr,
       ROUND(COALESCE(contraction_mrr, 0), 2)                                      AS contraction_mrr,
       ROUND(COALESCE(churned_mrr, 0), 2)                                          AS churned_mrr,
       ROUND(COALESCE(new_mrr, 0) + COALESCE(expansion_mrr, 0) + COALESCE(reactivation_mrr, 0)
             + COALESCE(contraction_mrr, 0) + COALESCE(churned_mrr, 0), 2)         AS net_new_mrr,
       new_accounts, reactivated_accounts, churned_accounts,
       ROUND(100.0 * churned_accounts / NULLIF(LAG(paying_accounts) OVER w, 0), 2) AS logo_churn_pct,
       ROUND(-100.0 * (COALESCE(churned_mrr, 0) + COALESCE(contraction_mrr, 0))
             / NULLIF(LAG(mrr) OVER w, 0), 2)                                      AS gross_mrr_churn_pct,
       ROUND(100.0 * (LAG(mrr) OVER w + COALESCE(expansion_mrr, 0) + COALESCE(contraction_mrr, 0)
                      + COALESCE(churned_mrr, 0)) / NULLIF(LAG(mrr) OVER w, 0), 2) AS nrr_month_pct,
       ROUND((COALESCE(new_mrr, 0) + COALESCE(expansion_mrr, 0) + COALESCE(reactivation_mrr, 0))
             / NULLIF(-(COALESCE(contraction_mrr, 0) + COALESCE(churned_mrr, 0)), 0), 2) AS quick_ratio
FROM kpi_base
WINDOW w AS (PARTITION BY segment ORDER BY month)
ORDER BY segment, month;

-- Trailing-twelve-month retention: of the MRR accounts paid twelve months ago, how much do the same
-- accounts pay now? NRR counts their expansion; GRR caps each account at its old MRR (losses only).
CREATE OR REPLACE TABLE retention_t12m AS
SELECT COALESCE(prv.segment, 'All')                                                   AS segment,
       cur.month,
       ROUND(100 * SUM(cur.mrr) / SUM(prv.mrr), 1)                                    AS nrr_t12m_pct,
       ROUND(100 * SUM(LEAST(cur.mrr, prv.mrr)) / SUM(prv.mrr), 1)                    AS grr_t12m_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE cur.mrr > 0) / COUNT(*), 1)               AS logo_retention_t12m_pct,
       COUNT(*)                                                                       AS accounts_12m_ago
FROM account_month prv
JOIN account_month cur
  ON cur.account_id = prv.account_id
 AND cur.month = prv.month + INTERVAL 12 MONTH
WHERE prv.mrr > 0
GROUP BY GROUPING SETS ((cur.month), (prv.segment, cur.month));

CREATE OR REPLACE TABLE result_kpi_monthly AS
SELECT k.segment, strftime(k.month, '%Y-%m') AS month, k.* EXCLUDE (segment, month),
       r.nrr_t12m_pct, r.grr_t12m_pct, r.logo_retention_t12m_pct
FROM kpi_monthly k
LEFT JOIN retention_t12m r USING (segment, month)
ORDER BY CASE k.segment WHEN 'All' THEN 0 WHEN 'SMB' THEN 1 WHEN 'Mid-Market' THEN 2 ELSE 3 END, k.month;
