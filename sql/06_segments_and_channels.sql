-- 06  Where does the business stand at the end of 2025, by segment, channel and billing period?
-- Input:  account_month, mrr_movements, retention_t12m
-- Output: result_segment_summary, result_channel_summary, result_billing_summary,
--         result_channel_retention_2024 (12-month retention of accounts that signed up in 2024)

-- summary_by('segment' | 'channel' | 'billing'): one table macro instead of three copies of the query
CREATE OR REPLACE MACRO summary_by(dim) AS TABLE
WITH latest AS (
    SELECT CASE dim WHEN 'segment' THEN segment WHEN 'channel' THEN channel ELSE billing_period END AS grp,
           mrr
    FROM account_month
    WHERE month = DATE '2025-12-01' AND mrr > 0
),
churn_2025 AS (   -- monthly logo churn in 2025, pooled over the twelve months
    SELECT CASE dim WHEN 'segment' THEN segment WHEN 'channel' THEN channel ELSE prev_billing END AS grp,
           ROUND(100.0 * COUNT(*) FILTER (WHERE movement = 'churn')
                 / COUNT(*) FILTER (WHERE prev_mrr > 0), 2)                                      AS avg_monthly_logo_churn_2025_pct
    FROM mrr_movements
    WHERE month BETWEEN DATE '2025-01-01' AND DATE '2025-12-01' AND prev_mrr > 0
    GROUP BY 1
)
SELECT l.grp,
       COUNT(*)                                                AS paying_accounts,
       ROUND(SUM(l.mrr), 2)                                    AS mrr,
       ROUND(100 * SUM(l.mrr) / SUM(SUM(l.mrr)) OVER (), 1)    AS share_of_mrr_pct,
       ROUND(SUM(l.mrr) / COUNT(*), 2)                         AS arppu,
       ANY_VALUE(c.avg_monthly_logo_churn_2025_pct)            AS avg_monthly_logo_churn_2025_pct
FROM latest l
LEFT JOIN churn_2025 c USING (grp)
GROUP BY l.grp
ORDER BY mrr DESC;

CREATE OR REPLACE TABLE result_segment_summary AS
SELECT s.grp AS segment, s.* EXCLUDE (grp), r.nrr_t12m_pct, r.grr_t12m_pct
FROM summary_by('segment') s
LEFT JOIN retention_t12m r ON r.segment = s.grp AND r.month = DATE '2025-12-01'
ORDER BY s.mrr DESC;

CREATE OR REPLACE TABLE result_channel_summary AS
SELECT grp AS channel, * EXCLUDE (grp) FROM summary_by('channel') ORDER BY mrr DESC;

CREATE OR REPLACE TABLE result_billing_summary AS
SELECT grp AS billing_period, * EXCLUDE (grp) FROM summary_by('billing') ORDER BY mrr DESC;

-- Same-age comparison: accounts that signed up in 2024, still paying 12 months after their signup month
CREATE OR REPLACE TABLE result_channel_retention_2024 AS
SELECT a0.channel,
       COALESCE(a0.segment, 'All')                                             AS segment,
       COUNT(*)                                                                AS accounts,
       ROUND(100.0 * COUNT(*) FILTER (WHERE a12.mrr > 0) / COUNT(*), 1)       AS still_paying_after_12m_pct,
       ROUND(100.0 * SUM(a12.mrr) / SUM(a0.mrr), 1)                            AS revenue_retention_12m_pct
FROM account_month a0
JOIN account_month a12
  ON a12.account_id = a0.account_id AND a12.month = a0.month + INTERVAL 12 MONTH
WHERE a0.month = a0.signup_month
  AND a0.signup_month BETWEEN DATE '2024-01-01' AND DATE '2024-12-01'
GROUP BY GROUPING SETS ((a0.channel), (a0.channel, a0.segment))
ORDER BY a0.channel, a0.segment NULLS FIRST;
