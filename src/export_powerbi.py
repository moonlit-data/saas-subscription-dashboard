"""Export a star schema for Power BI (powerbi/*.csv). Measures are in powerbi/measures.dax.

Usage:  python src/export_powerbi.py      (after python src/run_pipeline.py)
"""
import pathlib

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "powerbi"

QUERIES = {
    "dim_account": "SELECT account_id, signup_date, segment, channel, region, industry FROM accounts",
    "dim_date": """SELECT CAST(d AS DATE) AS date, year(d) AS year, month(d) AS month_number,
                          strftime(d, '%b %Y') AS month_name, CAST(date_trunc('month', d) AS DATE) AS month_start
                   FROM generate_series(DATE '2023-01-01', DATE '2025-12-31', INTERVAL 1 DAY) AS t(d)""",
    "fact_account_month": """SELECT m.account_id, m.month, m.plan, m.billing_period, m.mrr, m.prev_mrr, m.mrr_change,
                                    m.movement, COALESCE(y.mrr, 0) AS mrr_12m_ago
                             FROM mrr_movements m
                             LEFT JOIN account_month y
                               ON y.account_id = m.account_id AND y.month = m.month - INTERVAL 12 MONTH""",
}


def main():
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect(str(ROOT / "data" / "saas.duckdb"), read_only=True)
    for name, sql in QUERIES.items():
        path = (OUT / f"{name}.csv").as_posix()
        con.execute(f"COPY ({sql}) TO '{path}' (HEADER, DELIMITER ',')").fetchall()
        n = con.execute(f"SELECT COUNT(*) FROM ({sql})").fetchall()[0][0]
        print(f"{name}: {n:,} rows")
    con.close()


if __name__ == "__main__":
    main()
