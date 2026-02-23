"""Generate the full Ramadan Timing HTML dashboard."""

import os
from datetime import date
from typing import List, Dict, Optional, Tuple

from config import EXPERIMENT_NAME, FUNNEL_STEPS, RAMADAN_START, CITY_BUCKETS
from funnel import (
    FunnelMetrics, PeriodInfo, TimeBucketMetrics, WindowComparison,
    ProductivityMetrics, HourCell, WeekMetrics, DailyCredibility,
    wilson_ci, ambassador_breakdown,
    PRE_DAY_ONB, PRE_DAY_VISITS, PRE_NIGHT_ONB, PRE_NIGHT_VISITS,
)

CSS = """\
  :root {
    --zar-gold: #B8992E;
    --zar-gold-light: #CBAF4A;
    --zar-gold-dark: #9A7E24;
    --zar-sky-blue: #7BC4E8;
    --background: #F5F0E8;
    --card: #FFFFFF;
    --border: #E8E3DB;
    --text: #1A1A1A;
    --text-secondary: #6B6B6B;
    --success: #16a34a;
    --danger: #dc2626;
    --warning: #d97706;
    --night-bg: #1e293b;
    --night-text: #e2e8f0;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--background);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30px;
    color: var(--text);
  }
  h1 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 6px;
  }
  .subtitle {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 30px;
    text-align: center;
  }

  /* Stat grid (headline cards) */
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
    width: 100%;
  }
  .stat-box {
    background: var(--background);
    padding: 1rem;
    border-radius: 12px;
    text-align: center;
  }
  .stat-value {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--zar-gold-dark);
  }
  .stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
  }
  .stat-sub {
    font-size: 0.7rem;
    color: var(--text-secondary);
    margin-top: 2px;
  }

  /* Data cards */
  .data-card {
    margin-top: 24px;
    background: var(--card);
    border-radius: 20px;
    padding: 1.5rem 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid var(--border);
    width: 1020px;
  }
  .data-card h2 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .data-card h2 .num {
    background: linear-gradient(135deg, var(--zar-gold), var(--zar-gold-light));
    color: white;
    width: 26px;
    height: 26px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 600;
  }
  .data-card .period-info {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-bottom: 16px;
  }
  .data-card table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }
  .data-card th {
    padding: 0.6rem 0.75rem;
    text-align: left;
    color: var(--text-secondary);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid var(--border);
  }
  .data-card th.num-col { text-align: right; }
  .data-card td {
    padding: 0.6rem 0.75rem;
    color: var(--text);
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  .data-card td.num-col {
    text-align: right;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
  }
  .data-card tr:last-child td { border-bottom: none; }
  .data-card tr.total-row td {
    font-weight: 700;
    background: rgba(184,153,46,0.08);
    border-bottom: none;
  }
  .delta-pos { color: var(--success); font-weight: 600; }
  .delta-neg { color: var(--danger); font-weight: 600; }
  .delta-zero { color: var(--text-secondary); }

  .badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 600;
  }
  .badge-success { background: rgba(22,163,74,0.15); color: #16a34a; }
  .badge-warning { background: rgba(184,153,46,0.15); color: var(--zar-gold-dark); }
  .badge-danger  { background: rgba(220,38,38,0.15); color: #dc2626; }
  .badge-night   { background: rgba(30,41,59,0.15); color: #334155; }

  .insight {
    background: linear-gradient(135deg, rgba(184,153,46,0.08), rgba(184,153,46,0.02));
    border-left: 3px solid var(--zar-gold);
    padding: 1rem;
    margin-top: 1rem;
    font-size: 0.85rem;
    border-radius: 0 12px 12px 0;
  }
  .insight strong { color: var(--zar-gold-dark); }

  /* Window comparison side-by-side */
  .window-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1rem;
  }
  .window-box {
    padding: 1.25rem;
    border-radius: 12px;
    text-align: center;
  }
  .window-day { background: #FEF3C7; border: 1px solid #F59E0B; }
  .window-evening { background: #FED7AA; border: 1px solid #EA580C; }
  .window-night { background: #1e293b; border: 1px solid #475569; color: #e2e8f0; }
  .window-night .stat-label { color: #94a3b8; }

  /* Heatmap */
  .heatmap-grid {
    display: grid;
    gap: 2px;
    font-size: 0.7rem;
  }
  .hm-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4px 2px;
    border-radius: 4px;
    min-width: 44px;
    min-height: 36px;
  }
  .hm-rate {
    font-weight: 700;
    font-size: 0.75rem;
  }
  .hm-n {
    font-size: 0.6rem;
    opacity: 0.7;
  }

  /* Bucket bars */
  .bucket-bar-container {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .bucket-bar {
    height: 20px;
    border-radius: 4px;
    min-width: 2px;
  }

  /* Fatigue / hour chart */
  .hour-chart {
    display: flex;
    align-items: flex-end;
    gap: 4px;
    height: 140px;
    padding-top: 20px;
  }
  .hour-bar-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
  }
  .hour-bar {
    width: 100%;
    border-radius: 4px 4px 0 0;
    min-height: 2px;
  }
  .hour-label {
    font-size: 0.65rem;
    color: var(--text-secondary);
    margin-top: 4px;
  }
  .hour-pct {
    font-size: 0.65rem;
    font-weight: 600;
    margin-bottom: 2px;
  }

  .section-heading {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text);
    margin: 1.25rem 0 0.75rem;
  }

  .legend-row {
    display: flex;
    gap: 1.25rem;
    margin-top: 0.75rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
  .legend-row span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .legend-swatch {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 4px;
  }

  .rate-bar {
    display: inline-block;
    height: 8px;
    border-radius: 4px;
    vertical-align: middle;
  }
"""


