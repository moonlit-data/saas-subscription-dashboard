-- 01  Check the source tables before using them.
-- Input:  accounts, plans, subscriptions, invoices (loaded by src/run_pipeline.py with explicit types)
-- Output: result_source_checks

CREATE OR REPLACE TABLE result_source_checks AS
WITH sub_order AS (
    SELECT account_id, subscription_id, start_date, end_date,
           LEAD(start_date) OVER (PARTITION BY account_id ORDER BY start_date, subscription_id) AS next_start
    FROM subscriptions
)
SELECT 'account_id is unique' AS check_name,
       (SELECT COUNT(*) = COUNT(DISTINCT account_id) FROM accounts) AS passed,
       (SELECT format('{} rows', COUNT(*)) FROM accounts) AS detail
UNION ALL
SELECT 'subscription_id is unique',
       (SELECT COUNT(*) = COUNT(DISTINCT subscription_id) FROM subscriptions),
       (SELECT format('{} rows', COUNT(*)) FROM subscriptions)
UNION ALL
SELECT 'invoice_id is unique',
       (SELECT COUNT(*) = COUNT(DISTINCT invoice_id) FROM invoices),
       (SELECT format('{} rows', COUNT(*)) FROM invoices)
UNION ALL
SELECT 'every subscription belongs to a known account',
       (SELECT COUNT(*) = 0 FROM subscriptions s ANTI JOIN accounts a USING (account_id)),
       (SELECT format('{} orphans', COUNT(*)) FROM subscriptions s ANTI JOIN accounts a USING (account_id))
UNION ALL
SELECT 'every invoice belongs to a known subscription of the same account',
       (SELECT COUNT(*) = 0 FROM invoices i LEFT JOIN subscriptions s USING (subscription_id)
        WHERE s.subscription_id IS NULL OR s.account_id <> i.account_id),
       (SELECT format('{} bad', COUNT(*)) FROM invoices i LEFT JOIN subscriptions s USING (subscription_id)
        WHERE s.subscription_id IS NULL OR s.account_id <> i.account_id)
UNION ALL
SELECT 'subscription periods are valid (end after start)',
       (SELECT COUNT(*) = 0 FROM subscriptions WHERE end_date IS NOT NULL AND end_date < start_date),
       (SELECT format('{} bad', COUNT(*)) FROM subscriptions WHERE end_date IS NOT NULL AND end_date < start_date)
UNION ALL
SELECT 'an account never has two subscriptions at once',
       (SELECT COUNT(*) = 0 FROM sub_order WHERE next_start IS NOT NULL AND (end_date IS NULL OR next_start < end_date)),
       (SELECT format('{} overlaps', COUNT(*)) FROM sub_order
        WHERE next_start IS NOT NULL AND (end_date IS NULL OR next_start < end_date))
UNION ALL
SELECT 'mrr = seats x seat price (x 0.85 for annual billing)',
       (SELECT COUNT(*) = 0 FROM subscriptions
        WHERE ABS(mrr - seats * seat_price * CASE WHEN billing_period = 'annual' THEN 0.85 ELSE 1 END) > 0.01),
       (SELECT format('{} mismatches', COUNT(*)) FROM subscriptions
        WHERE ABS(mrr - seats * seat_price * CASE WHEN billing_period = 'annual' THEN 0.85 ELSE 1 END) > 0.01)
UNION ALL
SELECT 'invoice amounts are positive and paid invoices have a paid date',
       (SELECT COUNT(*) = 0 FROM invoices WHERE amount <= 0 OR (status = 'paid' AND paid_date IS NULL)),
       (SELECT format('{} bad', COUNT(*)) FROM invoices WHERE amount <= 0 OR (status = 'paid' AND paid_date IS NULL));
