-- 07  Did the July 2024 Starter price increase ($12 -> $15 per seat) pay off?
-- Monthly-billed Starter accounts were repriced on 1 July 2024. Compare their monthly logo churn with
-- the six months before, and with monthly-billed Growth accounts over the same months (not repriced).
-- Input:  mrr_movements
-- Output: result_price_churn_by_month, result_price_increase_effect

CREATE OR REPLACE TABLE price_cohort AS
SELECT month,
       prev_plan                                                  AS plan,
       COUNT(*) FILTER (WHERE prev_mrr > 0)                       AS paying_at_start,
       COUNT(*) FILTER (WHERE movement = 'churn')                 AS churned,
       SUM(-mrr_change) FILTER (WHERE movement = 'churn')         AS churned_mrr,
       SUM(mrr_change) FILTER (WHERE movement = 'expansion' AND plan = 'Starter' AND prev_plan = 'Starter')
                                                                  AS starter_expansion_mrr
FROM mrr_movements
WHERE prev_billing = 'monthly'
  AND prev_plan IN ('Starter', 'Growth')
  AND month BETWEEN DATE '2024-01-01' AND DATE '2024-12-01'
GROUP BY month, prev_plan;

CREATE OR REPLACE TABLE result_price_churn_by_month AS
SELECT strftime(month, '%Y-%m')                                   AS month,
       plan,
       paying_at_start,
       churned,
       ROUND(100.0 * churned / paying_at_start, 2)                AS logo_churn_pct
FROM price_cohort
ORDER BY plan DESC, month;

-- Excess churn = actual churn Jul-Sep minus what the Jan-Jun rate would have produced
CREATE OR REPLACE TABLE result_price_increase_effect AS
WITH base AS (
    SELECT plan, SUM(churned) * 1.0 / SUM(paying_at_start) AS rate_before
    FROM price_cohort WHERE month < DATE '2024-07-01' GROUP BY plan
),
after AS (
    SELECT p.plan,
           SUM(p.churned)                                        AS churned_jul_sep,
           SUM(p.paying_at_start * b.rate_before)                AS expected_jul_sep,
           SUM(p.churned_mrr) / SUM(p.churned)                   AS avg_mrr_of_churned
    FROM price_cohort p JOIN base b USING (plan)
    WHERE p.month BETWEEN DATE '2024-07-01' AND DATE '2024-09-01'
    GROUP BY p.plan
),
uplift AS (
    SELECT SUM(starter_expansion_mrr) AS repricing_mrr
    FROM price_cohort WHERE month = DATE '2024-07-01' AND plan = 'Starter'
)
SELECT a.plan,
       ROUND(100 * b.rate_before, 2)                                          AS churn_rate_jan_jun_pct,
       a.churned_jul_sep,
       ROUND(a.expected_jul_sep, 1)                                           AS expected_at_old_rate,
       ROUND(a.churned_jul_sep - a.expected_jul_sep, 1)                       AS excess_churned_accounts,
       ROUND((a.churned_jul_sep - a.expected_jul_sep) * a.avg_mrr_of_churned, 2) AS excess_churned_mrr,
       CASE WHEN a.plan = 'Starter' THEN ROUND(u.repricing_mrr, 2) END        AS mrr_gained_by_repricing_jul,
       CASE WHEN a.plan = 'Starter'
            THEN ROUND(u.repricing_mrr - (a.churned_jul_sep - a.expected_jul_sep) * a.avg_mrr_of_churned, 2)
       END                                                                    AS net_mrr_effect
FROM after a
JOIN base b USING (plan)
CROSS JOIN uplift u
ORDER BY a.plan DESC;
