-- 08  Payments: failed card charges, involuntary churn, and cash collected vs MRR.
-- Involuntary churn = subscriptions ended because a payment could not be collected (end_reason
-- 'payment_failed'), as opposed to customers who cancelled.
-- Input:  invoices, subscriptions, kpi_monthly
-- Output: result_payments_monthly

CREATE OR REPLACE TABLE result_payments_monthly AS
WITH inv AS (
    SELECT CAST(date_trunc('month', invoice_date) AS DATE)                     AS month,
           COUNT(*)                                                             AS invoices,
           COUNT(*) FILTER (WHERE attempts > 1)                                 AS first_charge_failed,
           COUNT(*) FILTER (WHERE status = 'failed')                            AS never_collected,
           SUM(amount)                                                          AS invoiced
    FROM invoices
    GROUP BY 1
),
cash AS (
    SELECT CAST(date_trunc('month', paid_date) AS DATE) AS month, SUM(amount) AS collected
    FROM invoices WHERE status = 'paid' GROUP BY 1
),
ended AS (
    SELECT CAST(date_trunc('month', end_date) AS DATE)                          AS month,
           COUNT(*) FILTER (WHERE end_reason = 'payment_failed')                AS involuntary_churn_accounts,
           SUM(mrr) FILTER (WHERE end_reason = 'payment_failed')                AS involuntary_churn_mrr,
           COUNT(*) FILTER (WHERE end_reason = 'churn')                         AS voluntary_churn_accounts
    FROM subscriptions
    WHERE end_date IS NOT NULL
    GROUP BY 1
)
SELECT strftime(k.month, '%Y-%m')                                                AS month,
       i.invoices,
       i.first_charge_failed,
       ROUND(100.0 * i.first_charge_failed / i.invoices, 2)                      AS first_charge_failed_pct,
       ROUND(100.0 * (i.first_charge_failed - i.never_collected)
             / NULLIF(i.first_charge_failed, 0), 1)                              AS recovered_by_retry_pct,
       COALESCE(e.involuntary_churn_accounts, 0)                                 AS involuntary_churn_accounts,
       ROUND(COALESCE(e.involuntary_churn_mrr, 0), 2)                            AS involuntary_churn_mrr,
       COALESCE(e.voluntary_churn_accounts, 0)                                   AS voluntary_churn_accounts,
       ROUND(i.invoiced, 2)                                                      AS invoiced,
       ROUND(COALESCE(c.collected, 0), 2)                                        AS cash_collected,
       k.mrr                                                                     AS mrr_month_end
FROM kpi_monthly k
LEFT JOIN inv i USING (month)
LEFT JOIN cash c USING (month)
LEFT JOIN ended e USING (month)
WHERE k.segment = 'All'
ORDER BY k.month;
