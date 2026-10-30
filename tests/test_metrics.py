"""Tests: the SQL metrics must agree with the simulator's own log of every MRR change.

The SQL never reads data/_truth/events.csv. Here the log is netted per account and month (an account
can change more than once in a month; only the month-end result is visible in the data) and compared
with the MRR bridge the SQL built from the subscription table alone.

Run:  python -m pytest        (generates the data and runs the pipeline first)
"""
import pathlib
import subprocess
import sys

import duckdb
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def con():
    for script in ("generate_data.py", "run_pipeline.py"):
        subprocess.run([sys.executable, str(ROOT / "src" / script)], check=True, cwd=ROOT)
    c = duckdb.connect(str(ROOT / "data" / "saas.duckdb"), read_only=True)
    yield c
    c.close()


@pytest.fixture(scope="session")
def truth():
    ev = pd.read_csv(ROOT / "data" / "_truth" / "events.csv", parse_dates=["month", "effective_date"])
    ev = ev.sort_values(["account_id", "effective_date"], kind="stable")
    net = ev.groupby(["account_id", "month"]).agg(before=("mrr_before", "first"), after=("mrr_after", "last"),
                                                  first_move=("movement", "first")).reset_index()
    def classify(r):
        if r.before == 0 and r.after > 0:
            return "new" if r.first_move == "new" else "reactivation"
        if r.before > 0 and r.after == 0:
            return "churn"
        if r.after > r.before:
            return "expansion"
        if r.after < r.before:
            return "contraction"
        return "none"
    net["movement"] = net.apply(classify, axis=1)
    net["change"] = net["after"] - net["before"]
    return net[net.movement != "none"]


def test_all_checks_pass(con):
    assert con.execute("SELECT check_name, detail FROM result_checks WHERE NOT passed").fetchall() == []


def test_mrr_bridge_matches_simulator(con, truth):
    sql = con.execute("""SELECT month, movement, COUNT(*) AS n, ROUND(SUM(mrr_change), 2) AS change
                         FROM mrr_movements WHERE movement <> 'none' GROUP BY ALL""").df()
    sql["month"] = pd.to_datetime(sql["month"])
    exp = truth.groupby(["month", "movement"]).agg(n=("change", "size"), change=("change", "sum")).reset_index()
    merged = exp.merge(sql, on=["month", "movement"], how="outer", suffixes=("_truth", "_sql")).fillna(0)
    bad = merged[(merged.n_truth != merged.n_sql) | ((merged.change_truth - merged.change_sql).abs() > 0.01)]
    assert bad.empty, bad.head(10).to_string()


def test_every_account_month_matches(con, truth):
    sql = con.execute("SELECT account_id, month, movement FROM mrr_movements WHERE movement <> 'none'").df()
    sql["month"] = pd.to_datetime(sql["month"])
    merged = truth.merge(sql, on=["account_id", "month"], how="outer", suffixes=("_truth", "_sql"))
    assert (merged.movement_truth == merged.movement_sql).all()


def test_planted_price_increase_is_found(con):
    row = con.execute("SELECT * FROM result_price_increase_effect WHERE plan = 'Starter'").df().iloc[0]
    control = con.execute("SELECT * FROM result_price_increase_effect WHERE plan = 'Growth'").df().iloc[0]
    assert row.excess_churned_accounts > 40          # Starter churn jumped after the increase
    assert abs(control.excess_churned_accounts) < 15  # the plan that was not repriced did not
    assert row.net_mrr_effect > 0                     # and the increase still paid for itself


def test_planted_payment_outage_is_found(con):
    p = con.execute("SELECT month, involuntary_churn_accounts FROM result_payments_monthly").df().set_index("month")
    outage = p.loc[["2025-03", "2025-04"], "involuntary_churn_accounts"].mean()
    normal = p.drop(index=["2025-03", "2025-04"]).loc["2024-01":, "involuntary_churn_accounts"].mean()
    assert outage > 5 * normal


def test_partner_retains_better_within_segment(con):
    r = con.execute("""SELECT channel, segment, still_paying_after_12m_pct FROM result_channel_retention_2024
                       WHERE segment IN ('SMB', 'Mid-Market')""").df()
    for seg in ("SMB", "Mid-Market"):
        s = r[r.segment == seg].set_index("channel").still_paying_after_12m_pct
        assert s["Partner"] > s["Organic"] and s["Partner"] > s["Paid Search"]
