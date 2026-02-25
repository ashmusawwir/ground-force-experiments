"""Generate HTML report — retargeting funnel, comparison, ambassador breakdown."""

import os
from funnel import RetargetingMetrics, PeriodInfo, ambassador_breakdown
from config import EXPERIMENT_NAME

CSS = """\
  :root {
    --zar-gold: #B8992E;
    --zar-gold-light: #CBAF4A;
    --zar-gold-dark: #9A7E24;
    --background: #F5F0E8;
    --card: #FFFFFF;
    --border: #E8E3DB;
    --text: #1A1A1A;
    --text-secondary: #6B6B6B;
    --success: #16a34a;
    --danger: #dc2626;
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
    margin-bottom: 6px;
  }
  .subtitle {
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 30px;
  }
  .data-card {
    margin-top: 20px;
    background: var(--card);
    border-radius: 20px;
    padding: 1.5rem 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid var(--border);
    width: 800px;
  }
  .data-card h2 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .data-card h2 .num {
    background: linear-gradient(135deg, var(--zar-gold), var(--zar-gold-light));
    color: white;
    width: 26px; height: 26px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 600;
  }
  .period-info {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-bottom: 16px;
  }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th {
    padding: 0.6rem 0.75rem;
    text-align: left;
    color: var(--text-secondary);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid var(--border);
  }
  th.num-col { text-align: right; }
  td {
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  td.num-col { text-align: right; font-family: 'DM Sans', sans-serif; font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  tr.total-row td {
    font-weight: 700;
    background: rgba(184,153,46,0.08);
    border-bottom: none;
  }
  .delta-pos { color: var(--success); font-weight: 600; }
  .delta-neg { color: var(--danger); font-weight: 600; }
  .delta-zero { color: var(--text-secondary); }
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  .stat-box {
    background: var(--background);
    padding: 1rem;
    border-radius: 12px;
    text-align: center;
  }
  .stat-value {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.8rem; font-weight: 700;
    color: var(--zar-gold-dark);
  }
  .stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
  }
  .insight {
    background: linear-gradient(135deg, rgba(184,153,46,0.08), rgba(184,153,46,0.02));
    border-left: 3px solid var(--zar-gold);
    padding: 1rem;
    margin-top: 1rem;
    font-size: 0.85rem;
    border-radius: 0 12px 12px 0;
  }
  .insight strong { color: var(--zar-gold-dark); }
  .badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 100px;
    font-size: 0.7rem; font-weight: 600;
  }
  .badge-success { background: rgba(22,163,74,0.15); color: #16a34a; }
  .badge-warning { background: rgba(184,153,46,0.15); color: var(--zar-gold-dark); }
  .badge-danger  { background: rgba(220,38,38,0.15); color: #dc2626; }
  .rate-bar {
    display: inline-block;
    height: 8px;
    border-radius: 4px;
    vertical-align: middle;
  }
  footer {
    margin-top: 30px;
    font-size: 0.75rem;
    color: var(--text-secondary);
  }"""


def _sig2(val):
    s = f"{val:.2g}"
    return s if 'e' not in s else f"{val:.0f}"


def _fmt(rate):
    return f"{_sig2(rate)}%" if rate is not None else "\u2014"


def _rate_color(rate):
    if rate is None:
        return "var(--text-secondary)"
    if rate >= 50:
        return "var(--success)"
    if rate < 20:
        return "var(--danger)"
    return "var(--zar-gold-dark)"


def _rate_badge(rate):
    if rate is None:
        return ""
    if rate >= 50:
        cls = "badge-success"
    elif rate >= 20:
        cls = "badge-warning"
    else:
        cls = "badge-danger"
    return f' <span class="badge {cls}">{_sig2(rate)}%</span>'


