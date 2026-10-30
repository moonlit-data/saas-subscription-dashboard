# How the data was made

Companies do not publish their subscription records, so this project uses a **simulated** company,
Ledgerly (invoicing software sold per seat to small and mid-sized businesses). `src/generate_data.py`
runs the simulation with a fixed random seed, so every run writes exactly the same files.

## What is simulated

- **Signups** from four channels (Organic, Paid Search, Outbound Sales, Partner), each with its own
  volume, growth and mix of segments (SMB, Mid-Market, Enterprise); busier in January.
- **Plans** priced per seat per month: Starter $12, Growth $25, Scale $40. Annual billing is 15% cheaper
  and is chosen more often by larger customers.
- **Every month, for every paying account:** a chance to cancel (higher for SMB, for monthly billing, in
  the first three months, and for Paid Search customers), to add or remove seats, or to change plan.
  Annual customers can only cancel or shrink at renewal.
- **Invoices:** monthly or annual; some card charges fail and are retried; an invoice that is never paid
  ends the subscription (involuntary churn).
- **Win-backs:** some churned accounts come back within 18 months.

## What was planted

These events are built into the simulation. The analysis was written to find them from the data alone,
and the tests check that it does.

| # | Event | When | Effect built in |
|---|---|---|---|
| 1 | Starter price rises from $12 to $15 per seat | 1 July 2024 | Monthly Starter customers are repriced at once (annual ones at renewal); their cancellation rate is 2.4x normal in July, 1.8x in August, 1.3x in September |
| 2 | Card payment problems after a processor change | March - April 2025 | First-charge failures rise from 2.5% to 9%; retries recover 30% instead of 80% |
| 3 | Partner channel opens | January 2024 | Partner customers cancel 40% less often than Organic customers of the same segment |

## Files

| File | Rows | What it is |
|---|---:|---|
| `data/accounts.csv` | 3,446 | one row per customer: signup date, segment, channel, region, industry |
| `data/plans.csv` | 3 | plan prices |
| `data/subscriptions.csv` | 5,525 | subscription history: one row per state (plan, seats, billing, MRR) with start and end dates |
| `data/invoices.csv` | 28,775 | every invoice: amount, status, retry attempts, paid date |
| `data/_truth/events.csv` | 6,882 | the simulator's own log of every MRR change - **read only by the tests** |

The data files are not stored in the repository; `python src/generate_data.py` recreates them in a second.

## How the analysis is checked against the simulation

`tests/test_metrics.py` nets the simulator's log per account and month (only the month-end result is
visible in the data) and compares it with the MRR bridge the SQL built from `subscriptions.csv` alone:
every account-month must get the same movement (new, expansion, contraction, churn, reactivation) and
the same dollar change. It also checks that the three planted events show up in the results.
