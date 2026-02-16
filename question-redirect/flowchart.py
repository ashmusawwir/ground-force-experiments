"""Generate HTML report — Q→Demo comparison, per-question conversion, ambassador improvement."""

import os
from typing import List, Tuple, Optional
from funnel import QDemoMetrics, TopicConversion, PeriodInfo, ambassador_q_demo
from config import EXPERIMENT_NAME, BASELINE_Q_DEMO_RATE

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


def _sig2(val: float) -> str:
    s = f"{val:.2g}"
    return s if 'e' not in s else f"{val:.0f}"


def _fmt(rate: Optional[float]) -> str:
    return f"{_sig2(rate)}%" if rate is not None else "\u2014"


def _rate_color(rate: Optional[float]) -> str:
    if rate is None:
        return "var(--text-secondary)"
    if rate >= 50:
        return "var(--success)"
    if rate < 30:
        return "var(--danger)"
    return "var(--zar-gold-dark)"


def _rate_badge(rate: Optional[float]) -> str:
    if rate is None:
        return ""
    if rate >= 50:
        cls = "badge-success"
    elif rate >= 30:
        cls = "badge-warning"
    else:
        cls = "badge-danger"
    return f' <span class="badge {cls}">{_sig2(rate)}%</span>'


def _delta_html(base: Optional[float], expt: Optional[float]) -> str:
    if base is None or expt is None:
        return '<span class="delta-zero">\u2014</span>'
    d = expt - base
    if abs(d) < 0.05:
        return '<span class="delta-zero">0.0</span>'
    sign = "+" if d >= 0 else ""
    cls = "delta-pos" if d > 0 else "delta-neg"
    return f'<span class="{cls}">{sign}{_sig2(d)}pp</span>'


