"""Static charts for the README (light and dark), drawn from results/*.csv.

Usage:  python src/make_charts.py      (after python src/run_pipeline.py)
Output: reports/figures/<chart>_light.png and <chart>_dark.png
"""
import csv
import pathlib

from matplotlib.colors import LinearSegmentedColormap

from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

from chart_style import PX, figure, money, month_label, rounded_bar, rounded_hbar, save, titles

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = ROOT / "reports" / "figures"

BLUE_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
             "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]


def read(name):
    with open(RESULTS / f"{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v):
    return float(v) if v not in ("", None) else None


def x_units(ax, px):
    return abs(px * (ax.get_xlim()[1] - ax.get_xlim()[0])
               / (ax.get_position().width * ax.figure.get_figwidth() * 100))


def kpis(segment="All"):
    return [r for r in read("kpi_monthly") if r["segment"] == segment]


def chart_gained_lost(theme):
    rows = kpis()[1:]                           # from February 2023 (January has no prior month)
    months = [r["month"] for r in rows]
    gained = [num(r["new_mrr"]) + num(r["expansion_mrr"]) + num(r["reactivation_mrr"]) for r in rows]
    lost = [num(r["contraction_mrr"]) + num(r["churned_mrr"]) for r in rows]
    net = [num(r["net_new_mrr"]) for r in rows]
    fig, ax, t = figure(theme, height_px=440, left=60, top=88)
    titles(fig, t, "MRR gained and lost each month",
           "Gained = new + expansion + reactivation. Lost = contraction + churn. Dots = net new MRR.")
    x = list(range(len(months)))
    ax.set_xlim(-0.8, len(months) - 0.2)
    ax.set_ylim(min(lost) * 1.35, max(gained) * 1.12)
    width = x_units(ax, 11)
    for i in x:
        rounded_bar(ax, i, width, 0, gained[i], t["up"], radius_px=3)
        rounded_bar(ax, i, width, 0, lost[i], t["down"], radius_px=3)
    ax.plot(x, net, "o", color=t["total"], markersize=6 * PX, markeredgecolor=t["surface"],
            markeredgewidth=2 * PX, zorder=4)
    ax.axhline(0, color=t["axis"], linewidth=1 * PX)
    handles = [Patch(color=t["up"], label="MRR gained"), Patch(color=t["down"], label="MRR lost"),
               Line2D([], [], marker="o", linestyle="", color=t["total"], markersize=6 * PX, label="Net new MRR")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.032, 1 - 58 / 440), ncol=3, frameon=False, fontsize=9,
               labelcolor=t["ink2"], handlelength=1.0, handleheight=0.8, columnspacing=1.6)
    j = months.index("2024-07")
    ax.annotate("Starter price increase\n(repricing counts as expansion)", xy=(j, gained[j]), xytext=(j - 9.5, max(gained) * 0.98),
                color=t["ink2"], fontsize=8.5, va="center",
                arrowprops={"arrowstyle": "-", "color": t["muted"], "linewidth": 1 * PX, "shrinkB": 3})
    k = months.index("2025-04")
    ax.annotate("Failed card payments", xy=(k, lost[k]), xytext=(k - 9, min(lost) * 1.18), color=t["ink2"],
                fontsize=8.5, va="center",
                arrowprops={"arrowstyle": "-", "color": t["muted"], "linewidth": 1 * PX, "shrinkB": 3})
    ticks = [i for i, m in enumerate(months) if m.endswith(("-01", "-07"))]
    ax.set_xticks(ticks, [month_label(months[i], True) for i in ticks])
    ax.yaxis.set_major_formatter(lambda v, _: money(v))
    ax.spines["bottom"].set_visible(False)
    save(fig, OUT / f"mrr_gained_lost_{theme}.png")


