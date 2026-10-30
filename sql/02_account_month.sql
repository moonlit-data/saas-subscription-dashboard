-- 02  Month-end MRR for every account and month.
-- A subscription row is live from start_date (inclusive) to end_date (exclusive). MRR is measured on the
-- last day of each month, so a customer who cancels on the 31st is already gone at month end.
-- Input:  accounts, subscriptions
-- Output: months, account_month (one row per account per month from its signup month)

CREATE OR REPLACE TABLE months AS
SELECT CAST(m AS DATE)                                       AS month,
       CAST(m + INTERVAL 1 MONTH - INTERVAL 1 DAY AS DATE)   AS month_end
FROM generate_series(DATE '2023-01-01', DATE '2025-12-01', INTERVAL 1 MONTH) AS t(m);

CREATE OR REPLACE TABLE account_month AS
SELECT a.account_id,
       a.segment,
       a.channel,
       a.region,
       CAST(date_trunc('month', a.signup_date) AS DATE)   AS signup_month,
       m.month,
       COALESCE(SUM(s.mrr), 0)                            AS mrr,
       ANY_VALUE(s.plan)                                  AS plan,
       ANY_VALUE(s.billing_period)                        AS billing_period,
       COUNT(s.subscription_id)                           AS live_subscriptions
FROM accounts a
JOIN months m
  ON m.month >= date_trunc('month', a.signup_date)
LEFT JOIN subscriptions s
  ON s.account_id = a.account_id
 AND s.start_date <= m.month_end
 AND (s.end_date IS NULL OR s.end_date > m.month_end)
GROUP BY ALL;
