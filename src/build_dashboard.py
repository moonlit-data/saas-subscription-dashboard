"""Build the interactive dashboard (docs/index.html) from results/*.csv.

Usage:  python src/build_dashboard.py      (after python src/run_pipeline.py)
The page is one static HTML file (Plotly from its CDN); GitHub Pages serves it from docs/.
"""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = ROOT / "docs" / "index.html"
SEGMENTS = ["All", "SMB", "Mid-Market", "Enterprise"]


def read(name):
    with open(RESULTS / f"{name}.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v):
    return float(v) if v not in ("", None) else None


def build_data():
    kpi = read("kpi_monthly")
    coh = read("cohort_retention")
    data = {"segments": {}, "cohorts": {}}
    for seg in SEGMENTS:
        rows = [r for r in kpi if r["segment"] == seg]
        series = {k: [num(r[k]) for r in rows] for k in (
            "mrr", "arr", "paying_accounts", "arppu", "new_mrr", "expansion_mrr", "reactivation_mrr",
            "contraction_mrr", "churned_mrr", "net_new_mrr", "logo_churn_pct", "nrr_t12m_pct", "grr_t12m_pct",
            "new_accounts", "churned_accounts")}
        series["months"] = [r["month"] for r in rows]
        data["segments"][seg] = series
        crow = [r for r in coh if r["segment"] == seg]
        cohorts = sorted({r["cohort"] for r in crow})
        cols = list(range(0, 34, 3))
        val = {(r["cohort"], int(r["months_since_signup"])): num(r["logo_retention_pct"]) for r in crow}
        data["cohorts"][seg] = {"cohorts": cohorts, "cols": [f"M{k}" for k in cols],
                                "z": [[val.get((c, k)) for k in cols] for c in cohorts]}
    return data


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ledgerly - subscription metrics dashboard (synthetic data)</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<style>
.viz-root {
  color-scheme: light;
  --page: #f9f9f7; --surface-1: #fcfcfb; --text-primary: #0b0b0b; --text-secondary: #52514e;
  --muted: #898781; --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --series-1: #2a78d6; --series-2: #eb6834; --up: #2a78d6; --down: #e34948; --total: #52514e;
  --good: #006300; --bad: #d03b3b;
  --ramp: "#cde2fb,#b7d3f6,#9ec5f4,#86b6ef,#6da7ec,#5598e7,#3987e5,#2a78d6,#256abf,#1c5cab,#184f95,#104281,#0d366b";
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) .viz-root {
    color-scheme: dark;
    --page: #0d0d0d; --surface-1: #1a1a19; --text-primary: #f0efec; --text-secondary: #c3c2b7;
    --muted: #898781; --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --series-2: #d95926; --up: #3987e5; --down: #e66767; --total: #c3c2b7;
    --good: #0ca30c; --bad: #e66767;
    --ramp: "#0d366b,#104281,#184f95,#1c5cab,#256abf,#2a78d6,#3987e5,#5598e7,#6da7ec,#86b6ef,#9ec5f4,#b7d3f6,#cde2fb";
  }
}
:root[data-theme="dark"] .viz-root {
    color-scheme: dark;
    --page: #0d0d0d; --surface-1: #1a1a19; --text-primary: #f0efec; --text-secondary: #c3c2b7;
    --muted: #898781; --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --series-2: #d95926; --up: #3987e5; --down: #e66767; --total: #c3c2b7;
    --good: #0ca30c; --bad: #e66767;
    --ramp: "#0d366b,#104281,#184f95,#1c5cab,#256abf,#2a78d6,#3987e5,#5598e7,#6da7ec,#86b6ef,#9ec5f4,#b7d3f6,#cde2fb";
}
body { margin: 0; }
.viz-root { background: var(--page); color: var(--text-primary); min-height: 100vh;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
.wrap { max-width: 1180px; margin: 0 auto; padding: 28px 24px 48px; }
h1 { font-size: 22px; font-weight: 600; margin: 0 0 4px; }
.sub { color: var(--text-secondary); font-size: 14px; margin: 0 0 18px; }
.note { font-size: 13px; color: var(--text-secondary); border: 1px solid var(--border); border-radius: 8px;
  padding: 8px 12px; margin-bottom: 18px; background: var(--surface-1); }
.filters { display: flex; gap: 12px; align-items: center; margin-bottom: 18px; font-size: 14px; }
.filters select { font: inherit; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--border);
  background: var(--surface-1); color: var(--text-primary); }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 18px; }