def _build_comparison_card(pre_m: QDemoMetrics, post_m: QDemoMetrics,
                           pre_info: PeriodInfo, post_info: PeriodInfo) -> str:
    pre_rate_str = _fmt(pre_m.q_demo_rate)
    post_rate_str = _fmt(post_m.q_demo_rate)
    pre_color = _rate_color(pre_m.q_demo_rate)
    post_color = _rate_color(post_m.q_demo_rate)

    stat_html = f"""\
  <div class="stat-grid">
    <div class="stat-box">
      <div class="stat-value" style="color:{pre_color}">{pre_rate_str}</div>
      <div class="stat-label">Pre-Training Q\u2192Demo</div>
    </div>
    <div class="stat-box">
      <div class="stat-value" style="color:{post_color}">{post_rate_str}</div>
      <div class="stat-label">Post-Training Q\u2192Demo</div>
    </div>
    <div class="stat-box">
      <div class="stat-value">{pre_m.questions_asked}</div>
      <div class="stat-label">Pre Questions</div>
    </div>
    <div class="stat-box">
      <div class="stat-value">{post_m.questions_asked}</div>
      <div class="stat-label">Post Questions</div>
    </div>
  </div>"""

    rows = [
        ("Visits", pre_m.visits, post_m.visits, None, None),
        ("Opener Passed", pre_m.opener_passed, post_m.opener_passed, None, None),
        ("Questions Asked", pre_m.questions_asked, post_m.questions_asked, None, None),
        ("Converted to Demo", pre_m.converted_to_demo, post_m.converted_to_demo, None, None),
        ("Q\u2192Demo Rate", None, None, pre_m.q_demo_rate, post_m.q_demo_rate),
    ]

    rows_html = []
    for label, pre_n, post_n, pre_r, post_r in rows:
        if pre_r is not None or post_r is not None:
            rows_html.append(
                f'      <tr class="total-row"><td>{label}</td>'
                f'<td class="num-col">{_fmt(pre_r)}</td>'
                f'<td class="num-col">{_fmt(post_r)}</td>'
                f'<td class="num-col">{_delta_html(pre_r, post_r)}</td></tr>'
            )
        else:
            rows_html.append(
                f'      <tr><td>{label}</td>'
                f'<td class="num-col">{pre_n}</td>'
                f'<td class="num-col">{post_n}</td>'
                f'<td class="num-col">\u2014</td></tr>'
            )

    return f"""\
<div class="data-card">
  <h2><span class="num">1</span> Q\u2192Demo Before vs After Training</h2>
  <div class="period-info">
    Pre: {pre_info.range_str} ({pre_info.num_days} days) &middot;
    Post: {post_info.range_str} ({post_info.num_days} day{"s" if post_info.num_days != 1 else ""})
  </div>
{stat_html}
  <table>
    <thead>
      <tr>
        <th>Metric</th>
        <th class="num-col">Pre</th>
        <th class="num-col">Post</th>
        <th class="num-col">&Delta;</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


def _build_topic_card(topics: TopicConversion, info: PeriodInfo) -> str:
    rows_html = []
    for topic, asked, demo, rate in topics.topics:
        bar_w = int(rate * 1.2) if rate is not None else 0
        bar_col = _rate_color(rate)
        bar_html = f'<span class="rate-bar" style="width:{bar_w}px; background:{bar_col};"></span>' if bar_w > 0 else ""
        rows_html.append(
            f'      <tr><td>{topic}</td>'
            f'<td class="num-col">{asked}</td>'
            f'<td class="num-col">{demo}</td>'
            f'<td class="num-col">{_fmt(rate)}{_rate_badge(rate)}</td>'
            f'<td>{bar_html}</td></tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">2</span> Per-Question Conversion Rate</h2>
  <div class="period-info">
    {info.range_str} ({info.num_days} day{"s" if info.num_days != 1 else ""})
  </div>
  <table>
    <thead>
      <tr>
        <th>Question Topic</th>
        <th class="num-col">Asked</th>
        <th class="num-col">Demo</th>
        <th class="num-col">Conv %</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


def _build_ambassador_card(rows, info: PeriodInfo) -> str:
    amb_data = ambassador_q_demo(rows)

    rows_html = []
    for name, m in amb_data:
        if m.questions_asked == 0:
            continue
        top_qs = ", ".join(f"{q} ({c})" for q, c in m.top_dropoff[:3]) if m.top_dropoff else "\u2014"
        rows_html.append(
            f'      <tr><td>{name}</td>'
            f'<td class="num-col">{m.questions_asked}</td>'
            f'<td class="num-col">{m.converted_to_demo}</td>'
            f'<td class="num-col">{m.dropped_off}</td>'
            f'<td class="num-col">{_fmt(m.q_demo_rate)}{_rate_badge(m.q_demo_rate)}</td>'
            f'<td style="font-size:0.75rem;color:var(--text-secondary);">{top_qs}</td></tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">3</span> Per-Ambassador Q\u2192Demo</h2>
  <div class="period-info">
    {info.range_str} ({info.num_days} day{"s" if info.num_days != 1 else ""})
  </div>
  <table>
    <thead>
      <tr>
        <th>Ambassador</th>
        <th class="num-col">Questions</th>
        <th class="num-col">Demos</th>
        <th class="num-col">Dropoffs</th>
        <th class="num-col">Conv %</th>
        <th>Top Dropoff Qs</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


def generate_html(pre_m: QDemoMetrics, post_m: QDemoMetrics,
                  pre_info: PeriodInfo, post_info: PeriodInfo,
                  topics: TopicConversion, all_rows, all_info: PeriodInfo) -> str:
    comparison = _build_comparison_card(pre_m, post_m, pre_info, post_info)
    topic_card = _build_topic_card(topics, all_info)
    ambassador_card = _build_ambassador_card(all_rows, all_info)

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
<div class="subtitle">Tracking Q&rarr;Demo conversion before and after redirect training &middot; Baseline: {BASELINE_Q_DEMO_RATE:.0f}%</div>

{comparison}

{topic_card}

{ambassador_card}

<footer>
  Generated from visit form data &middot; EXP-006
</footer>

</body>
</html>
"""


def write_html(pre_m: QDemoMetrics, post_m: QDemoMetrics,
               pre_info: PeriodInfo, post_info: PeriodInfo,
               topics: TopicConversion, all_rows, all_info: PeriodInfo) -> None:
    html_path = os.path.join(os.path.dirname(__file__), "question_redirect.html")
    html = generate_html(pre_m, post_m, pre_info, post_info, topics, all_rows, all_info)
    with open(html_path, "w") as f:
        f.write(html)
    import sys
    print(f"  Updated report: {html_path}", file=sys.stderr)
