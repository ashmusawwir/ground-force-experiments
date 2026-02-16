"""Generate the full experiment HTML report — 4-card one-pager."""

import os
from typing import List, Tuple, Optional
from config import FUNNEL_STEPS, EXPERIMENT_NAME, TARGET_AMBASSADOR
from funnel import FunnelMetrics, PeriodInfo, FlowchartNodes

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
    text-align: center;
    max-width: 700px;
  }
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

  /* Stat grid */
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
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

  /* Insight box */
  .insight {
    background: linear-gradient(135deg, rgba(184,153,46,0.08), rgba(184,153,46,0.02));
    border-left: 3px solid var(--zar-gold);
    padding: 1rem;
    margin-top: 1rem;
    font-size: 0.85rem;
    border-radius: 0 12px 12px 0;
  }
  .insight strong { color: var(--zar-gold-dark); }
  .section-heading {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text);
    margin: 1.25rem 0 0.75rem;
  }

  /* Executive summary */
  .exec-summary {
    background: linear-gradient(135deg, rgba(184,153,46,0.06), rgba(184,153,46,0.02));
    border: 1.5px solid var(--zar-gold);
    border-radius: 16px;
    padding: 1.5rem;
    margin-top: 1rem;
  }
  .exec-summary h3 {
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    color: var(--zar-gold-dark);
    margin-bottom: 0.75rem;
  }
  .exec-summary ul {
    padding-left: 1.25rem;
    font-size: 0.85rem;
    line-height: 1.7;
  }
  .exec-summary li { margin-bottom: 0.25rem; }
  .verdict-box {
    margin-top: 1.25rem;
    padding: 1rem 1.25rem;
    border-radius: 12px;
    font-size: 0.9rem;
    font-weight: 600;
  }
  .verdict-positive {
    background: rgba(22,163,74,0.1);
    border: 1.5px solid var(--success);
    color: var(--success);
  }
  .verdict-negative {
    background: rgba(220,38,38,0.1);
    border: 1.5px solid var(--danger);
    color: var(--danger);
  }
  .verdict-neutral {
    background: rgba(184,153,46,0.1);
    border: 1.5px solid var(--zar-gold);
    color: var(--zar-gold-dark);
  }"""


def _sig2(val: float) -> str:
    """Format a number to 2 significant digits."""
    s = f"{val:.2g}"
    return s if 'e' not in s else f"{val:.0f}"


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


def _delta_badge(base_rate: Optional[float], expt_rate: Optional[float]) -> str:
    """Colored badge showing delta between two rates."""
    if base_rate is None or expt_rate is None:
        return '<span class="badge" style="background:#eee;color:#999;">&mdash;</span>'
    d = expt_rate - base_rate
    sign = "+" if d >= 0 else ""
    if d > 2:
        cls = "badge-success"
    elif d < -2:
        cls = "badge-danger"
    else:
        cls = "badge-warning"
    return f'<span class="badge {cls}">{sign}{_sig2(d)}pp</span>'


# --- Card 1: Sharoon vs Others Funnel ---

def _build_comparison_card(others_m: FunnelMetrics, sharoon_m: FunnelMetrics,
                           period_info: PeriodInfo) -> str:
    others_d, sharoon_d = others_m.as_dict(), sharoon_m.as_dict()
    others_conv, sharoon_conv = others_m.step_conversions(), sharoon_m.step_conversions()

    rows_html = []
    for step in FUNNEL_STEPS:
        o_count = others_d[step]
        s_count = sharoon_d[step]
        o_conv = _fmt_conv(others_conv[step])
        s_conv = _fmt_conv(sharoon_conv[step])
        delta = _fmt_delta_html(others_conv[step], sharoon_conv[step])
        rows_html.append(
            f'      <tr>'
            f'<td>{step}</td>'
            f'<td class="num-col">{o_count}</td>'
            f'<td class="num-col">{o_conv}</td>'
            f'<td class="num-col">{s_count}</td>'
            f'<td class="num-col">{s_conv}</td>'
            f'<td class="num-col">{delta}</td>'
            f'</tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">1</span> Sharoon (Map) vs Others (No Map)</h2>
  <div class="period-info">
    Window: {period_info.range_str} ({period_info.num_days} day{"s" if period_info.num_days != 1 else ""})
    &nbsp;&middot;&nbsp; Concurrent split: same days, different ambassadors
  </div>
  <table>
    <thead>
      <tr>
        <th>Step</th>
        <th class="num-col">Others #</th>
        <th class="num-col">Others Conv</th>
        <th class="num-col">Sharoon #</th>
        <th class="num-col">Sharoon Conv</th>
        <th class="num-col">&Delta;</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(rows_html)}
    </tbody>
  </table>
</div>"""