.tile { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
.tile .label { font-size: 13px; color: var(--text-secondary); }
.tile .value { font-size: 26px; font-weight: 600; margin: 4px 0 2px; }
.tile .delta { font-size: 13px; color: var(--text-secondary); }
.tile .delta .up-good, .tile .delta .down-good { color: var(--good); font-weight: 600; }
.tile .delta .up-bad, .tile .delta .down-bad { color: var(--bad); font-weight: 600; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(520px, 1fr)); gap: 12px; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px 6px; }
.card h2 { font-size: 15px; font-weight: 600; margin: 0 0 2px; }
.card p { font-size: 12.5px; color: var(--text-secondary); margin: 0 0 4px; }
.chart { height: 300px; }
.wide { grid-column: 1 / -1; }
details { margin-top: 18px; background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 10px 16px; }
summary { cursor: pointer; font-size: 14px; }
table { border-collapse: collapse; font-size: 12.5px; margin-top: 10px; width: 100%;
  font-variant-numeric: tabular-nums; }
th, td { padding: 4px 8px; text-align: right; border-bottom: 1px solid var(--grid); }
th:first-child, td:first-child { text-align: left; }
th { color: var(--text-secondary); font-weight: 600; }
footer { margin-top: 18px; font-size: 12.5px; color: var(--text-secondary); }
a { color: var(--series-1); }
</style>
</head>
<body>
<div class="viz-root">
<div class="wrap">
  <h1>Ledgerly subscription metrics</h1>
  <p class="sub">MRR, retention and churn, January 2023 - December 2025</p>
  <div class="note">Ledgerly is a fictional company and every number here is simulated
    (<a href="https://github.com/__REPO__">how the data was made, the SQL and the checks</a>).</div>
  <div class="filters"><label for="seg">Segment</label>
    <select id="seg"><option>All</option><option>SMB</option><option>Mid-Market</option><option>Enterprise</option></select>
  </div>
  <div class="tiles" id="tiles"></div>
  <div class="grid">
    <div class="card"><h2>Monthly recurring revenue</h2><p>Month-end MRR</p><div class="chart" id="c-mrr"></div></div>
    <div class="card"><h2>MRR gained and lost</h2><p>Gained = new + expansion + reactivation; lost = contraction + churn; dots = net new MRR</p><div class="chart" id="c-move"></div></div>
    <div class="card"><h2>Monthly logo churn</h2><p>Accounts that stopped paying / paying accounts at the start of the month</p><div class="chart" id="c-churn"></div></div>
    <div class="card"><h2>Revenue retention, trailing 12 months</h2><p>MRR today from accounts that paid 12 months ago, vs what they paid then</p><div class="chart" id="c-ret"></div></div>
    <div class="card wide"><h2>Share of each signup cohort still paying (%)</h2><p>Rows = signup quarter; columns = months since signup</p><div class="chart" id="c-coh" style="height:380px"></div></div>
  </div>
  <details><summary>Table view: monthly numbers for the selected segment</summary><div id="table"></div></details>
  <footer>Built from the CSV files in <code>results/</code> by <code>src/build_dashboard.py</code>.</footer>
</div>
</div>
<script>
const DATA = __DATA__;
const css = n => getComputedStyle(document.querySelector('.viz-root')).getPropertyValue(n).trim();
const fmtMoney = v => v == null ? '-' : (Math.abs(v) >= 1e6 ? '$' + (v / 1e6).toFixed(2) + 'M'
  : Math.abs(v) >= 1e3 ? '$' + (v / 1e3).toFixed(1) + 'K' : '$' + v.toFixed(0));
const fmtPct = v => v == null ? '-' : v.toFixed(1) + '%';
const MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ');
const label = ym => MONTHS[+ym.slice(5) - 1] + ' ' + ym.slice(0, 4);
const avg = a => a.reduce((s, v) => s + v, 0) / a.length;

function baseLayout(extra) {
  return Object.assign({
    paper_bgcolor: css('--surface-1'), plot_bgcolor: css('--surface-1'),
    font: { family: 'system-ui, -apple-system, "Segoe UI", sans-serif', size: 12, color: css('--text-secondary') },
    margin: { l: 56, r: 12, t: 8, b: 36 }, showlegend: false,
    hoverlabel: { bgcolor: css('--surface-1'), bordercolor: css('--axis'), font: { color: css('--text-primary') } },
    xaxis: { gridcolor: css('--grid'), linecolor: css('--axis'), tickcolor: css('--axis'), showgrid: false, ticks: '' },
    yaxis: { gridcolor: css('--grid'), gridwidth: 1, zerolinecolor: css('--axis'), linecolor: css('--axis'), ticks: '' },
  }, extra || {});
}
const CFG = { displayModeBar: false, responsive: true };