def _sig2(val: float) -> str:
    """Format a number to 2 significant digits."""
    s = f"{val:.2g}"
    return s if 'e' not in s else f"{val:.0f}"


def _pct(n: int, d: int) -> str:
    return f"{_sig2(n / d * 100)}%" if d else "\u2013"


def _conv_rate(count: int, total: int) -> Optional[float]:
    return count / total * 100 if total else None


def _fmt(rate: Optional[float]) -> str:
    return f"{_sig2(rate)}%" if rate is not None else "\u2014"


def _fmt_delta_html(base: Optional[float], expt: Optional[float]) -> str:
    if base is None or expt is None:
        return '<span class="delta-zero">\u2014</span>'
    d = expt - base
    if abs(d) < 0.05:
        return '<span class="delta-zero">0</span>'
    sign = "+" if d >= 0 else ""
    cls = "delta-pos" if d > 0 else "delta-neg"
    return f'<span class="{cls}">{sign}{_sig2(d)}pp</span>'


def _e2e_badge(rate: Optional[float]) -> str:
    if rate is None:
        return ""
    if rate >= 10:
        cls = "badge-success"
    elif rate >= 5:
        cls = "badge-warning"
    else:
        cls = "badge-danger"
    return f' <span class="badge {cls}">{_sig2(rate)}%</span>'


def _tier_badge(tier: str) -> str:
    cls = {"Reliable": "badge-success", "Directional": "badge-warning",
           "Insufficient": "badge-danger"}.get(tier, "")
    return f'<span class="badge {cls}">{tier}</span>'


def _hm_bg(rate: Optional[float]) -> str:
    if rate is None:
        return "#e5e5e5"
    if rate >= 15:
        return "#16a34a"
    if rate >= 5:
        return "#B8992E"
    if rate > 0:
        return "#d97706"
    return "#dc2626"


def _hm_fg(rate: Optional[float]) -> str:
    if rate is None:
        return "#999"
    return "#fff"


def _bar_color(rate: Optional[float]) -> str:
    if rate is None:
        return "#ccc"
    if rate >= 10:
        return "var(--success)"
    if rate >= 5:
        return "var(--zar-gold)"
    return "var(--danger)"


def _fmt_hour(h: Optional[float]) -> str:
    if h is None:
        return "\u2014"
    hour = int(h)
    minute = int((h - hour) * 60)
    suffix = "am" if hour < 12 else "pm"
    display_h = hour if hour <= 12 else hour - 12
    if display_h == 0:
        display_h = 12
    if minute == 0:
        return f"{display_h}{suffix}"
    return f"{display_h}:{minute:02d}{suffix}"


# ── Card 0: Headline stats ────────────────────────────────────────

