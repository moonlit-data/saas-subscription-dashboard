-- 03  Classify every account-month change in MRR (the "MRR bridge").
--   new           first month with MRR
--   reactivation  MRR again after a month at zero
--   expansion     MRR went up (more seats, a bigger plan, a price increase)
--   contraction   MRR went down but stayed above zero
--   churn         MRR went to zero
-- Input:  account_month
-- Output: mrr_movements

CREATE OR REPLACE TABLE mrr_movements AS
WITH x AS (
    SELECT *,
           COALESCE(LAG(mrr) OVER w, 0)                                        AS prev_mrr,
           COALESCE(MAX(CASE WHEN mrr > 0 THEN 1 ELSE 0 END)
                    OVER (PARTITION BY account_id ORDER BY month
                          ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0) AS was_paying_before,
           LAG(plan) OVER w                                                    AS prev_plan,
           LAG(billing_period) OVER w                                          AS prev_billing
    FROM account_month
    WINDOW w AS (PARTITION BY account_id ORDER BY month)
)
SELECT *,
       mrr - prev_mrr AS mrr_change,
       CASE WHEN prev_mrr = 0 AND mrr > 0 AND was_paying_before = 0 THEN 'new'
            WHEN prev_mrr = 0 AND mrr > 0                            THEN 'reactivation'
            WHEN prev_mrr > 0 AND mrr = 0                            THEN 'churn'
            WHEN mrr > prev_mrr                                      THEN 'expansion'
            WHEN mrr < prev_mrr                                      THEN 'contraction'
            ELSE 'none' END AS movement
FROM x;