function tile(labelText, value, deltaText, cls) {
  const d = document.createElement('div'); d.className = 'tile';
  const l = document.createElement('div'); l.className = 'label'; l.textContent = labelText;
  const v = document.createElement('div'); v.className = 'value'; v.textContent = value;
  const de = document.createElement('div'); de.className = 'delta';
  if (deltaText) { const s = document.createElement('span'); s.className = cls; s.textContent = deltaText;
    de.appendChild(s); de.appendChild(document.createTextNode(' vs Dec 2024')); }
  d.append(l, v, de); return d;
}

function render() {
  const seg = document.getElementById('seg').value;
  const S = DATA.segments[seg];
  const n = S.months.length, last = n - 1, yearAgo = n - 13;
  const x = S.months.map(m => m + '-01');

  // KPI tiles
  const tiles = document.getElementById('tiles'); tiles.replaceChildren();
  const ch = (a, b) => (100 * (a / b - 1));
  const sign = v => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(1);
  const g = ch(S.mrr[last], S.mrr[yearAgo]);
  tiles.append(
    tile('MRR, Dec 2025', fmtMoney(S.mrr[last]), sign(g) + '%', g >= 0 ? 'up-good' : 'down-bad'),
    tile('ARR', fmtMoney(S.arr[last]), sign(ch(S.arr[last], S.arr[yearAgo])) + '%', g >= 0 ? 'up-good' : 'down-bad'),
    tile('Paying accounts', S.paying_accounts[last].toLocaleString('en-US'),
         sign(ch(S.paying_accounts[last], S.paying_accounts[yearAgo])) + '%',
         S.paying_accounts[last] >= S.paying_accounts[yearAgo] ? 'up-good' : 'down-bad'),
    tile('Average MRR per paying account', fmtMoney(S.arppu[last]),
         sign(ch(S.arppu[last], S.arppu[yearAgo])) + '%', S.arppu[last] >= S.arppu[yearAgo] ? 'up-good' : 'down-bad'));
  const churn25 = avg(S.logo_churn_pct.slice(n - 12)), churn24 = avg(S.logo_churn_pct.slice(n - 24, n - 12));
  const t = document.createElement('div');
  tiles.append(
    tile('Logo churn, 2025 monthly average', fmtPct(churn25), sign(churn25 - churn24) + ' pts',
         churn25 <= churn24 ? 'down-good' : 'up-bad'),
    tile('Net revenue retention (12 months)', fmtPct(S.nrr_t12m_pct[last]),
         sign(S.nrr_t12m_pct[last] - S.nrr_t12m_pct[yearAgo]) + ' pts',
         S.nrr_t12m_pct[last] >= S.nrr_t12m_pct[yearAgo] ? 'up-good' : 'down-bad'));

  // MRR
  Plotly.react('c-mrr', [{ x, y: S.mrr, type: 'scatter', mode: 'lines', fill: 'tozeroy',
    line: { color: css('--series-1'), width: 2 }, fillcolor: css('--series-1') + '1a',
    hovertemplate: '<b>%{y:$,.0f}</b><br>%{x|%b %Y}<extra></extra>' }],
    baseLayout({ hovermode: 'x', yaxis: Object.assign(baseLayout().yaxis, { tickformat: '$~s' }) }), CFG);

  // Gained / lost
  const gained = S.months.map((_, i) => S.new_mrr[i] + S.expansion_mrr[i] + S.reactivation_mrr[i]);
  const lost = S.months.map((_, i) => S.contraction_mrr[i] + S.churned_mrr[i]);
  Plotly.react('c-move', [
    { x: x.slice(1), y: gained.slice(1), name: 'Gained', type: 'bar', marker: { color: css('--up'), cornerradius: 3 },
      hovertemplate: '<b>%{y:$,.0f}</b> gained<extra></extra>' },
    { x: x.slice(1), y: lost.slice(1), name: 'Lost', type: 'bar', marker: { color: css('--down'), cornerradius: 3 },
      hovertemplate: '<b>%{y:$,.0f}</b> lost<extra></extra>' },
    { x: x.slice(1), y: S.net_new_mrr.slice(1), name: 'Net new', type: 'scatter', mode: 'markers',
      marker: { color: css('--total'), size: 7, line: { color: css('--surface-1'), width: 2 } },
      hovertemplate: '<b>%{y:$,.0f}</b> net new<extra></extra>' }],
    baseLayout({ barmode: 'relative', bargap: 0.45, hovermode: 'x unified', showlegend: true,
      legend: { orientation: 'h', x: 0, y: 1.12, font: { color: css('--text-secondary') } },
      yaxis: Object.assign(baseLayout().yaxis, { tickformat: '$~s' }) }), CFG);

  // Churn
  Plotly.react('c-churn', [{ x: x.slice(1), y: S.logo_churn_pct.slice(1), type: 'scatter', mode: 'lines',
    line: { color: css('--series-1'), width: 2 }, hovertemplate: '<b>%{y:.2f}%</b><br>%{x|%b %Y}<extra></extra>' }],
    baseLayout({ hovermode: 'x', yaxis: Object.assign(baseLayout().yaxis, { ticksuffix: '%', rangemode: 'tozero' }),
      annotations: [
        { x: '2024-07-01', y: S.logo_churn_pct[S.months.indexOf('2024-07')], text: 'Starter price increase',
          showarrow: true, arrowcolor: css('--muted'), ax: -60, ay: -26, font: { size: 11, color: css('--text-secondary') } },
        { x: '2025-03-01', y: S.logo_churn_pct[S.months.indexOf('2025-03')], text: 'Card payment failures',
          showarrow: true, arrowcolor: css('--muted'), ax: -70, ay: -18, font: { size: 11, color: css('--text-secondary') } }] }), CFG);

  // NRR / GRR
  const from = S.months.indexOf('2024-01');
  Plotly.react('c-ret', [
    { x: x.slice(from), y: S.nrr_t12m_pct.slice(from), name: 'Net revenue retention', type: 'scatter', mode: 'lines',
      line: { color: css('--series-1'), width: 2 }, hovertemplate: '<b>%{y:.1f}%</b> NRR<extra></extra>' },
    { x: x.slice(from), y: S.grr_t12m_pct.slice(from), name: 'Gross revenue retention', type: 'scatter', mode: 'lines',
      line: { color: css('--series-2'), width: 2 }, hovertemplate: '<b>%{y:.1f}%</b> GRR<extra></extra>' }],
    baseLayout({ hovermode: 'x unified', showlegend: true,
      legend: { orientation: 'h', x: 0, y: 1.12, font: { color: css('--text-secondary') } },
      yaxis: Object.assign(baseLayout().yaxis, { ticksuffix: '%' }),
      shapes: [{ type: 'line', xref: 'paper', x0: 0, x1: 1, y0: 100, y1: 100, line: { color: css('--axis'), width: 1 } }] }), CFG);

  // Cohorts
  const C = DATA.cohorts[seg];
  const ramp = css('--ramp').replace(/"/g, '').split(',');
  const scale = ramp.map((c, i) => [i / (ramp.length - 1), c]);
  Plotly.react('c-coh', [{ type: 'heatmap', z: C.z, x: C.cols, y: C.cohorts, zmin: 40, zmax: 100,
    colorscale: scale, showscale: false, xgap: 2, ygap: 2, texttemplate: '%{z:.0f}', textfont: { size: 11 },
    hovertemplate: '<b>%{z:.1f}%</b> still paying<br>%{y} cohort, %{x}<extra></extra>' }],
    baseLayout({ margin: { l: 64, r: 12, t: 30, b: 8 }, yaxis: { autorange: 'reversed', ticks: '', showgrid: false },
      xaxis: { side: 'top', ticks: '', showgrid: false } }), CFG);

  // Table view
  const cols = [['months', 'Month'], ['mrr', 'MRR'], ['paying_accounts', 'Paying accounts'], ['new_mrr', 'New'],
    ['expansion_mrr', 'Expansion'], ['contraction_mrr', 'Contraction'], ['churned_mrr', 'Churned'],
    ['logo_churn_pct', 'Logo churn'], ['nrr_t12m_pct', 'NRR 12m']];
  const table = document.createElement('table');
  const head = table.insertRow();
  cols.forEach(([, h]) => { const th = document.createElement('th'); th.textContent = h; head.appendChild(th); });
  for (let i = last; i >= 0; i--) {
    const r = table.insertRow();
    cols.forEach(([k]) => { const c = r.insertCell(); const v = S[k][i];
      c.textContent = k === 'months' ? label(v) : k.endsWith('_pct') ? fmtPct(v)
        : k === 'paying_accounts' ? v.toLocaleString('en-US') : fmtMoney(v); });
  }
  document.getElementById('table').replaceChildren(table);
}
document.getElementById('seg').addEventListener('change', render);
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', render);
render();
</script>
</body>
</html>
"""


def main():
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "moonlit-data/saas-subscription-dashboard"
    OUT.parent.mkdir(exist_ok=True)
    html = PAGE.replace("__DATA__", json.dumps(build_data(), separators=(",", ":"))).replace("__REPO__", repo)
    OUT.write_text(html, encoding="utf-8")
    (OUT.parent / ".nojekyll").write_text("", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