def _build_scorecard(metrics, info, total_onb, no_phone):
    rt_rate_str = _fmt(metrics.retargeted_rate)
    nrt_rate_str = _fmt(metrics.not_retargeted_rate)
    rt_color = _rate_color(metrics.retargeted_rate)
    nrt_color = _rate_color(metrics.not_retargeted_rate)

    phone_pct = (total_onb - no_phone) / total_onb * 100 if total_onb else 0

    return f"""\
<div class="data-card">
  <h2><span class="num">1</span> Scorecard</h2>
  <div class="period-info">{info.range_str} ({info.num_days} days)</div>
  <div class="stat-grid">
    <div class="stat-box">
      <div class="stat-value">{metrics.total_merchants}</div>
      <div class="stat-label">Unique Merchants</div>
    </div>
    <div class="stat-box">
      <div class="stat-value">{metrics.pool_size}</div>
      <div class="stat-label">Retarget Pool</div>
    </div>
    <div class="stat-box">
      <div class="stat-value" style="color:{rt_color}">{rt_rate_str}</div>
      <div class="stat-label">Retargeted Conv</div>
    </div>
    <div class="stat-box">
      <div class="stat-value" style="color:{nrt_color}">{nrt_rate_str}</div>
      <div class="stat-label">Not-Retargeted Conv</div>
    </div>
  </div>
  <div class="insight">
    <strong>Data quality:</strong> {_sig2(phone_pct)}% of onboarding visits have phone numbers ({total_onb - no_phone}/{total_onb}).
    {f'{no_phone} rows excluded from analysis.' if no_phone else ''}
  </div>
</div>"""


