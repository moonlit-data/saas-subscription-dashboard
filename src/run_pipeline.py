"""Load the CSV files into DuckDB, run sql/01..09 in order, export result_* tables to results/*.csv.

Usage:  python src/run_pipeline.py        (after python src/generate_data.py)
Stops with an error if any check in result_checks fails.
"""
import pathlib
import sys

import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB = DATA / "saas.duckdb"
RESULTS = ROOT / "results"

SCHEMAS = {
    "accounts": {"account_id": "VARCHAR", "signup_date": "DATE", "segment": "VARCHAR", "channel": "VARCHAR",
                 "region": "VARCHAR", "industry": "VARCHAR"},
    "plans": {"plan": "VARCHAR", "seat_price": "DECIMAL(10,2)", "seat_price_from_2024_07": "DECIMAL(10,2)",
              "min_seats_at_signup": "INTEGER", "max_seats_at_signup": "INTEGER"},
    "subscriptions": {"subscription_id": "VARCHAR", "account_id": "VARCHAR", "plan": "VARCHAR", "seats": "INTEGER",
                      "billing_period": "VARCHAR", "seat_price": "DECIMAL(10,2)", "mrr": "DECIMAL(12,2)",
                      "start_date": "DATE", "end_date": "DATE", "start_reason": "VARCHAR", "end_reason": "VARCHAR"},
    "invoices": {"invoice_id": "VARCHAR", "account_id": "VARCHAR", "subscription_id": "VARCHAR",
                 "invoice_date": "DATE", "period_start": "DATE", "period_end": "DATE", "amount": "DECIMAL(12,2)",
                 "status": "VARCHAR", "attempts": "INTEGER", "paid_date": "DATE"},
}


def main():
    missing = [t for t in SCHEMAS if not (DATA / f"{t}.csv").exists()]
    if missing:
        sys.exit(f"missing data files {missing}: run  python src/generate_data.py  first")
    con = duckdb.connect(str(DB))
    for table, cols in SCHEMAS.items():
        spec = ", ".join(f"'{c}': '{t}'" for c, t in cols.items())
        path = (DATA / f"{table}.csv").as_posix()
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv('{path}', header = true, "
                    f"columns = {{{spec}}})").fetchall()
    for path in sorted((ROOT / "sql").glob("[0-9][0-9]_*.sql")):
        print(f"running {path.name}")
        for stmt in duckdb.extract_statements(path.read_text(encoding="utf-8")):
            con.execute(stmt).fetchall()
    RESULTS.mkdir(exist_ok=True)
    tables = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'result_%' ORDER BY 1").fetchall()]
    for name in tables:
        out = RESULTS / f"{name.removeprefix('result_')}.csv"
        con.execute(f"COPY {name} TO '{out.as_posix()}' (HEADER, DELIMITER ',')").fetchall()
    print(f"wrote {len(tables)} result tables to results/")
    failed = con.execute("SELECT check_name, detail FROM result_checks WHERE NOT passed").fetchall()
    total = con.execute("SELECT COUNT(*) FROM result_checks").fetchall()[0][0]
    con.close()
    if failed:
        for name, detail in failed:
            print(f"CHECK FAILED: {name}: {detail}")
        sys.exit(1)
    print(f"all {total} checks passed")


if __name__ == "__main__":
    main()
