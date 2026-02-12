"""Generate the full experiment HTML report — flowchart + data tables."""

import os
from typing import List, Tuple, Optional
from config import FUNNEL_STEPS
from funnel import FlowchartNodes, FunnelMetrics, PeriodInfo, QuestionDropoffData

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
  }
  .flowchart {
    position: relative;
    width: 960px;
    height: 520px;
  }
  .node {
    position: absolute;
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 500;
    text-align: center;
    line-height: 1.3;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  }
  .node .count {
    font-family: 'DM Sans', sans-serif;
    font-size: 26px;
    font-weight: 700;
    margin-top: 4px;
  }
  .node .label {
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
  }

  /* Node variants */
  .node.neutral {
    background: var(--card);
    border: 1.5px solid var(--border);
    color: var(--text);
  }
  .node.gold-tint {
    background: rgba(184, 153, 46, 0.10);
    border: 1.5px solid var(--zar-gold);
    color: var(--text);
  }
  .node.gold-tint .count { color: var(--zar-gold-dark); }
  .node.gold-tint .label { color: var(--zar-gold-dark); }
  .node.gold {
    background: linear-gradient(135deg, var(--zar-gold), var(--zar-gold-light));
    border: 1.5px solid var(--zar-gold-dark);
    color: #fff;
  }
  .node.gold .label { color: rgba(255,255,255,0.85); }
  .node.gold .count { color: #fff; }
  .node.muted {
    background: var(--border);
    border: 1.5px solid #D5CEBD;
    color: var(--text-secondary);
  }
  .node.muted .label { color: var(--text-secondary); }
  .node.muted .count { color: var(--text-secondary); }
  .node.success {
    background: var(--success);
    border: 1.5px solid #15803d;
    color: #fff;
  }
  .node.success .label { color: rgba(255,255,255,0.85); }
  .node.success .count { color: #fff; }
  .node.danger {
    background: var(--danger);
    border: 1.5px solid #b91c1c;
    color: #fff;
  }
  .node.danger .label { color: rgba(255,255,255,0.85); }
  .node.danger .count { color: #fff; }

  /* SVG arrows */
  svg.arrows {
    position: absolute;
    top: 0; left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }
  svg.arrows line, svg.arrows path {
    stroke-width: 1.5;
    fill: none;
  }

  /* Data table cards */
  .data-card {
    margin-top: 30px;
    background: var(--card);
    border-radius: 20px;
    padding: 1.5rem 2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border: 1px solid var(--border);
    width: 960px;
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
  .data-card tr.total-row td:first-child {
    color: var(--zar-gold-dark);
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

  /* Dropoff card extras */
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
    font-size: 1.8rem;
    font-weight: 700;
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
  .question-text { font-style: italic; color: var(--text-secondary); white-space: nowrap; }
  .section-heading {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text);
    margin: 1.25rem 0 0.75rem;
  }"""

SVG_ARROWS = """\
  <svg class="arrows" viewBox="0 0 960 520">
    <defs>
      <marker id="arrowGold" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
        <polygon points="0 0, 8 3, 0 6" fill="#B8992E"/>
      </marker>
      <marker id="arrowMuted" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
        <polygon points="0 0, 8 3, 0 6" fill="#D5CEBD"/>
      </marker>
      <marker id="arrowSuccess" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
        <polygon points="0 0, 8 3, 0 6" fill="#16a34a"/>
      </marker>
      <marker id="arrowDanger" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
        <polygon points="0 0, 8 3, 0 6" fill="#dc2626"/>
      </marker>
    </defs>

    <!-- visit → asked questions (horizontal right) -->
    <line x1="140" y1="250" x2="268" y2="250" stroke="#B8992E" marker-end="url(#arrowGold)"/>

    <!-- visit → proceeded to demo (up then right) -->
    <path d="M 90 220 L 90 125 L 418 125" stroke="#B8992E" marker-end="url(#arrowGold)"/>

    <!-- visit → opener rejection (down) -->
    <line x1="90" y1="280" x2="105" y2="388" stroke="#D5CEBD" marker-end="url(#arrowMuted)"/>

    <!-- asked questions → proceeded to demo (up-right) -->
    <line x1="340" y1="220" x2="450" y2="162" stroke="#B8992E" marker-end="url(#arrowGold)"/>

    <!-- asked questions → demo rejection (down) -->
    <line x1="340" y1="280" x2="350" y2="388" stroke="#D5CEBD" marker-end="url(#arrowMuted)"/>

    <!-- proceeded to demo → Not onboarded (right-up) -->
    <path d="M 590 110 L 728 92" stroke="#dc2626" marker-end="url(#arrowDanger)"/>

    <!-- proceeded to demo → merchant onboarded (right-down) -->
    <path d="M 590 140 L 728 197" stroke="#16a34a" marker-end="url(#arrowSuccess)"/>
  </svg>"""


def _sig2(val: float) -> str:
    """Format a number to 2 significant digits."""
    s = f"{val:.2g}"
    return s if 'e' not in s else f"{val:.0f}"


def _pct(n: int, d: int) -> str:
    return f"{_sig2(n / d * 100)}%" if d else "\u2013"


def _node(cls: str, label: str, count: int, left: int, top: int, w: int, h: int) -> str:
    return (f'  <div class="node {cls}" style="left:{left}px; top:{top}px; width:{w}px; height:{h}px;">\n'
            f'    <div class="label">{label}</div>\n'
            f'    <div class="count">{count}</div>\n'
            f'  </div>')


def _conv_rate(count: int, total: int) -> Optional[float]:
    return count / total * 100 if total else None


def _fmt_conv(rate: Optional[float]) -> str:
    return f"{_sig2(rate)}%" if rate is not None else "\u2014"


def _fmt_delta_html(base_rate: Optional[float], expt_rate: Optional[float]) -> str:
    if base_rate is None or expt_rate is None:
        return '<span class="delta-zero">\u2014</span>'
    d = expt_rate - base_rate
    if abs(d) < 0.05:
        return '<span class="delta-zero">0.0</span>'
    sign = "+" if d >= 0 else ""
    cls = "delta-pos" if d > 0 else "delta-neg"
    return f'<span class="{cls}">{sign}{_sig2(d)}</span>'


def _e2e_badge(rate: Optional[float]) -> str:
    if rate is None:
        return ""
    if rate >= 20:
        cls = "badge-success"
    elif rate >= 10:
        cls = "badge-warning"
    else:
        cls = "badge-danger"
    return f' <span class="badge {cls}">{_sig2(rate)}%</span>'


def _build_comparison_card(base_m: FunnelMetrics, expt_m: FunnelMetrics,
                           base_info: PeriodInfo, expt_info: PeriodInfo) -> str:
    base_d, expt_d = base_m.as_dict(), expt_m.as_dict()
    base_conv, expt_conv = base_m.step_conversions(), expt_m.step_conversions()

    rows_html = []
    for step in FUNNEL_STEPS:
        b_count = base_d[step]
        e_count = expt_d[step]
        b_conv = _fmt_conv(base_conv[step])
        e_conv = _fmt_conv(expt_conv[step])
        delta = _fmt_delta_html(base_conv[step], expt_conv[step])
        rows_html.append(
            f'      <tr>'
            f'<td>{step}</td>'
            f'<td class="num-col">{b_count}</td>'
            f'<td class="num-col">{b_conv}</td>'
            f'<td class="num-col">{e_count}</td>'
            f'<td class="num-col">{e_conv}</td>'
            f'<td class="num-col">{delta}</td>'
            f'</tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">1</span> Baseline vs Experiment</h2>
  <div class="period-info">
    Baseline: {base_info.range_str} ({base_info.num_days} days) &nbsp;&middot;&nbsp;
    Experiment: {expt_info.range_str} ({expt_info.num_days} day{"s" if expt_info.num_days != 1 else ""})
  </div>
  <table>
    <thead>
      <tr>
        <th>Step</th>
        <th class="num-col">Base #</th>
        <th class="num-col">Base Conv</th>
        <th class="num-col">Expt #</th>
        <th class="num-col">Expt Conv</th>
        <th class="num-col">&Delta;</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


def _build_ambassador_card(amb_data: List[Tuple[str, FunnelMetrics]],
                           total_m: FunnelMetrics,
                           expt_info: PeriodInfo) -> str:
    rows_html = []
    for name, m in amb_data:
        if m.visits == 0:
            continue
        opener_pct = _fmt_conv(_conv_rate(m.opener_passed, m.visits))
        demo_pct = _fmt_conv(_conv_rate(m.demos, m.opener_passed))
        e2e = _conv_rate(m.onboardings, m.visits)
        e2e_pct = _fmt_conv(e2e)
        rows_html.append(
            f'      <tr>'
            f'<td>{name}</td>'
            f'<td class="num-col">{m.visits}</td>'
            f'<td class="num-col">{opener_pct}</td>'
            f'<td class="num-col">{m.demos}</td>'
            f'<td class="num-col">{demo_pct}</td>'
            f'<td class="num-col">{m.onboardings}</td>'
            f'<td class="num-col">{e2e_pct}{_e2e_badge(e2e)}</td>'
            f'</tr>'
        )

    # Total row
    t_opener = _fmt_conv(_conv_rate(total_m.opener_passed, total_m.visits))
    t_demo = _fmt_conv(_conv_rate(total_m.demos, total_m.opener_passed))
    t_e2e = _conv_rate(total_m.onboardings, total_m.visits)
    t_e2e_pct = _fmt_conv(t_e2e)
    rows_html.append(
        f'      <tr class="total-row">'
        f'<td>TOTAL</td>'
        f'<td class="num-col">{total_m.visits}</td>'
        f'<td class="num-col">{t_opener}</td>'
        f'<td class="num-col">{total_m.demos}</td>'
        f'<td class="num-col">{t_demo}</td>'
        f'<td class="num-col">{total_m.onboardings}</td>'
        f'<td class="num-col">{t_e2e_pct}{_e2e_badge(t_e2e)}</td>'
        f'</tr>'
    )

    return f"""\
<div class="data-card">
  <h2><span class="num">2</span> Per-Ambassador Funnel</h2>
  <div class="period-info">
    Experiment: {expt_info.range_str} ({expt_info.num_days} day{"s" if expt_info.num_days != 1 else ""})
  </div>
  <table>
    <thead>
      <tr>
        <th>Ambassador</th>
        <th class="num-col">Visits</th>
        <th class="num-col">Opener Conv</th>
        <th class="num-col">Demos</th>
        <th class="num-col">Demo Conv</th>
        <th class="num-col">Onboard</th>
        <th class="num-col">E2E %</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


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


def _build_dropoff_card(dropoff: QuestionDropoffData, expt_info: PeriodInfo) -> str:
    rate_color = _rate_color(dropoff.conversion_rate)
    rate_str = f"{_sig2(dropoff.conversion_rate)}%" if dropoff.conversion_rate is not None else "\u2014"

    # Section A — stat boxes
    stat_html = f"""\
  <div class="stat-grid">
    <div class="stat-box">
      <div class="stat-value">{dropoff.total_asked}</div>
      <div class="stat-label">Asked Questions</div>
    </div>
    <div class="stat-box">
      <div class="stat-value">{dropoff.converted_to_demo}</div>
      <div class="stat-label">Converted to Demo</div>
    </div>
    <div class="stat-box">
      <div class="stat-value">{dropoff.dropped_off}</div>
      <div class="stat-label">Dropped Off</div>
    </div>
    <div class="stat-box">
      <div class="stat-value" style="color:{rate_color}">{rate_str}</div>
      <div class="stat-label">Conversion Rate</div>
    </div>
  </div>"""

    # Section B — top dropoff questions
    q_rows = []
    for i, (text, count) in enumerate(dropoff.dropoff_questions, 1):
        pct = f"{count / dropoff.dropped_off * 100:.0f}%" if dropoff.dropped_off else "\u2014"
        q_rows.append(
            f'      <tr><td class="num-col">{i}</td>'
            f'<td class="question-text">{text}</td>'
            f'<td class="num-col">{count}</td>'
            f'<td class="num-col">{pct}</td></tr>'
        )

    questions_html = ""
    if q_rows:
        questions_html = f"""\
  <div class="section-heading">Top Dropoff Questions</div>
  <table>
    <thead>
      <tr>
        <th class="num-col">#</th>
        <th>Question</th>
        <th class="num-col">Count</th>
        <th class="num-col">% of Dropoffs</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(q_rows)}
    </tbody>
  </table>
  <div class="insight">
    <strong>{dropoff.dropped_off}</strong> merchants asked a question but did not see a demo.
  </div>"""

    # Section C — per-ambassador Q→Demo table
    amb_rows = []
    for name, n_asked, n_demos, n_drops, rate, top_qs in dropoff.ambassador_stats:
        rate_str_a = f"{_sig2(rate)}%" if rate is not None else "\u2014"
        badge = _rate_badge(rate)
        top_qs_str = ", ".join(f"{q} ({c})" for q, c in top_qs) if top_qs else "\u2014"
        amb_rows.append(
            f'      <tr><td>{name}</td>'
            f'<td class="num-col">{n_asked}</td>'
            f'<td class="num-col">{n_demos}</td>'
            f'<td class="num-col">{n_drops}</td>'
            f'<td class="num-col">{rate_str_a}{badge}</td>'
            f'<td class="question-text">{top_qs_str}</td></tr>'
        )

    # Total row
    t_rate = dropoff.conversion_rate
    t_rate_str = f"{_sig2(t_rate)}%" if t_rate is not None else "\u2014"
    amb_rows.append(
        f'      <tr class="total-row"><td>TOTAL</td>'
        f'<td class="num-col">{dropoff.total_asked}</td>'
        f'<td class="num-col">{dropoff.converted_to_demo}</td>'
        f'<td class="num-col">{dropoff.dropped_off}</td>'
        f'<td class="num-col">{t_rate_str}</td>'
        f'<td></td></tr>'
    )

    # Insight — worst ambassador
    worst_insight = ""
    if dropoff.ambassador_stats:
        w_name, _, _, _, w_rate, _ = dropoff.ambassador_stats[0]
        if w_rate is not None:
            worst_insight = (
                f'\n  <div class="insight">'
                f'Struggling most: <strong>{w_name}</strong> &mdash; only '
                f'<strong>{_sig2(w_rate)}%</strong> of question-askers proceeded to demo.</div>'
            )

    ambassador_q_html = f"""\
  <div class="section-heading">Per-Ambassador Q&rarr;Demo Conversion</div>
  <table>
    <thead>
      <tr>
        <th>Ambassador</th>
        <th class="num-col">Questions</th>
        <th class="num-col">Demos</th>
        <th class="num-col">Dropoffs</th>
        <th class="num-col">Conv %</th>
        <th>Top Questions</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(amb_rows)}
    </tbody>
  </table>{worst_insight}"""

    return f"""\
<div class="data-card">
  <h2><span class="num">3</span> Question &rarr; Demo Dropoff Deep-Dive</h2>
  <div class="period-info">
    Experiment: {expt_info.range_str} ({expt_info.num_days} day{"s" if expt_info.num_days != 1 else ""})
  </div>
{stat_html}
{questions_html}
{ambassador_q_html}
</div>"""


def generate_flowchart(nodes: FlowchartNodes, info: PeriodInfo,
                       base_m: FunnelMetrics, expt_m: FunnelMetrics,
                       base_info: PeriodInfo, expt_info: PeriodInfo,
                       amb_data: List[Tuple[str, FunnelMetrics]],
                       total_m: FunnelMetrics,
                       dropoff: 'QuestionDropoffData' = None) -> str:
    v = nodes
    opener_passed = v.asked_questions + v.direct_to_demo
    days_word = f"{info.num_days} day{'s' if info.num_days != 1 else ''}"

    node_html = "\n\n".join([
        _node("neutral",   "visit",              v.visit,             40,  220, 100, 60),
        _node("gold-tint", "asked questions",     v.asked_questions,  270, 220, 140, 60),
        _node("gold",      "proceeded to demo",   v.proceeded_to_demo, 420, 90, 170, 70),
        _node("muted",     "opener rejection",    v.opener_rejection,  20, 390, 170, 60),
        _node("muted",     "demo rejection",      v.demo_rejection,   270, 390, 160, 60),
        _node("danger",    "Not onboarded",        v.not_onboarded,   730,  60, 180, 65),
        _node("success",   "merchant onboarded",   v.onboarded,       730, 165, 180, 65),
    ])

    comparison_html = _build_comparison_card(base_m, expt_m, base_info, expt_info)
    ambassador_html = _build_ambassador_card(amb_data, total_m, expt_info)
    dropoff_html = _build_dropoff_card(dropoff, expt_info) if dropoff else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Onboarding Funnel &mdash; {info.range_str}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{CSS}
</style>
</head>
<body>

<h1>Onboarding Funnel &mdash; {info.range_str}</h1>
<div class="subtitle">{v.visit} onboarding visits &middot; {days_word} of experiment data &middot; Data from new visit form</div>

<div class="data-card" style="padding: 2rem;">
<div class="flowchart">
  <!-- SVG Arrows -->
{SVG_ARROWS}

  <!-- NODES -->

{node_html}
</div>
</div>

{comparison_html}

{ambassador_html}

{dropoff_html}

<div style="margin-top:20px; font-size:0.75rem; color:var(--text-secondary);">
  Generated from new visit form data &middot; {info.range_str} &middot; Experiment period: {days_word}
</div>

</body>
</html>
"""


def write_flowchart(nodes: FlowchartNodes, info: PeriodInfo,
                    base_m: FunnelMetrics, expt_m: FunnelMetrics,
                    base_info: PeriodInfo, expt_info: PeriodInfo,
                    amb_data: List[Tuple[str, FunnelMetrics]],
                    total_m: FunnelMetrics,
                    dropoff: 'QuestionDropoffData' = None) -> None:
    html_path = os.path.join(os.path.dirname(__file__), "dont_show_tell_exp.html")
    html = generate_flowchart(nodes, info, base_m, expt_m, base_info, expt_info, amb_data, total_m, dropoff)
    with open(html_path, "w") as f:
        f.write(html)
    import sys
    print(f"  Updated flowchart: {html_path}", file=sys.stderr)
