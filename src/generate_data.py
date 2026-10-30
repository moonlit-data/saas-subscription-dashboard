"""Generate the synthetic data set: a fictional B2B SaaS company ("Ledgerly", invoicing software).

Real subscription data is not public, so the data is simulated with a fixed seed (every run writes the
same files). The simulation plants a few business events, listed in docs/data_generation.md. The SQL in
sql/ never reads the simulator's own log; tests/ compare what the SQL finds with that log.

Usage:  python src/generate_data.py
Output: data/accounts.csv, data/plans.csv, data/subscriptions.csv, data/invoices.csv
        data/_truth/events.csv   (every MRR change as the simulator made it; read by the tests only)
"""
import calendar
import datetime as dt
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
SEED = 20261029

FIRST_MONTH = dt.date(2023, 1, 1)
N_MONTHS = 36                        # January 2023 .. December 2025
ANNUAL_DISCOUNT = 0.15               # annual billing: 15% off the monthly list price

PLANS = {                            # list price per seat per month, seats at signup (min, max)
    "Starter": (12, 1, 5),
    "Growth": (25, 3, 25),
    "Scale": (40, 15, 120),
}
PLAN_ORDER = ["Starter", "Growth", "Scale"]

# Planted events (docs/data_generation.md)
PRICE_CHANGE = dt.date(2024, 7, 1)           # 1. Starter goes from $12 to $15 per seat
STARTER_NEW_PRICE = 15
PRICE_CHURN_BOOST = {dt.date(2024, 7, 1): 2.4, dt.date(2024, 8, 1): 1.8, dt.date(2024, 9, 1): 1.3}
PAYMENT_OUTAGE = {dt.date(2025, 3, 1), dt.date(2025, 4, 1)}   # 2. card payments fail more, retries fail more
PARTNER_LAUNCH = dt.date(2024, 1, 1)         # 3. partner channel opens; its customers churn less

CHANNELS = {   # signups per month at launch, monthly growth, segment mix (SMB, Mid-Market, Enterprise)
    "Organic": (38, 0.015, (0.80, 0.18, 0.02)),
    "Paid Search": (30, 0.004, (0.86, 0.13, 0.01)),
    "Outbound Sales": (5, 0.010, (0.10, 0.55, 0.35)),
    "Partner": (9, 0.025, (0.30, 0.60, 0.10)),
}
SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]
PLAN_MIX = {"SMB": (0.78, 0.22, 0.0), "Mid-Market": (0.12, 0.68, 0.20), "Enterprise": (0.0, 0.25, 0.75)}
ANNUAL_SHARE = {"SMB": 0.22, "Mid-Market": 0.45, "Enterprise": 0.80}
MONTHLY_CHURN = {"SMB": 0.034, "Mid-Market": 0.014, "Enterprise": 0.006}
RENEWAL_CHURN = {"SMB": 0.22, "Mid-Market": 0.11, "Enterprise": 0.05}
CHANNEL_CHURN = {"Organic": 1.0, "Paid Search": 1.25, "Outbound Sales": 0.9, "Partner": 0.6}
SEAT_UP = {"SMB": 0.015, "Mid-Market": 0.035, "Enterprise": 0.045}
SEAT_DOWN = {"SMB": 0.008, "Mid-Market": 0.015, "Enterprise": 0.02}
UPGRADE = {"SMB": 0.008, "Mid-Market": 0.006, "Enterprise": 0.003}
DOWNGRADE = {"SMB": 0.002, "Mid-Market": 0.004, "Enterprise": 0.003}
REACTIVATE = {"SMB": 0.012, "Mid-Market": 0.008, "Enterprise": 0.004}
CARD_FAIL = (0.025, 0.09)            # share of monthly invoices whose first charge fails: normal, outage
RETRY_SUCCESS = (0.80, 0.30)         # share of failed charges recovered by retries: normal, outage
REGIONS = (["North America", "Europe", "Asia Pacific"], [0.55, 0.30, 0.15])
INDUSTRIES = (["Professional Services", "Retail", "Manufacturing", "Healthcare", "Software", "Nonprofit"],
              [0.28, 0.20, 0.16, 0.14, 0.14, 0.08])


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    return dt.date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def month_end(d):
    return dt.date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def seat_price(plan, on_date):
    if plan == "Starter" and on_date >= PRICE_CHANGE:
        return STARTER_NEW_PRICE
    return PLANS[plan][0]