def chart_churn(theme):
    rows = kpis()[1:]
    months = [r["month"] for r in rows]
    churn = [num(r["logo_churn_pct"]) for r in rows]
    fig, ax, t = figure(theme, height_px=400, left=52)
    titles(fig, t, "Monthly logo churn", "Accounts that stopped paying, as a share of paying accounts at the start of the month")
    x = list(range(len(months)))
    ax.plot(x, churn, color=t["series"][0], linewidth=2 * PX, solid_joinstyle="round", solid_capstyle="round")
    for m, label, dx, dy in (("2024-07", "Starter price\nincrease", -6.2, 1.0), ("2025-03", "Card payment\nfailures", -6.5, 0.3)):
        i = months.index(m)
        ax.plot(x[i], churn[i], "o", color=t["series"][0], markersize=8 * PX, markeredgecolor=t["surface"],
                markeredgewidth=2 * PX, zorder=4)
        ax.annotate(f"{label}: {churn[i]:.1f}%", xy=(x[i], churn[i]), xytext=(x[i] + dx, churn[i] + dy),
                    color=t["ink2"], fontsize=8.5, va="center",
                    arrowprops={"arrowstyle": "-", "color": t["muted"], "linewidth": 1 * PX, "shrinkB": 5})
    ax.set_xlim(-0.5, len(months) - 0.5)
    ax.set_ylim(0, max(churn) * 1.25)
    ticks = [i for i, m in enumerate(months) if m.endswith(("-01", "-07"))]
    ax.set_xticks(ticks, [month_label(months[i], True) for i in ticks])
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    save(fig, OUT / f"logo_churn_{theme}.png")


def chart_cohorts(theme):
    rows = [r for r in read("cohort_retention") if r["segment"] == "All"]
    cohorts = sorted({r["cohort"] for r in rows})
    cols = list(range(0, 34, 3))
    val = {(r["cohort"], int(r["months_since_signup"])): num(r["logo_retention_pct"]) for r in rows}
    fig, ax, t = figure(theme, height_px=500, left=72, top=100, bottom=20)
    titles(fig, t, "Share of each signup cohort still paying (%)",
           "Accounts grouped by signup quarter; columns = months since signup; "
           + ("darker" if theme == "light" else "brighter") + " = more still paying")
    ramp = BLUE_RAMP if theme == "light" else BLUE_RAMP[::-1]
    cmap = LinearSegmentedColormap.from_list("blue", ramp)
    ax.grid(False)
    ax.set_xlim(-0.5, len(cols) - 0.5)
    ax.set_ylim(len(cohorts) - 0.5, -0.5)
    gap_x, gap_y = 0.04, 0.05
    for yi, c in enumerate(cohorts):
        for xi, k in enumerate(cols):
            v = val.get((c, k))
            if v is None:
                continue
            level = (v - 40) / 60                      # 40% .. 100% spans the ramp
            color = cmap(max(0.0, min(1.0, level)))
            ax.add_patch(Rectangle((xi - 0.5 + gap_x, yi - 0.5 + gap_y), 1 - 2 * gap_x, 1 - 2 * gap_y,
                                   facecolor=color, edgecolor="none"))
            r, g, b = color[:3]
            light_cell = 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.5
            ax.text(xi, yi, f"{v:.0f}", ha="center", va="center", fontsize=8,
                    color="#0b0b0b" if light_cell else "#ffffff")
    ax.set_xticks(range(len(cols)), [f"M{k}" for k in cols])
    ax.set_yticks(range(len(cohorts)), cohorts)
    ax.tick_params(axis="x", labeltop=True, labelbottom=False)
    for side in ("bottom", "left"):
        ax.spines[side].set_visible(False)
    save(fig, OUT / f"cohort_retention_{theme}.png")


def chart_channels(theme):
    rows = [r for r in read("channel_retention_2024") if r["segment"] == "All"]
    rows.sort(key=lambda r: num(r["still_paying_after_12m_pct"]))
    fig, ax, t = figure(theme, height_px=300, left=150, right=48, top=70, bottom=36)
    titles(fig, t, "Still paying 12 months after signup, by channel",
           "Accounts that signed up in 2024 (all segments)")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=t["grid"], linewidth=1 * PX)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlim(0, 100)
    height = (len(rows) + 0.2) * 22 / (ax.get_position().height * fig.get_figheight() * 100)
    for i, r in enumerate(rows):
        v = num(r["still_paying_after_12m_pct"])
        rounded_hbar(ax, i, height, 0, v, t["series"][0])
        ax.text(v + 1.2, i, f"{v:.0f}%", va="center", color=t["ink"], fontsize=9.5, fontweight="semibold")
    ax.set_yticks(range(len(rows)), [f"{r['channel']}  ({r['accounts']})" for r in rows])
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color(t["axis"])
    ax.spines["left"].set_linewidth(1 * PX)
    save(fig, OUT / f"channel_retention_{theme}.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for theme in ("light", "dark"):
        chart_gained_lost(theme)
        chart_churn(theme)
        chart_cohorts(theme)
        chart_channels(theme)
    print(f"charts written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
