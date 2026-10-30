-- 05  Cohort retention: accounts grouped by the quarter they signed up (all accounts and per segment).
-- Logo retention    = share of the cohort still paying k months after the signup month.
-- Revenue retention = cohort MRR k months after signup / cohort MRR in the signup month.
-- A cohort spans three signup months, so month k is shown only once every account in it has reached k.
-- Input:  account_month
-- Output: result_cohort_retention (long format: segment x cohort x months_since_signup)

CREATE OR REPLACE TABLE result_cohort_retention AS
WITH a AS (
    SELECT account_id,
           segment,
           strftime(signup_month, '%Y') || '-Q' || CAST(quarter(signup_month) AS VARCHAR)  AS cohort,
           date_diff('month', signup_month, month)                                         AS months_since_signup,
           mrr,
           FIRST_VALUE(mrr) OVER (PARTITION BY account_id ORDER BY month)                  AS first_mrr
    FROM account_month
),
both_views AS (                      -- every row twice: once for 'All', once for its own segment
    SELECT 'All' AS view_segment, * FROM a
    UNION ALL
    SELECT segment, * FROM a
),
sizes AS (
    SELECT view_segment, cohort,
           COUNT(DISTINCT account_id)                                   AS cohort_accounts,
           SUM(first_mrr) FILTER (WHERE months_since_signup = 0)        AS cohort_mrr
    FROM both_views
    GROUP BY view_segment, cohort
)
SELECT b.view_segment                                                       AS segment,
       b.cohort,
       b.months_since_signup,
       s.cohort_accounts,
       ROUND(100.0 * COUNT(*) FILTER (WHERE b.mrr > 0) / s.cohort_accounts, 1) AS logo_retention_pct,
       ROUND(100.0 * SUM(b.mrr) / s.cohort_mrr, 1)                             AS revenue_retention_pct
FROM both_views b
JOIN sizes s USING (view_segment, cohort)
GROUP BY b.view_segment, b.cohort, b.months_since_signup, s.cohort_accounts, s.cohort_mrr
HAVING COUNT(DISTINCT b.account_id) = s.cohort_accounts
ORDER BY CASE b.view_segment WHEN 'All' THEN 0 WHEN 'SMB' THEN 1 WHEN 'Mid-Market' THEN 2 ELSE 3 END,
         b.cohort, b.months_since_signup;