def _build_headline_card(base_m: FunnelMetrics, ram_m: FunnelMetrics,
                         base_info: PeriodInfo, ram_info: PeriodInfo) -> str:
    # Compute deltas
    ram_vpd = ram_m.visits / ram_info.num_days if ram_info.num_days else 0
    base_vpd = base_m.visits / base_info.num_days if base_info.num_days else 0
    ram_opd = ram_m.onboardings / ram_info.num_days if ram_info.num_days else 0
    base_opd = base_m.onboardings / base_info.num_days if base_info.num_days else 0
    ram_e2e = ram_m.e2e_rate() or 0
    base_e2e = base_m.e2e_rate() or 0

    ramadan_day = (date.today() - RAMADAN_START).days + 1

    def _delta_sub(ram_val, base_val, suffix=""):
        d = ram_val - base_val
        if abs(d) < 0.05:
            return f'<div class="stat-sub">&mdash; vs pre-Ramadan</div>'
        sign = "+" if d >= 0 else ""
        color = "var(--success)" if d > 0 else "var(--danger)"
        return f'<div class="stat-sub" style="color:{color}">{sign}{_sig2(d)}{suffix} vs pre-Ramadan</div>'

    return f"""\
<div class="data-card">
  <div class="stat-grid">
    <div class="stat-box">
      <div class="stat-label">Ramadan Day</div>
      <div class="stat-value">{ramadan_day}</div>
      <div class="stat-sub">{ram_info.num_days} day{"s" if ram_info.num_days != 1 else ""} of data</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Visits / Day</div>
      <div class="stat-value">{_sig2(ram_vpd)}</div>
      {_delta_sub(ram_vpd, base_vpd)}
    </div>
    <div class="stat-box">
      <div class="stat-label">Onboardings / Day</div>
      <div class="stat-value">{_sig2(ram_opd)}</div>
      {_delta_sub(ram_opd, base_opd)}
    </div>
    <div class="stat-box">
      <div class="stat-label">E2E Rate</div>
      <div class="stat-value">{_sig2(ram_e2e)}%</div>
      {_delta_sub(ram_e2e, base_e2e, "pp")}
    </div>
  </div>
</div>"""


# ── Card 1: Period comparison ──────────────────────────────────────