# --- Card 2: Per-Ambassador Baseline Breakdown ---

def _build_ambassador_card(amb_data: List[Tuple[str, FunnelMetrics]],
                           total_m: FunnelMetrics,
                           period_info: PeriodInfo) -> str:
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
  <h2><span class="num">2</span> Per-Ambassador Baseline Breakdown (Others)</h2>
  <div class="period-info">
    {period_info.range_str} &middot; Shows variance within the no-map group
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


# --- Card 3: Friction vs Credibility Analysis ---

def _build_friction_card(others_m: FunnelMetrics, sharoon_m: FunnelMetrics,
                         others_nodes: FlowchartNodes, sharoon_nodes: FlowchartNodes) -> str:
    # Metric 1: Opener pass rate
    o_opener_rate = _conv_rate(others_m.opener_passed, others_m.visits)
    s_opener_rate = _conv_rate(sharoon_m.opener_passed, sharoon_m.visits)

    # Metric 2: Questions asked rate (among those who passed opener)
    o_q_rate = _conv_rate(others_nodes.asked_questions, others_m.opener_passed) if others_m.opener_passed else None
    s_q_rate = _conv_rate(sharoon_nodes.asked_questions, sharoon_m.opener_passed) if sharoon_m.opener_passed else None

    # Metric 3: Demo -> Onboard rate
    o_demo_onboard = _conv_rate(others_m.onboardings, others_m.demos)
    s_demo_onboard = _conv_rate(sharoon_m.onboardings, sharoon_m.demos)

    metrics = [
        ("Opener Pass Rate", "Did the map reduce rejections at the door?",
         o_opener_rate, s_opener_rate,
         others_m.opener_passed, others_m.visits,
         sharoon_m.opener_passed, sharoon_m.visits),
        ("Questions Asked Rate", "Did the map create new conversation friction?",
         o_q_rate, s_q_rate,
         others_nodes.asked_questions, others_m.opener_passed,
         sharoon_nodes.asked_questions, sharoon_m.opener_passed),
        ("Demo &rarr; Onboard Rate", "Did map-sourced demos convert better?",
         o_demo_onboard, s_demo_onboard,
         others_m.onboardings, others_m.demos,
         sharoon_m.onboardings, sharoon_m.demos),
    ]

    metric_rows = []
    for label, question, o_rate, s_rate, o_num, o_den, s_num, s_den in metrics:
        o_str = _fmt_conv(o_rate)
        s_str = _fmt_conv(s_rate)
        delta = _delta_badge(o_rate, s_rate)

        # Insight interpretation
        if o_rate is not None and s_rate is not None:
            d = s_rate - o_rate
            if label == "Opener Pass Rate":
                if d > 5:
                    insight = "Map appears to reduce rejections"
                elif d < -5:
                    insight = "Map may increase rejection friction"
                else:
                    insight = "No meaningful difference at opener"
            elif label == "Questions Asked Rate":
                if d > 10:
                    insight = "Map generates more questions (friction risk)"
                elif d < -10:
                    insight = "Map reduces questions (smoother path to demo)"
                else:
                    insight = "Similar question rates"
            else:
                if d > 5:
                    insight = "Map-sourced demos convert better"
                elif d < -5:
                    insight = "Map-sourced demos convert worse"
                else:
                    insight = "Similar conversion after demo"
        else:
            insight = "Insufficient data"

        metric_rows.append(
            f'      <tr>'
            f'<td><strong>{label}</strong><br><span style="font-size:0.75rem;color:var(--text-secondary);">{question}</span></td>'
            f'<td class="num-col">{o_str}<br><span style="font-size:0.7rem;color:var(--text-secondary);">{o_num}/{o_den}</span></td>'
            f'<td class="num-col">{s_str}<br><span style="font-size:0.7rem;color:var(--text-secondary);">{s_num}/{s_den}</span></td>'
            f'<td class="num-col">{delta}</td>'
            f'<td style="font-size:0.8rem;">{insight}</td>'
            f'</tr>'
        )

    return f"""\
<div class="data-card">
  <h2><span class="num">3</span> Friction vs Credibility Analysis</h2>
  <div class="period-info">
    Three diagnostic sub-metrics: where exactly does the map help (or hurt)?
  </div>
  <table>
    <thead>
      <tr>
        <th>Metric</th>
        <th class="num-col">Others</th>
        <th class="num-col">Sharoon</th>
        <th class="num-col">&Delta;</th>
        <th>Interpretation</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(metric_rows)}
    </tbody>
  </table>
</div>"""