def _build_funnel_card(metrics):
    demo_rate = metrics.demoed / metrics.total_merchants * 100 if metrics.total_merchants else 0
    onb_rate = metrics.onboarded_first / metrics.total_merchants * 100 if metrics.total_merchants else 0
    pool_pct = metrics.pool_size / metrics.total_merchants * 100 if metrics.total_merchants else 0
    rt_pct = metrics.retargeted_count / metrics.pool_size * 100 if metrics.pool_size else 0

    rows = [
        ("Unique merchants (with phone)", metrics.total_merchants, ""),
        ("Demoed on first visit", metrics.demoed, _fmt(demo_rate)),
        ("Onboarded on first visit", metrics.onboarded_first, _fmt(onb_rate)),
        ("Retarget pool", metrics.pool_size, _fmt(pool_pct)),
        ("Retargeted (2+ visit days)", metrics.retargeted_count, _fmt(rt_pct)),
        ("Not retargeted", metrics.not_retargeted_count, ""),
    ]

    rows_html = []
    for label, count, rate in rows:
        is_highlight = label == "Retarget pool"
        cls = ' class="total-row"' if is_highlight else ""
        rows_html.append(
            f'      <tr{cls}><td>{label}</td>'
            f'<td class="num-col">{count}</td>'
            f'<td class="num-col">{rate}</td></tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">2</span> Retargeting Funnel</h2>
  <table>
    <thead>
      <tr>
        <th>Stage</th>
        <th class="num-col">Count</th>
        <th class="num-col">% of Total</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


def _build_comparison_card(metrics):
    rows_html = []

    for label, n, conv, rate in [
        ("Retargeted", metrics.retargeted_count, metrics.retargeted_converted, metrics.retargeted_rate),
        ("Not retargeted", metrics.not_retargeted_count, metrics.not_retargeted_converted, metrics.not_retargeted_rate),
        ("Pool total", metrics.pool_size, metrics.overall_pool_converted, metrics.overall_pool_rate),
    ]:
        is_total = label == "Pool total"
        cls = ' class="total-row"' if is_total else ""
        rows_html.append(
            f'      <tr{cls}><td>{label}</td>'
            f'<td class="num-col">{n}</td>'
            f'<td class="num-col">{conv}</td>'
            f'<td class="num-col">{_fmt(rate)}{_rate_badge(rate)}</td></tr>'
        )

    insight = ""
    if metrics.retargeted_rate is not None and metrics.not_retargeted_rate is not None:
        delta = metrics.retargeted_rate - metrics.not_retargeted_rate
        sign = "+" if delta >= 0 else ""
        direction = "higher" if delta > 0 else "lower" if delta < 0 else "same"
        insight = f"""\
  <div class="insight">
    <strong>Finding:</strong> Retargeted merchants convert at {_fmt(metrics.retargeted_rate)} vs {_fmt(metrics.not_retargeted_rate)} for not-retargeted ({sign}{_sig2(delta)}pp {direction}).
  </div>"""

    return f"""\
<div class="data-card">
  <h2><span class="num">3</span> Conversion Comparison</h2>
  <table>
    <thead>
      <tr>
        <th>Group</th>
        <th class="num-col">N</th>
        <th class="num-col">Converted</th>
        <th class="num-col">Rate</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
{insight}
</div>"""


def _build_ambassador_card(journeys, info):
    amb_data = ambassador_breakdown(journeys)
    if not amb_data:
        return ""

    rows_html = []
    for a in amb_data:
        rt_str = f"{a['rt_converted']}/{a['retargeted']}" if a['retargeted'] else "\u2014"
        nrt_str = f"{a['nrt_converted']}/{a['not_retargeted']}" if a['not_retargeted'] else "\u2014"
        rows_html.append(
            f'      <tr><td>{a["name"]}</td>'
            f'<td class="num-col">{a["pool"]}</td>'
            f'<td class="num-col">{a["retargeted"]}</td>'
            f'<td class="num-col">{rt_str}</td>'
            f'<td class="num-col">{_fmt(a["rt_rate"])}{_rate_badge(a["rt_rate"])}</td>'
            f'<td class="num-col">{nrt_str}</td>'
            f'<td class="num-col">{_fmt(a["nrt_rate"])}</td></tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">4</span> Per-Ambassador Retargeting</h2>
  <div class="period-info">{info.range_str} ({info.num_days} days)</div>
  <table>
    <thead>
      <tr>
        <th>Ambassador</th>
        <th class="num-col">Pool</th>
        <th class="num-col">Retargeted</th>
        <th class="num-col">RT Conv</th>
        <th class="num-col">RT Rate</th>
        <th class="num-col">No-RT Conv</th>
        <th class="num-col">No-RT Rate</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


def _build_timing_card(metrics):
    if not metrics.days_distribution:
        return ""

    buckets = ["1-3 days", "4-7 days", "8-14 days", "15+ days"]
    rows_html = []
    max_count = max(metrics.days_distribution.values()) if metrics.days_distribution else 1
    for bucket in buckets:
        count = metrics.days_distribution.get(bucket, 0)
        if count:
            bar_w = int(count / max_count * 150)
            rows_html.append(
                f'      <tr><td>{bucket}</td>'
                f'<td class="num-col">{count}</td>'
                f'<td><span class="rate-bar" style="width:{bar_w}px; background:var(--zar-gold);"></span></td></tr>'
            )

    if not rows_html:
        return ""

    return f"""\
<div class="data-card">
  <h2><span class="num">5</span> Days to First Revisit</h2>
  <table>
    <thead>
      <tr>
        <th>Bucket</th>
        <th class="num-col">Count</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


def generate_html(metrics, journeys, info, total_onb, no_phone):
    scorecard = _build_scorecard(metrics, info, total_onb, no_phone)
    funnel = _build_funnel_card(metrics)
    comparison = _build_comparison_card(metrics)
    ambassador = _build_ambassador_card(journeys, info)
    timing = _build_timing_card(metrics)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{EXPERIMENT_NAME}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{CSS}
</style>
</head>
<body>

<h1>{EXPERIMENT_NAME}</h1>
<div class="subtitle">Do revisited merchants convert at a higher rate than single-visit merchants?</div>

{scorecard}

{funnel}

{comparison}

{ambassador}

{timing}

<footer>
  Generated from visit form data &middot; EXP-007
</footer>

</body>
</html>
"""


def write_html(metrics, journeys, info, total_onb, no_phone):
    html_path = os.path.join(os.path.dirname(__file__), "post_demo_retargeting.html")
    html = generate_html(metrics, journeys, info, total_onb, no_phone)
    with open(html_path, "w") as f:
        f.write(html)
    import sys
    print(f"  Updated report: {html_path}", file=sys.stderr)