def _build_comparison_card(base_m: FunnelMetrics, ram_m: FunnelMetrics,
                           base_info: PeriodInfo, ram_info: PeriodInfo) -> str:
    base_d, ram_d = base_m.as_dict(), ram_m.as_dict()
    base_conv, ram_conv = base_m.step_conversions(), ram_m.step_conversions()

    rows_html = []
    for step in FUNNEL_STEPS:
        b, r = base_d[step], ram_d[step]
        bc = _fmt(base_conv[step])
        rc = _fmt(ram_conv[step])
        delta = _fmt_delta_html(base_conv[step], ram_conv[step])
        rows_html.append(
            f'      <tr><td>{step}</td>'
            f'<td class="num-col">{b}</td><td class="num-col">{bc}</td>'
            f'<td class="num-col">{r}</td><td class="num-col">{rc}</td>'
            f'<td class="num-col">{delta}</td></tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">1</span> Pre-Ramadan vs Ramadan</h2>
  <div class="period-info">
    Pre-Ramadan: {base_info.range_str} ({base_info.num_days} days) &middot;
    Ramadan: {ram_info.range_str} ({ram_info.num_days} day{"s" if ram_info.num_days != 1 else ""})
  </div>
  <table>
    <thead><tr>
      <th>Step</th>
      <th class="num-col">Pre #</th><th class="num-col">Pre Conv</th>
      <th class="num-col">Ram #</th><th class="num-col">Ram Conv</th>
      <th class="num-col">&Delta;</th>
    </tr></thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


# ── Card 2: Day vs Night window ───────────────────────────────────

def _build_window_card(wc: WindowComparison) -> str:
    dm, em, nm = wc.day_metrics, wc.evening_metrics, wc.night_metrics
    p = wc.p_night_better_than_day

    def _window_stat(m: FunnelMetrics) -> Tuple[str, str, str]:
        e2e = _fmt(m.e2e_rate())
        ci = wilson_ci(m.onboardings, m.visits)
        ci_str = f"[{_sig2(ci[0])}, {_sig2(ci[1])}]" if m.visits else "\u2014"
        return e2e, str(m.visits), ci_str

    d_e2e, d_n, d_ci = _window_stat(dm)
    e_e2e, e_n, e_ci = _window_stat(em)
    n_e2e, n_n, n_ci = _window_stat(nm)

    p_prior = wc.p_night_better_with_prior
    p_base = wc.p_vs_pre_ramadan_baseline

    # Credibility label (use informed prior as primary)
    if p_prior >= 0.95:
        cred_label = "Strong evidence"
        cred_color = "var(--success)"
    elif p_prior >= 0.80:
        cred_label = "Likely"
        cred_color = "var(--zar-gold)"
    else:
        cred_label = "Directional"
        cred_color = "var(--text-secondary)"

    return f"""\
<div class="data-card">
  <h2><span class="num">2</span> Day vs Night Window</h2>
  <div class="period-info">Daytime (&lt;Iftar) vs Evening Transition vs Nighttime (&gt;Taraweeh)</div>
  <div class="window-grid">
    <div class="window-box window-day">
      <div class="stat-label">Daytime (&lt;Iftar)</div>
      <div class="stat-value" style="color:var(--warning)">{d_e2e}</div>
      <div class="stat-sub">{d_n} visits &middot; CI {d_ci}</div>
    </div>
    <div class="window-box window-evening">
      <div class="stat-label">Evening Transition</div>
      <div class="stat-value" style="color:#ea580c">{e_e2e}</div>
      <div class="stat-sub">{e_n} visits &middot; CI {e_ci}</div>
    </div>
    <div class="window-box window-night">
      <div class="stat-label" style="color:#94a3b8">Nighttime (&gt;Taraweeh)</div>
      <div class="stat-value" style="color:#60a5fa">{n_e2e}</div>
      <div class="stat-sub" style="color:#94a3b8">{n_n} visits &middot; CI {n_ci}</div>
    </div>
  </div>
  <div class="insight">
    <strong>P(Night &gt; Day) with prior = {p_prior:.0%}</strong> &mdash; {cred_label}
    <span style="color:{cred_color}">&#9679;</span>
    <br><span style="font-size:0.8rem; color:var(--text-secondary);">
      Without prior: {p:.0%} &middot; P(Night &ge; pre-Ram evening): {p_base:.0%}
    </span>
  </div>
</div>"""


# ── Card 3: Hourly heatmap / fatigue curve ─────────────────────────

def _build_heatmap_card(heatmap: Dict[str, Dict[int, HourCell]],
                        totals: Dict[int, HourCell]) -> str:
    hours = list(range(9, 24))
    ambassadors = sorted(heatmap.keys())

    # Hour bar chart (totals)
    max_visits = max((totals.get(h, HourCell()).visits for h in hours), default=1) or 1
    bar_html = []
    for h in hours:
        cell = totals.get(h, HourCell())
        e2e = cell.e2e_rate
        bar_h = max(2, int(cell.visits / max_visits * 120))
        color = _bar_color(e2e)
        pct_str = f"{_sig2(e2e)}%" if e2e is not None else "\u2013"
        suffix = "am" if h < 12 else "pm"
        h_label = h if h <= 12 else h - 12
        bar_html.append(
            f'<div class="hour-bar-wrap">'
            f'<div class="hour-pct" style="color:{color}">{pct_str}</div>'
            f'<div class="hour-bar" style="height:{bar_h}px; background:{color};"></div>'
            f'<div class="hour-label">{h_label}{suffix}</div>'
            f'<div class="hour-label" style="font-weight:600">{cell.visits}</div>'
            f'</div>'
        )

    # Ambassador x hour grid
    grid_rows = []
    for amb in ambassadors:
        cells = f'<td><strong>{amb}</strong></td>'
        for h in hours:
            cell = heatmap.get(amb, {}).get(h, HourCell())
            if cell.visits > 0:
                bg = _hm_bg(cell.e2e_rate)
                fg = _hm_fg(cell.e2e_rate)
                e2e_str = f"{_sig2(cell.e2e_rate)}%" if cell.e2e_rate is not None else "0%"
                cells += (
                    f'<td style="text-align:center; padding:2px;">'
                    f'<div class="hm-cell" style="background:{bg}; color:{fg};">'
                    f'<div class="hm-rate">{e2e_str}</div>'
                    f'<div class="hm-n">n={cell.visits}</div>'
                    f'</div></td>'
                )
            else:
                cells += '<td style="text-align:center; padding:2px;"><div class="hm-cell" style="background:#f5f5f5; color:#ccc;"><div class="hm-rate">&mdash;</div></div></td>'
        grid_rows.append(f'      <tr>{cells}</tr>')

    hour_headers = "".join(
        f'<th style="text-align:center; min-width:44px;">{h if h <= 12 else h - 12}{"am" if h < 12 else "pm"}</th>'
        for h in hours
    )

    return f"""\
<div class="data-card">
  <h2><span class="num">3</span> Hourly Conversion &amp; Heatmap</h2>
  <div class="period-info">E2E rate by hour &middot; bar height = visit volume, color = conversion rate</div>

  <div class="hour-chart">
    {"".join(bar_html)}
  </div>

  <div class="section-heading">Ambassador &times; Hour Heatmap</div>
  <div style="overflow-x:auto;">
  <table style="font-size:0.75rem;">
    <thead><tr><th>Ambassador</th>{hour_headers}</tr></thead>
    <tbody>
{chr(10).join(grid_rows)}
    </tbody>
  </table>
  </div>

  <div class="legend-row">
    <span><span class="legend-swatch" style="background:#16a34a;"></span> &ge;15% E2E</span>
    <span><span class="legend-swatch" style="background:#B8992E;"></span> 5&ndash;14%</span>
    <span><span class="legend-swatch" style="background:#d97706;"></span> 1&ndash;4%</span>
    <span><span class="legend-swatch" style="background:#dc2626;"></span> 0%</span>
    <span><span class="legend-swatch" style="background:#e5e5e5;"></span> No visits</span>
  </div>
</div>"""


# ── Card 4: Time bucket bars ──────────────────────────────────────

def _build_bucket_card(ram_buckets: List[TimeBucketMetrics],
                       pre_buckets: List[TimeBucketMetrics],
                       city: str) -> str:
    # Build pre-Ramadan lookup
    pre_map = {b.bucket_name: b for b in pre_buckets}
    max_visits = max((b.visits for b in ram_buckets), default=1) or 1

    rows_html = []
    for b in ram_buckets:
        bar_w = max(2, int(b.visits / max_visits * 200))
        color = _bar_color(b.e2e_rate)
        ci = b.e2e_ci()
        ci_str = f"[{_sig2(ci[0])}, {_sig2(ci[1])}]" if b.visits > 0 else "\u2014"

        # Pre-Ramadan comparison
        pre_b = pre_map.get(b.bucket_name)
        pre_e2e = pre_b.e2e_rate if pre_b else None
        delta = _fmt_delta_html(pre_e2e, b.e2e_rate)

        rows_html.append(
            f'      <tr><td>{b.bucket_name}</td>'
            f'<td class="num-col">{b.visits}</td>'
            f'<td><div class="bucket-bar-container">'
            f'<div class="bucket-bar" style="width:{bar_w}px; background:{color};"></div>'
            f'</div></td>'
            f'<td class="num-col">{_fmt(b.opener_rate)}</td>'
            f'<td class="num-col">{_fmt(b.demo_rate)}</td>'
            f'<td class="num-col">{_fmt(b.e2e_rate)}</td>'
            f'<td class="num-col" style="font-size:0.75rem;">{ci_str}</td>'
            f'<td class="num-col">{_fmt(pre_e2e)}</td>'
            f'<td class="num-col">{delta}</td>'
            f'</tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">4</span> Time Bucket Breakdown &mdash; {city}</h2>
  <div class="period-info">Ramadan conversion by time bucket, with pre-Ramadan overlay</div>
  <table>
    <thead><tr>
      <th>Bucket</th>
      <th class="num-col">Visits</th>
      <th>Volume</th>
      <th class="num-col">Opener%</th>
      <th class="num-col">Demo%</th>
      <th class="num-col">E2E%</th>
      <th class="num-col">95% CI</th>
      <th class="num-col">Pre-Ram E2E</th>
      <th class="num-col">&Delta;</th>
    </tr></thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


# ── Card 5: City comparison ───────────────────────────────────────

def _build_city_card(city_metrics: Dict[str, FunnelMetrics]) -> str:
    if len(city_metrics) < 2:
        return ""

    rows_html = []
    for city, m in sorted(city_metrics.items()):
        e2e = m.e2e_rate()
        ci = wilson_ci(m.onboardings, m.visits)
        ci_str = f"[{_sig2(ci[0])}, {_sig2(ci[1])}]" if m.visits else "\u2014"
        rows_html.append(
            f'      <tr><td>{city}</td>'
            f'<td class="num-col">{m.visits}</td>'
            f'<td class="num-col">{_fmt(_conv_rate(m.opener_passed, m.visits))}</td>'
            f'<td class="num-col">{_fmt(_conv_rate(m.demos, m.visits))}</td>'
            f'<td class="num-col">{m.onboardings}</td>'
            f'<td class="num-col">{_fmt(e2e)}{_e2e_badge(e2e)}</td>'
            f'<td class="num-col" style="font-size:0.75rem;">{ci_str}</td>'
            f'</tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">5</span> City Comparison</h2>
  <div class="period-info">Karachi (Iftar 6:28pm) vs Lahore (Iftar 5:53pm) &mdash; natural quasi-experiment</div>
  <table>
    <thead><tr>
      <th>City</th>
      <th class="num-col">Visits</th>
      <th class="num-col">Opener%</th>
      <th class="num-col">Demo%</th>
      <th class="num-col">Onboards</th>
      <th class="num-col">E2E%</th>
      <th class="num-col">95% CI</th>
    </tr></thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


# ── Card 6: Ambassador table ──────────────────────────────────────

def _build_ambassador_card(prods: List[ProductivityMetrics],
                           amb_funnel: List[Tuple[str, FunnelMetrics]],
                           info: PeriodInfo) -> str:
    funnel_map = {name: m for name, m in amb_funnel}

    rows_html = []
    for p in prods:
        fm = funnel_map.get(p.ambassador)
        e2e = fm.e2e_rate() if fm else None
        vpd = f"{p.visits_per_day:.1f}" if p.visits_per_day else "\u2014"
        opd = f"{p.onboards_per_day:.1f}" if p.onboards_per_day else "\u2014"
        fh = _fmt_hour(p.first_hour)
        lh = _fmt_hour(p.last_hour)
        ah = f"{p.active_hours:.1f}h" if p.active_hours else "\u2014"
        pref_badge = ""
        if p.preference == "Night":
            pref_badge = '<span class="badge badge-night">Night</span>'
        elif p.preference == "Day":
            pref_badge = '<span class="badge badge-warning">Day</span>'
        else:
            pref_badge = f'<span class="badge" style="background:#e5e5e5; color:#666;">{p.preference}</span>'

        rows_html.append(
            f'      <tr><td>{p.ambassador}</td>'
            f'<td>{p.city}</td>'
            f'<td class="num-col">{p.visits}</td>'
            f'<td class="num-col">{p.onboardings}</td>'
            f'<td class="num-col">{vpd}</td>'
            f'<td class="num-col">{opd}</td>'
            f'<td class="num-col">{_fmt(e2e)}{_e2e_badge(e2e)}</td>'
            f'<td class="num-col">{fh}</td>'
            f'<td class="num-col">{lh}</td>'
            f'<td class="num-col">{ah}</td>'
            f'<td>{pref_badge}</td>'
            f'<td>{_tier_badge(p.tier)}</td>'
            f'</tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">6</span> Ambassador Summary</h2>
  <div class="period-info">
    {info.range_str} ({info.num_days} day{"s" if info.num_days != 1 else ""})
  </div>
  <div style="overflow-x:auto;">
  <table style="font-size:0.8rem;">
    <thead><tr>
      <th>Ambassador</th>
      <th>City</th>
      <th class="num-col">Visits</th>
      <th class="num-col">Onb</th>
      <th class="num-col">V/day</th>
      <th class="num-col">O/day</th>
      <th class="num-col">E2E%</th>
      <th class="num-col">1st Hr</th>
      <th class="num-col">Last Hr</th>
      <th class="num-col">Active</th>
      <th>Pref</th>
      <th>Tier</th>
    </tr></thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
  </div>
</div>"""


# ── Card 7: Weekly trend ──────────────────────────────────────────

def _build_weekly_card(weeks: List[WeekMetrics]) -> str:
    if not weeks:
        return ""

    rows_html = []
    for w in weeks:
        dates = f"{w.start_date.strftime('%b %d')}\u2013{w.end_date.strftime('%d')}"
        vpd = f"{w.visits_per_day:.1f}" if w.visits_per_day else "\u2014"
        opd = f"{w.onboards_per_day:.1f}" if w.onboards_per_day else "\u2014"
        e2e = w.e2e_rate
        rows_html.append(
            f'      <tr><td>Week {w.week_num}</td>'
            f'<td>{dates}</td>'
            f'<td class="num-col">{w.num_days}</td>'
            f'<td class="num-col">{w.visits}</td>'
            f'<td class="num-col">{w.onboardings}</td>'
            f'<td class="num-col">{vpd}</td>'
            f'<td class="num-col">{opd}</td>'
            f'<td class="num-col">{_fmt(e2e)}{_e2e_badge(e2e)}</td>'
            f'</tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">7</span> Weekly Trend (Cumulative Fatigue Tracking)</h2>
  <div class="period-info">Week = 7-day block from Ramadan start</div>
  <table>
    <thead><tr>
      <th>Week</th>
      <th>Dates</th>
      <th class="num-col">Days</th>
      <th class="num-col">Visits</th>
      <th class="num-col">Onboards</th>
      <th class="num-col">V/day</th>
      <th class="num-col">O/day</th>
      <th class="num-col">E2E%</th>
    </tr></thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


# ── Card 8: Data quality (batch logging) ──────────────────────────

def _build_data_quality_card(flags: List[dict]) -> str:
    if not flags:
        return f"""\
<div class="data-card">
  <h2><span class="num">8</span> Data Quality</h2>
  <div class="insight" style="border-left-color:var(--success);">
    <strong style="color:var(--success);">&#10004; No batch-logging flags detected.</strong>
  </div>
</div>"""

    rows_html = []
    for f in flags:
        d_str = f["date"].strftime("%b %d")
        ts_str = ", ".join(f["timestamps"])
        rows_html.append(
            f'      <tr><td>{f["ambassador"]}</td>'
            f'<td>{d_str}</td>'
            f'<td class="num-col">{f["count"]}</td>'
            f'<td style="font-size:0.75rem;">{ts_str}</td>'
            f'</tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">8</span> Data Quality</h2>
  <div class="period-info">&#9888; {len(flags)} batch-logging cluster{"s" if len(flags) != 1 else ""} detected (3+ visits within 5 min)</div>
  <table>
    <thead><tr>
      <th>Ambassador</th>
      <th>Date</th>
      <th class="num-col">Count</th>
      <th>Timestamps</th>
    </tr></thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
  <div class="insight" style="border-left-color:var(--danger);">
    <strong style="color:var(--danger);">Action:</strong> Qasim to verify these clusters &mdash;
    are they real rapid visits or batch-logged at end of day?
  </div>
</div>"""


# ── Card 9: Sequential credibility monitor ────────────────────────

def _build_sequential_card(trajectory: List[DailyCredibility],
                           est_days: Optional[int]) -> str:
    if not trajectory:
        return f"""\
<div class="data-card">
  <h2><span class="num">9</span> Sequential Credibility Monitor</h2>
  <div class="period-info">Tracking P(Night &gt; Day) as Ramadan data accumulates — using pre-Ramadan informative priors</div>
  <div class="insight" style="border-left-color:var(--text-secondary);">
    <strong>No Ramadan data yet.</strong> Monitor will populate as visits are recorded.
  </div>
</div>"""

    latest = trajectory[-1]
    p = latest.p_with_prior
    p_flat = latest.p_uninformative

    # Headline badge
    if p >= 0.95:
        badge_bg = "rgba(22,163,74,0.15)"
        badge_color = "#16a34a"
        badge_text = "Strong ✓"
    elif p >= 0.80:
        badge_bg = "rgba(184,153,46,0.15)"
        badge_color = "var(--zar-gold-dark)"
        badge_text = "Likely"
    else:
        badge_bg = "rgba(107,107,107,0.1)"
        badge_color = "var(--text-secondary)"
        badge_text = "Directional"

    # Estimate text
    if est_days is not None and est_days == 0:
        est_html = '<span style="color:var(--success); font-weight:600;">Already credible ✓</span>'
    elif est_days is not None:
        est_html = f'<span style="color:var(--zar-gold-dark); font-weight:600;">~{est_days} more day{"s" if est_days != 1 else ""} at current rate</span>'
    else:
        est_html = '<span style="color:var(--text-secondary);">Insufficient data to estimate</span>'

    # Daily trajectory table rows
    traj_rows = []
    for dc in trajectory:
        day_str = dc.day.strftime("%b %d")
        v_class = "badge-success" if dc.verdict == "Strong" else \
                  "badge-warning" if dc.verdict == "Likely" else ""
        verdict_badge = f'<span class="badge {v_class}">{dc.verdict}{"" if dc.verdict != "Strong" else " ✓"}</span>'
        traj_rows.append(
            f'      <tr>'
            f'<td>{day_str}</td>'
            f'<td class="num-col">{dc.cum_day_visits}</td>'
            f'<td class="num-col">{dc.cum_day_onb}</td>'
            f'<td class="num-col">{dc.cum_night_visits}</td>'
            f'<td class="num-col">{dc.cum_night_onb}</td>'
            f'<td class="num-col" style="font-weight:700;">{dc.p_with_prior:.0%}</td>'
            f'<td class="num-col" style="color:var(--text-secondary);">{dc.p_uninformative:.0%}</td>'
            f'<td class="num-col">{dc.p_vs_baseline:.0%}</td>'
            f'<td>{verdict_badge}</td>'
            f'</tr>'
        )

    # Prior info
    pre_day_rate = PRE_DAY_ONB / PRE_DAY_VISITS * 100
    pre_night_rate = PRE_NIGHT_ONB / PRE_NIGHT_VISITS * 100

    return f"""\
<div class="data-card">
  <h2><span class="num">9</span> Sequential Credibility Monitor</h2>
  <div class="period-info">
    Tracking P(Night &gt; Day) as Ramadan data accumulates &mdash;
    prior: {PRE_DAY_VISITS} daytime visits ({_sig2(pre_day_rate)}% E2E) + {PRE_NIGHT_VISITS} evening visits ({_sig2(pre_night_rate)}% E2E)
  </div>

  <div style="display:flex; gap:1.5rem; margin-bottom:1.25rem; align-items:center;">
    <div style="text-align:center;">
      <div style="font-size:0.75rem; color:var(--text-secondary); margin-bottom:4px;">P(Night &gt; Day) with prior</div>
      <div style="font-size:2.2rem; font-weight:700; font-family:'DM Sans',sans-serif; color:var(--zar-gold-dark);">{p:.0%}</div>
      <span class="badge" style="background:{badge_bg}; color:{badge_color}; font-size:0.8rem;">{badge_text}</span>
    </div>
    <div style="text-align:center;">
      <div style="font-size:0.75rem; color:var(--text-secondary); margin-bottom:4px;">Without prior</div>
      <div style="font-size:1.6rem; font-weight:600; font-family:'DM Sans',sans-serif; color:var(--text-secondary);">{p_flat:.0%}</div>
      <div style="font-size:0.7rem; color:var(--text-secondary);">uniform Beta(1,1)</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:0.75rem; color:var(--text-secondary); margin-bottom:4px;">P(Night &ge; pre-Ram evening)</div>
      <div style="font-size:1.6rem; font-weight:600; font-family:'DM Sans',sans-serif; color:var(--text-secondary);">{latest.p_vs_baseline:.0%}</div>
      <div style="font-size:0.7rem; color:var(--text-secondary);">baseline: {_sig2(pre_night_rate)}% E2E</div>
    </div>
    <div style="flex:1; text-align:right;">
      <div style="font-size:0.75rem; color:var(--text-secondary); margin-bottom:4px;">Days to credibility</div>
      <div>{est_html}</div>
    </div>
  </div>

  <div class="section-heading">Daily P Trajectory</div>
  <table>
    <thead><tr>
      <th>Day</th>
      <th class="num-col">Cum Day V</th>
      <th class="num-col">Day Onb</th>
      <th class="num-col">Cum Night V</th>
      <th class="num-col">Night Onb</th>
      <th class="num-col">P(N&gt;D) prior</th>
      <th class="num-col">P(N&gt;D) flat</th>
      <th class="num-col">P(N&ge;base)</th>
      <th>Verdict</th>
    </tr></thead>
    <tbody>
{chr(10).join(traj_rows)}
    </tbody>
  </table>

  <div class="insight" style="margin-top:1rem; border-left-color:#7BC4E8;">
    <strong style="color:#1e293b;">Stopping rule:</strong>
    Declare when P &gt; 0.95 (Strong) or abandon when P &lt; 0.20 after 5+ days (Futile).
    Prior encodes {PRE_DAY_VISITS + PRE_NIGHT_VISITS} pre-Ramadan visits &mdash;
    expect credible comparison in 3&ndash;5 days vs ~13 without prior.
  </div>
</div>"""


# ── Assemble ───────────────────────────────────────────────────────

def generate_html(
    base_m: FunnelMetrics, ram_m: FunnelMetrics,
    base_info: PeriodInfo, ram_info: PeriodInfo,
    wc: WindowComparison,
    heatmap: Dict[str, Dict[int, HourCell]],
    totals: Dict[int, HourCell],
    ram_buckets: List[TimeBucketMetrics],
    pre_buckets: List[TimeBucketMetrics],
    city: str,
    city_metrics: Dict[str, FunnelMetrics],
    prods: List[ProductivityMetrics],
    amb_funnel: List[Tuple[str, FunnelMetrics]],
    weeks: List[WeekMetrics],
    batch_flags: List[dict],
    trajectory: Optional[List[DailyCredibility]] = None,
    est_days: Optional[int] = None,
) -> str:
    ramadan_day = (date.today() - RAMADAN_START).days + 1

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>EXP-020: {EXPERIMENT_NAME}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{CSS}
</style>
</head>
<body>

<h1>EXP-020: {EXPERIMENT_NAME}</h1>
<div class="subtitle">
  Ramadan Day {ramadan_day} &middot;
  {ram_info.range_str} ({ram_info.num_days} day{"s" if ram_info.num_days != 1 else ""} of data) &middot;
  Phase 1: Observation
</div>

{_build_headline_card(base_m, ram_m, base_info, ram_info)}

{_build_comparison_card(base_m, ram_m, base_info, ram_info)}

{_build_window_card(wc)}

{_build_heatmap_card(heatmap, totals)}

{_build_bucket_card(ram_buckets, pre_buckets, city)}

{_build_city_card(city_metrics)}

{_build_ambassador_card(prods, amb_funnel, ram_info)}

{_build_weekly_card(weeks)}

{_build_data_quality_card(batch_flags)}

{_build_sequential_card(trajectory or [], est_days)}

<div style="margin-top:20px; font-size:0.75rem; color:var(--text-secondary); text-align:center;">
  EXP-020: {EXPERIMENT_NAME} &middot; Generated from live visit form data &middot; Ramadan Day {ramadan_day}
</div>

</body>
</html>
"""


def write_html(html: str) -> str:
    html_path = os.path.join(os.path.dirname(__file__), "ramadan_timing.html")
    with open(html_path, "w") as f:
        f.write(html)
    import sys
    print(f"  Updated dashboard: {html_path}", file=sys.stderr)
    return html_path