class Sim:
    def __init__(self):
        self.rng = np.random.default_rng(SEED)
        self.accounts, self.subs, self.invoices, self.events = [], [], [], []
        self.state = {}    # account_id -> dict of the live subscription (or churned info)

    # ---- helpers -------------------------------------------------------------------------------
    def day_in(self, month, earliest=1):
        last = calendar.monthrange(month.year, month.month)[1]
        return dt.date(month.year, month.month, int(self.rng.integers(earliest, last + 1)))

    def mrr(self, plan, seats, billing, price_date):
        price = seat_price(plan, price_date)
        factor = (1 - ANNUAL_DISCOUNT) if billing == "annual" else 1.0
        return round(seats * price * factor, 2)

    def open_sub(self, acc_id, plan, seats, billing, start, reason, term_start=None, price_date=None):
        sub_id = f"S{len(self.subs) + 1:06d}"
        price_date = price_date or start
        row = {"subscription_id": sub_id, "account_id": acc_id, "plan": plan, "seats": seats,
               "billing_period": billing, "seat_price": seat_price(plan, price_date),
               "mrr": self.mrr(plan, seats, billing, price_date), "start_date": start, "end_date": None,
               "start_reason": reason, "end_reason": None}
        self.subs.append(row)
        st = self.state[acc_id]
        st.update(sub=row, active=True, term_start=term_start or start, churned_on=None)
        return row

    def close_sub(self, acc_id, on, reason):
        row = self.state[acc_id]["sub"]
        row["end_date"], row["end_reason"] = on, reason

    def log(self, acc_id, month, on, movement, detail, before, after):
        self.events.append({"account_id": acc_id, "month": month, "effective_date": on, "movement": movement,
                            "detail": detail, "mrr_before": before, "mrr_after": after})

    def invoice(self, acc_id, sub, on, period_end, amount, outage, first=False):
        fail_p = 0.0 if first else (CARD_FAIL[1] if outage else CARD_FAIL[0])
        if sub["billing_period"] == "annual" and not first:
            fail_p = 0.01
        failed = self.rng.random() < fail_p
        recovered = failed and self.rng.random() < (RETRY_SUCCESS[1] if outage else RETRY_SUCCESS[0])
        status = "paid" if (not failed or recovered) else "failed"
        paid = on + dt.timedelta(days=int(self.rng.integers(3, 11))) if recovered else (on if status == "paid" else None)
        self.invoices.append({"invoice_id": f"INV{len(self.invoices) + 1:07d}", "account_id": acc_id,
                              "subscription_id": sub["subscription_id"], "invoice_date": on,
                              "period_start": on, "period_end": period_end, "amount": round(amount, 2),
                              "status": status, "attempts": 1 + (2 if failed else 0), "paid_date": paid})
        return status == "paid"

    # ---- the simulation ------------------------------------------------------------------------
    def signups(self, m_idx, month):
        for channel, (base, growth, mix) in CHANNELS.items():
            if channel == "Partner" and month < PARTNER_LAUNCH:
                continue
            months_live = m_idx if channel != "Partner" else (month.year - 2024) * 12 + month.month - 1
            season = 1.0 + 0.12 * np.cos(2 * np.pi * (month.month - 1) / 12)   # busiest in January
            n = self.rng.poisson(base * (1 + growth) ** months_live * season)
            for _ in range(n):
                self.new_account(month, channel, mix)

    def new_account(self, month, channel, mix):
        acc_id = f"A{len(self.accounts) + 1:05d}"
        seg = self.rng.choice(SEGMENTS, p=mix)
        plan = self.rng.choice(PLAN_ORDER, p=PLAN_MIX[seg])
        lo, hi = PLANS[plan][1], PLANS[plan][2]
        seats = int(np.clip(round(lo * self.rng.lognormal(0.45, 0.55)), lo, hi))
        billing = "annual" if self.rng.random() < ANNUAL_SHARE[seg] else "monthly"
        start = self.day_in(month)
        self.accounts.append({"account_id": acc_id, "signup_date": start, "segment": seg, "channel": channel,
                              "region": self.rng.choice(REGIONS[0], p=REGIONS[1]),
                              "industry": self.rng.choice(INDUSTRIES[0], p=INDUSTRIES[1])})
        self.state[acc_id] = {"segment": seg, "channel": channel, "billing_day": min(start.day, 28)}
        sub = self.open_sub(acc_id, plan, seats, billing, start, "new")
        self.log(acc_id, month, start, "new", "signup", 0.0, sub["mrr"])
        period_end = add_months(start, 12 if billing == "annual" else 1)
        self.invoice(acc_id, sub, start, period_end, sub["mrr"] * (12 if billing == "annual" else 1), False, first=True)

    def step_account(self, acc_id, month):
        st = self.state[acc_id]
        seg, channel = st["segment"], st["channel"]
        outage = month in PAYMENT_OUTAGE
        if not st["active"]:
            gone = (month.year - st["churned_on"].year) * 12 + month.month - st["churned_on"].month
            if 1 <= gone <= 18 and self.rng.random() < REACTIVATE[seg]:
                old = st["last_sub"]
                plan = old["plan"] if self.rng.random() < 0.7 else PLAN_ORDER[max(0, PLAN_ORDER.index(old["plan"]) - 1)]
                lo, hi = PLANS[plan][1], PLANS[plan][2]
                seats = int(np.clip(old["seats"], lo, hi))
                on = self.day_in(month)
                sub = self.open_sub(acc_id, plan, seats, "monthly", on, "reactivation")
                self.log(acc_id, month, on, "reactivation", "returned", 0.0, sub["mrr"])
                self.invoice(acc_id, sub, on, add_months(on, 1), sub["mrr"], outage, first=True)
            return

        sub = st["sub"]
        if sub["start_date"] >= month:      # started this month: nothing else happens yet
            return
        before = sub["mrr"]
        billing = sub["billing_period"]
        tenure = (month.year - sub["start_date"].year) * 12 + month.month - sub["start_date"].month
        bill_day = dt.date(month.year, month.month, st["billing_day"])

        # Annual subscriptions only renew (or not) on their anniversary month
        renewal = billing == "annual" and (
            (month.year - st["term_start"].year) * 12 + month.month - st["term_start"].month) % 12 == 0

        # 1. Voluntary churn
        churn_p = 0.0
        if billing == "monthly":
            churn_p = MONTHLY_CHURN[seg] * CHANNEL_CHURN[channel] * (1.5 if tenure <= 3 else 1.0)
            if sub["plan"] == "Starter":
                churn_p *= PRICE_CHURN_BOOST.get(month, 1.0)
        elif renewal:
            churn_p = RENEWAL_CHURN[seg] * CHANNEL_CHURN[channel]
            if sub["plan"] == "Starter" and PRICE_CHANGE <= month < add_months(PRICE_CHANGE, 12):
                churn_p *= 1.4
        if self.rng.random() < churn_p:
            on = self.day_in(month)
            self.close_sub(acc_id, on, "churn")
            st.update(active=False, churned_on=month, last_sub=sub)
            self.log(acc_id, month, on, "churn", "cancelled", before, 0.0)
            return

        # 2. The price increase reaches Starter monthly customers on 1 July 2024
        if billing == "monthly" and sub["plan"] == "Starter" and month == PRICE_CHANGE:
            self.close_sub(acc_id, PRICE_CHANGE, "change")
            new = self.open_sub(acc_id, "Starter", sub["seats"], "monthly", PRICE_CHANGE, "price_increase")
            self.log(acc_id, month, PRICE_CHANGE, "expansion", "price_increase", before, new["mrr"])
            sub, before = new, new["mrr"]
            if not self.invoice(acc_id, sub, bill_day, add_months(bill_day, 1), sub["mrr"], outage):
                self.payment_churn(acc_id, month, bill_day, before)
            return

        # 3. Billing: monthly every month, annual at renewal (with the new price and maybe new seats)
        if billing == "monthly":
            if not self.invoice(acc_id, sub, bill_day, add_months(bill_day, 1), sub["mrr"], outage):
                self.payment_churn(acc_id, month, bill_day, before)
                return
        elif renewal:
            seats = old_seats = sub["seats"]
            r = self.rng.random()
            if r < SEAT_UP[seg] * 4:
                seats = min(PLANS[sub["plan"]][2] * 2, max(seats + 1, round(seats * self.rng.uniform(1.1, 1.4))))
            elif r < (SEAT_UP[seg] + SEAT_DOWN[seg]) * 4:
                seats = max(PLANS[sub["plan"]][1], round(seats * self.rng.uniform(0.6, 0.9)))
            new_mrr = self.mrr(sub["plan"], seats, "annual", bill_day)
            if new_mrr != before:
                self.close_sub(acc_id, bill_day, "change")
                sub = self.open_sub(acc_id, sub["plan"], seats, "annual", bill_day, "renewal_change", term_start=bill_day)
                movement = "expansion" if new_mrr > before else "contraction"
                if seats == old_seats:
                    detail = "price_increase"
                else:
                    detail = "seats_up" if seats > old_seats else "seats_down"
                self.log(acc_id, month, bill_day, movement, detail, before, new_mrr)
            else:
                st["term_start"] = bill_day
            if not self.invoice(acc_id, sub, bill_day, add_months(bill_day, 12), sub["mrr"] * 12, outage):
                self.payment_churn(acc_id, month, bill_day, sub["mrr"])
            return

        # 4. Seat and plan changes (annual customers can only grow mid-term)
        r = self.rng.random()
        plan, seats = sub["plan"], sub["seats"]
        idx = PLAN_ORDER.index(plan)
        cut = np.cumsum([SEAT_UP[seg], UPGRADE[seg], SEAT_DOWN[seg], DOWNGRADE[seg]])
        if r < cut[0]:
            detail = "seats_up"
            seats = min(PLANS[plan][2] * 3, max(seats + 1, round(seats * self.rng.uniform(1.1, 1.5))))
        elif r < cut[1] and idx < 2:
            detail, plan = "upgrade", PLAN_ORDER[idx + 1]
            seats = max(seats, PLANS[plan][1])
        elif r < cut[2] and billing == "monthly" and seats > PLANS[plan][1]:
            detail, seats = "seats_down", max(PLANS[plan][1], round(seats * self.rng.uniform(0.5, 0.9)))
        elif r < cut[3] and billing == "monthly" and idx > 0:
            detail, plan = "downgrade", PLAN_ORDER[idx - 1]
            seats = min(max(seats, PLANS[plan][1]), PLANS[plan][2] * 2)
        else:
            return
        on = self.day_in(month)
        new_mrr = self.mrr(plan, seats, billing, on if billing == "monthly" else st["term_start"])
        if new_mrr == before:
            return
        self.close_sub(acc_id, on, "change")
        new = self.open_sub(acc_id, plan, seats, billing, on, detail, term_start=st["term_start"],
                            price_date=on if billing == "monthly" else st["term_start"])
        self.log(acc_id, month, on, "expansion" if new_mrr > before else "contraction", detail, before, new_mrr)
        if billing == "annual":      # prorated invoice for the rest of the annual term
            term_end = add_months(st["term_start"], 12)
            months_left = max(1, (term_end.year - on.year) * 12 + term_end.month - on.month)
            self.invoice(acc_id, new, on, term_end, (new_mrr - before) * months_left, outage)

    def payment_churn(self, acc_id, month, bill_day, before):
        on = min(bill_day + dt.timedelta(days=14), month_end(bill_day))
        st = self.state[acc_id]
        self.close_sub(acc_id, on, "payment_failed")
        st.update(active=False, churned_on=month, last_sub=st["sub"])
        self.log(acc_id, month, on, "churn", "payment_failed", before, 0.0)

    def run(self):
        for m_idx in range(N_MONTHS):
            month = add_months(FIRST_MONTH, m_idx)
            for acc_id in list(self.state):
                self.step_account(acc_id, month)
            self.signups(m_idx, month)


def main():
    sim = Sim()
    sim.run()
    OUT.mkdir(exist_ok=True)
    (OUT / "_truth").mkdir(exist_ok=True)
    pd.DataFrame(sim.accounts).to_csv(OUT / "accounts.csv", index=False)
    pd.DataFrame([{"plan": p, "seat_price": v[0], "seat_price_from_2024_07": seat_price(p, PRICE_CHANGE),
                   "min_seats_at_signup": v[1], "max_seats_at_signup": v[2]} for p, v in PLANS.items()]
                 ).to_csv(OUT / "plans.csv", index=False)
    pd.DataFrame(sim.subs).to_csv(OUT / "subscriptions.csv", index=False)
    pd.DataFrame(sim.invoices).to_csv(OUT / "invoices.csv", index=False)
    pd.DataFrame(sim.events).to_csv(OUT / "_truth" / "events.csv", index=False)
    print(f"accounts {len(sim.accounts):,}  subscriptions {len(sim.subs):,}  invoices {len(sim.invoices):,}  "
          f"events {len(sim.events):,}")


if __name__ == "__main__":
    main()