# --- Card 4: Executive Summary ---

def _build_executive_card(others_m: FunnelMetrics, sharoon_m: FunnelMetrics) -> str:
    o_opener = _conv_rate(others_m.opener_passed, others_m.visits)
    s_opener = _conv_rate(sharoon_m.opener_passed, sharoon_m.visits)
    o_e2e = others_m.e2e_rate()
    s_e2e = sharoon_m.e2e_rate()

    # Determine verdict
    opener_delta = (s_opener - o_opener) if (s_opener is not None and o_opener is not None) else 0
    e2e_delta = (s_e2e - o_e2e) if (s_e2e is not None and o_e2e is not None) else 0

    if opener_delta > 10 and e2e_delta > 5:
        verdict_cls = "verdict-positive"
        verdict_text = "Social proof map shows strong positive signal. Recommend teaching verbal social proof to all ambassadors immediately, and building a merchant map feature in the app."
        confidence = "High"
    elif opener_delta > 5 or e2e_delta > 3:
        verdict_cls = "verdict-positive"
        verdict_text = "Social proof map shows moderate positive signal. Recommend extending the test to more ambassadors before scaling. Teach verbal social proof as a low-cost interim measure."
        confidence = "Medium"
    elif opener_delta < -5 or e2e_delta < -3:
        verdict_cls = "verdict-negative"
        verdict_text = "Social proof map shows negative signal. The map may add friction without building enough credibility. Consider verbal social proof (\"your neighbor uses ZAR\") as a lighter-weight alternative."
        confidence = "Medium"
    else:
        verdict_cls = "verdict-neutral"
        verdict_text = "Results are inconclusive. Sample size may be too small for definitive judgment. Consider extending the experiment window or testing with additional ambassadors."
        confidence = "Low"

    o_opener_str = _fmt_conv(o_opener)
    s_opener_str = _fmt_conv(s_opener)
    o_e2e_str = _fmt_conv(o_e2e)
    s_e2e_str = _fmt_conv(s_e2e)

    return f"""\
<div class="data-card">
  <h2><span class="num">4</span> Executive Summary &amp; Recommendations</h2>
  <div class="period-info">
    Data-driven verdict on the social proof map intervention
  </div>

  <div class="stat-grid">
    <div class="stat-box">
      <div class="stat-value">{s_opener_str}</div>
      <div class="stat-label">Sharoon Opener Pass</div>
    </div>
    <div class="stat-box">
      <div class="stat-value">{o_opener_str}</div>
      <div class="stat-label">Others Opener Pass</div>
    </div>
    <div class="stat-box">
      <div class="stat-value">{_delta_badge(o_opener, s_opener)}</div>
      <div class="stat-label">Opener Delta</div>
    </div>
  </div>

  <div class="exec-summary">
    <h3>Why This Matters</h3>
    <ul>
      <li><strong>54% of rejections are addressable by social proof.</strong> "Not interested in dollars" (43%) and "Doesn't trust" (11%) both stem from the same root: the merchant doesn't believe this is real.</li>
      <li><strong>This tests credibility vs product objection.</strong> If showing nearby merchants increases conversion, the objection was never about the product &mdash; it was about trust.</li>
      <li><strong>Clear scaling paths:</strong> verbal social proof (short-term) &rarr; merchant map feature (medium-term) &rarr; self-reinforcing growth loop (long-term).</li>
      <li><strong>Terra's framing:</strong> every second between opener and demo is a chance for the merchant to say no. The map either buys credibility (weapon) or costs time (theater).</li>
    </ul>
  </div>

  <div style="margin-top:1.25rem;">
    <div class="section-heading">Outcome</div>
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th class="num-col">Others</th>
          <th class="num-col">Sharoon</th>
          <th class="num-col">&Delta;</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Opener Pass Rate</td>
          <td class="num-col">{o_opener_str}</td>
          <td class="num-col">{s_opener_str}</td>
          <td class="num-col">{_delta_badge(o_opener, s_opener)}</td>
        </tr>
        <tr>
          <td>End-to-End Rate</td>
          <td class="num-col">{o_e2e_str}</td>
          <td class="num-col">{s_e2e_str}</td>
          <td class="num-col">{_delta_badge(o_e2e, s_e2e)}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="{verdict_cls} verdict-box">
    Confidence: {confidence} &mdash; {verdict_text}
  </div>
</div>"""


# --- HTML Assembly ---

def generate_html(others_m: FunnelMetrics, sharoon_m: FunnelMetrics,
                  period_info: PeriodInfo,
                  amb_data: List[Tuple[str, FunnelMetrics]],
                  total_m: FunnelMetrics,
                  others_nodes: FlowchartNodes,
                  sharoon_nodes: FlowchartNodes) -> str:
    days_word = f"{period_info.num_days} day{'s' if period_info.num_days != 1 else ''}"

    card1 = _build_comparison_card(others_m, sharoon_m, period_info)
    card2 = _build_ambassador_card(amb_data, total_m, period_info)
    card3 = _build_friction_card(others_m, sharoon_m, others_nodes, sharoon_nodes)
    card4 = _build_executive_card(others_m, sharoon_m)

    total_visits = others_m.visits + sharoon_m.visits

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{EXPERIMENT_NAME} &mdash; EXP-002</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{CSS}
</style>
</head>
<body>

<h1>{EXPERIMENT_NAME} &mdash; EXP-002</h1>
<div class="subtitle">
  Does showing a map of nearby ZAR merchants bypass objections?<br>
  {TARGET_AMBASSADOR} (map) vs all other ambassadors (no map) &middot;
  {total_visits} onboarding visits &middot; {days_word} &middot; {period_info.range_str}
</div>

{card1}

{card2}

{card3}

{card4}

<div style="margin-top:20px; font-size:0.75rem; color:var(--text-secondary);">
  Generated from visit form data &middot; {period_info.range_str} &middot; Window: {days_word}
</div>

</body>
</html>
"""


def write_html(others_m: FunnelMetrics, sharoon_m: FunnelMetrics,
               period_info: PeriodInfo,
               amb_data: List[Tuple[str, FunnelMetrics]],
               total_m: FunnelMetrics,
               others_nodes: FlowchartNodes,
               sharoon_nodes: FlowchartNodes) -> None:
    html_path = os.path.join(os.path.dirname(__file__), "social_proof_map.html")
    html = generate_html(others_m, sharoon_m, period_info, amb_data, total_m,
                         others_nodes, sharoon_nodes)
    with open(html_path, "w") as f:
        f.write(html)
    import sys
    print(f"  Updated report: {html_path}", file=sys.stderr)
