#!/usr/bin/env python3
"""
Experiment report verification against the Experimentation-OS spec.

Reads a Notion page (saved as markdown) and validates structural compliance.
Run after any replace_content call to catch spec violations early.

Usage:
    python3 lib/verify_report.py --file /tmp/exp007_content.md
    python3 lib/verify_report.py --file /tmp/exp007_content.md --verbose
"""

import argparse
import re
import sys
from pathlib import Path


# ── Check functions ──────────────────────────────────────────────────
# Each returns (passed: bool, message: str)

def check_verdict_banner_first(content):
    """Check 1: Verdict banner is first element (callout with verdict keyword)."""
    stripped = content.lstrip()
    verdict_keywords = ['SHIP IT', 'ITERATE', 'KILL IT', 'IN PROGRESS', 'NEEDS MORE DATA', 'MIXED']

    # Check first ~500 chars for a callout containing a verdict
    first_block = stripped[:500]

    # Notion callouts: ::: callout {icon="..." color="..."} or <callout ...>
    has_callout = (
        '<callout' in first_block
        or '::: callout' in first_block
        or ':::callout' in first_block
    )
    has_verdict = any(kw in first_block.upper() for kw in [k.upper() for k in verdict_keywords])

    if has_callout and has_verdict:
        return True, "Verdict banner is first element"
    elif has_verdict and not has_callout:
        return False, "Verdict keyword found but not in a callout block"
    elif has_callout and not has_verdict:
        return False, "Callout found first but missing verdict keyword (SHIP IT/ITERATE/KILL IT/IN PROGRESS)"
    else:
        return False, "No verdict banner found at start of page"


def check_verdict_appears_once(content):
    """Check 2: Verdict keyword appears at most twice (banner + scorecard ref is OK)."""
    # Find which verdict is used
    verdict_keywords = ['SHIP IT', 'ITERATE', 'KILL IT', 'IN PROGRESS', 'NEEDS MORE DATA']

    for kw in verdict_keywords:
        count = content.upper().count(kw.upper())
        if count > 0:
            if count <= 2:
                return True, f"Verdict '{kw}' appears {count} time(s)"
            else:
                return False, f"Verdict '{kw}' appears {count} times (max: 2)"

    return False, "No verdict keyword found anywhere on page"


def check_scorecard_rows(content):
    """Check 3: Scorecard has exactly 5 rows."""
    # Find the first table after the banner (scorecard)
    # Look for table patterns — Notion markdown tables use | delimiters
    lines = content.split('\n')

    in_first_table = False
    table_rows = 0
    header_separator_found = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_first_table:
                in_first_table = True
                continue  # header row
            if re.match(r'^\|[\s\-:]+\|', stripped):
                header_separator_found = True
                continue  # separator row
            if header_separator_found:
                table_rows += 1
        elif in_first_table and header_separator_found:
            break  # end of first table

    # Also try HTML table pattern
    if table_rows == 0:
        # Count <tr> tags in first <table> block
        table_match = re.search(r'<table[^>]*>(.*?)</table>', content, re.DOTALL)
        if table_match:
            table_rows = len(re.findall(r'<tr[ >]', table_match.group(1))) - 1  # minus header

    if table_rows == 5:
        return True, "Scorecard has exactly 5 rows"
    elif table_rows > 0:
        return False, f"Scorecard has {table_rows} rows (expected: 5)"
    else:
        return False, "Could not find scorecard table"


def check_story_word_count(content):
    """Check 4: The Story section is <= 50 words."""
    # Find text between "The Story" heading and next section break
    story_match = re.search(
        r'(?:##?\s*(?:The Story|2\.\s*The Story))(.*?)(?:---|##|$)',
        content, re.DOTALL | re.IGNORECASE
    )

    if not story_match:
        return False, "Could not find 'The Story' section"

    story_text = story_match.group(1).strip()
    # Remove markdown formatting
    story_text = re.sub(r'<[^>]+>', '', story_text)  # HTML tags
    story_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', story_text)  # bold
    story_text = re.sub(r'\*([^*]+)\*', r'\1', story_text)  # italic
    story_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', story_text)  # links

    words = [w for w in story_text.split() if w.strip()]
    word_count = len(words)

    if word_count <= 50:
        return True, f"The Story: {word_count} words (max: 50)"
    else:
        return False, f"The Story: {word_count} words (max: 50)"


def check_insight_count(content):
    """Check 5: Insight count <= 3 in What We Found."""
    # Find What We Found section
    found_match = re.search(
        r'(?:##?\s*(?:What We Found|3\.\s*What We Found))(.*?)(?:##?\s*(?:What To Do|4\.))',
        content, re.DOTALL | re.IGNORECASE
    )

    if not found_match:
        # Try broader match
        found_match = re.search(
            r'(?:What We Found)(.*?)(?:What To Do)',
            content, re.DOTALL | re.IGNORECASE
        )

    if not found_match:
        return False, "Could not find 'What We Found' section"

    section = found_match.group(1)

    # Count callout blocks — Notion uses ::: callout or <callout
    callout_count = len(re.findall(r'(?:::: ?callout|<callout)', section))

    if callout_count <= 3:
        return True, f"What We Found: {callout_count} insight callouts (max: 3)"
    else:
        return False, f"What We Found: {callout_count} insight callouts (max: 3)"


def check_comparison_table_rows(content):
    """Check 6: Comparison table in What We Found has <= 4 data rows."""
    found_match = re.search(
        r'(?:##?\s*(?:What We Found|3\.\s*What We Found))(.*?)(?:##?\s*(?:What To Do|4\.))',
        content, re.DOTALL | re.IGNORECASE
    )

    if not found_match:
        found_match = re.search(
            r'(?:What We Found)(.*?)(?:What To Do)',
            content, re.DOTALL | re.IGNORECASE
        )

    if not found_match:
        return False, "Could not find 'What We Found' section"

    section = found_match.group(1)

    # Find first table in section
    lines = section.split('\n')
    in_table = False
    data_rows = 0
    header_sep_found = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                in_table = True
                continue  # header
            if re.match(r'^\|[\s\-:]+\|', stripped):
                header_sep_found = True
                continue
            if header_sep_found:
                data_rows += 1
        elif in_table and header_sep_found:
            break

    # Also try HTML table
    if data_rows == 0:
        table_match = re.search(r'<table[^>]*>(.*?)</table>', section, re.DOTALL)
        if table_match:
            data_rows = max(0, len(re.findall(r'<tr[ >]', table_match.group(1))) - 1)

    if data_rows == 0:
        return False, "No comparison table found in What We Found"
    elif data_rows <= 4:
        return True, f"Comparison table: {data_rows} data rows (max: 4)"
    else:
        return False, f"Comparison table: {data_rows} data rows (max: 4)"


def check_layer3_toggled(content):
    """Check 7: Layer 3 sections (5-8) are collapsed toggles."""
    layer3_names = [
        'Breakdown Detail', 'How We Tested', 'Decision Contract', 'Appendix'
    ]

    missing_toggles = []
    for name in layer3_names:
        # Check if section exists
        if not re.search(rf'{re.escape(name)}', content, re.IGNORECASE):
            continue  # section not present, skip

        # Check if it's toggled — Notion uses {toggle="true"} or ▶ prefix
        toggle_pattern = re.compile(
            rf'(?:▶|toggle\s*=\s*["\']true["\']|collapsed).*?{re.escape(name)}|'
            rf'{re.escape(name)}.*?(?:toggle\s*=\s*["\']true["\'])',
            re.IGNORECASE
        )
        if not toggle_pattern.search(content):
            missing_toggles.append(name)

    if not missing_toggles:
        return True, "All Layer 3 sections are toggled"
    else:
        return False, f"Not toggled: {', '.join(missing_toggles)}"


def check_primary_metric_once(content):
    """Check 8: Primary metric value doesn't appear more than 3 times.

    Allowed locations: banner (1), scorecard (2), The Story (3).
    The summary callout above Breakdown Detail is a section bridge and
    acceptable as a 4th if it uses a different framing (e.g., fraction
    instead of percentage).
    """
    # Extract the primary metric value from scorecard
    # Handle HTML table format: <td>Primary Metric</td><td>...35%...</td>
    scorecard_match = re.search(
        r'Primary Metric.*?(\d+%)',
        content, re.IGNORECASE | re.DOTALL
    )

    if not scorecard_match:
        return False, "Could not find Primary Metric in scorecard"

    metric_val = scorecard_match.group(1)
    count = content.count(metric_val)

    # Allow up to 3: banner, scorecard, story. A 4th in the section bridge
    # callout is flagged as a warning but not a hard fail.
    if count <= 3:
        return True, f"Primary metric '{metric_val}' appears {count} time(s) (max: 3)"
    else:
        return False, f"Primary metric '{metric_val}' appears {count} times (max: 3)"


def check_no_jargon_layers12(content):
    """Check 9: No statistical jargon in Layer 1-2 (before first toggle)."""
    # Find content before first toggle
    toggle_pos = content.find('▶')
    if toggle_pos == -1:
        # Try alternative toggle marker
        toggle_match = re.search(r'<toggle|{toggle|collapsed', content, re.IGNORECASE)
        toggle_pos = toggle_match.start() if toggle_match else len(content)

    visible_content = content[:toggle_pos]

    # Match statistical jargon but exclude common English uses:
    # "prior" as in "prior baseline" is OK; "prior distribution" is not
    jargon_terms = [
        r'\bP[\s-]?value\b', r'\bBeta\s*\(', r'\bCI\b', r'\bMDE\b',
        r'\bICC\b', r'\bcredible interval\b', r'\bposterior\b',
        r'\bprior\s+distribution\b', r'\bBayesian\b', r'\bconfidence interval\b',
        r'\bstatistically significant\b', r'\binformative prior\b',
    ]

    found_jargon = []
    for pattern in jargon_terms:
        matches = re.findall(pattern, visible_content, re.IGNORECASE)
        if matches:
            found_jargon.extend(matches)

    if not found_jargon:
        return True, "No jargon in Layer 1-2"
    else:
        return False, f"Jargon in Layer 1-2: {', '.join(set(found_jargon))}"


def check_action_items_have_owners(content):
    """Check 10: Each item in What To Do Next has a parenthetical with an owner name."""
    next_match = re.search(
        r'(?:##?\s*(?:What To Do Next|4\.\s*What To Do))(.*?)(?:##?\s*(?:Breakdown|5\.)|▶|:::|\{toggle)',
        content, re.DOTALL | re.IGNORECASE
    )

    if not next_match:
        next_match = re.search(
            r'(?:What To Do Next)(.*?)(?:▶|Breakdown|How We Tested|:::|\{toggle|$)',
            content, re.DOTALL | re.IGNORECASE
        )

    if not next_match:
        return False, "Could not find 'What To Do Next' section"

    section = next_match.group(1)
    # Find numbered items
    items = re.findall(r'^\s*\d+\.\s+(.+)', section, re.MULTILINE)

    if not items:
        return False, "No numbered items in What To Do Next"

    # Known owner names
    owners = ['Qasim', 'Asharib', 'Turab', 'Brandon']
    missing_owners = []

    for i, item in enumerate(items, 1):
        has_owner = any(name in item for name in owners)
        if not has_owner:
            # Check for parenthetical with any name
            if not re.search(r'\([^)]*[A-Z][a-z]+[^)]*\)', item):
                missing_owners.append(f"Item {i}")

    if not missing_owners:
        return True, f"All {len(items)} action items have owners"
    else:
        return False, f"Missing owners: {', '.join(missing_owners)}"


def check_pooled_callout_above_toggle(content):
    """Check 11: Pooled/summary callout appears ABOVE the Breakdown Detail toggle."""
    # Find Breakdown Detail toggle position
    breakdown_match = re.search(
        r'Breakdown\s*Detail\s*\{toggle',
        content, re.IGNORECASE
    )

    if not breakdown_match:
        breakdown_match = re.search(
            r'▶.*?Breakdown\s*Detail',
            content, re.IGNORECASE
        )

    if not breakdown_match:
        breakdown_match = re.search(
            r'Breakdown\s*Detail',
            content, re.IGNORECASE
        )

    if not breakdown_match:
        return False, "Could not find 'Breakdown Detail' section"

    # Check for a callout in the ~800 chars before the toggle heading
    before_toggle = content[max(0, breakdown_match.start() - 800):breakdown_match.start()]

    has_callout = (
        '<callout' in before_toggle
        or '::: callout' in before_toggle
        or ':::callout' in before_toggle
    )

    if has_callout:
        return True, "Pooled callout found above Breakdown Detail toggle"
    else:
        return False, "No callout found above Breakdown Detail toggle"


def check_banner_sentence_count(content):
    """Check 12: Banner has <= 2 sentences (for final verdicts), <= 3 for IN PROGRESS."""
    # Extract banner callout content — try multiple formats
    # Format 1: <callout ...>...</callout>
    banner_match = re.search(
        r'<callout[^>]*>(.*?)</callout>',
        content[:1500], re.DOTALL
    )

    if not banner_match:
        # Format 2: ::: callout {...}\n\t...\n:::
        banner_match = re.search(
            r':::\s*callout\s*\{[^}]*\}\s*\n(.*?)\n\s*:::',
            content[:1500], re.DOTALL
        )

    if not banner_match:
        return False, "Could not extract banner callout content"

    banner_text = banner_match.group(1).strip()
    # Remove markdown formatting
    banner_text = re.sub(r'<[^>]+>', '', banner_text)
    banner_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', banner_text)
    banner_text = re.sub(r'\\[\$]', '$', banner_text)  # unescape dollars

    # Count sentences (. or ! or ? followed by space or end)
    sentences = re.split(r'[.!?]+(?:\s|$)', banner_text)
    sentences = [s.strip() for s in sentences if s.strip()]

    is_in_progress = 'IN PROGRESS' in banner_text.upper()
    max_sentences = 3 if is_in_progress else 2

    if len(sentences) <= max_sentences:
        return True, f"Banner: {len(sentences)} sentence(s) (max: {max_sentences})"
    else:
        return False, f"Banner: {len(sentences)} sentences (max: {max_sentences})"


# ── Main ─────────────────────────────────────────────────────────────

ALL_CHECKS = [
    ("Verdict banner is first element", check_verdict_banner_first),
    ("Verdict appears once", check_verdict_appears_once),
    ("Scorecard has exactly 5 rows", check_scorecard_rows),
    ("The Story word count <= 50", check_story_word_count),
    ("Insight count <= 3", check_insight_count),
    ("Comparison table <= 4 rows", check_comparison_table_rows),
    ("Layer 3 all toggled", check_layer3_toggled),
    ("Primary metric once", check_primary_metric_once),
    ("No jargon in Layer 1-2", check_no_jargon_layers12),
    ("Action items have owners", check_action_items_have_owners),
    ("Pooled callout above toggle", check_pooled_callout_above_toggle),
    ("Banner <= 2 sentences", check_banner_sentence_count),
]


def run_checks(content, verbose=False):
    """Run all checks and return (passed_count, total, results)."""
    results = []
    passed = 0

    for name, check_fn in ALL_CHECKS:
        try:
            ok, msg = check_fn(content)
        except Exception as e:
            ok, msg = False, f"Error: {e}"

        results.append((ok, name, msg))
        if ok:
            passed += 1

    return passed, len(ALL_CHECKS), results


def main():
    parser = argparse.ArgumentParser(
        description="Verify experiment report against Experimentation-OS spec"
    )
    parser.add_argument("--file", required=True, help="Path to markdown file (Notion page content)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed messages")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    content = path.read_text(encoding="utf-8")

    if not content.strip():
        print("Error: file is empty", file=sys.stderr)
        sys.exit(1)

    # Extract experiment ID from content if possible
    exp_match = re.search(r'EXP-(\d+)', content)
    exp_id = f"EXP-{exp_match.group(1)}" if exp_match else "Report"

    print(f"\n{exp_id} Report Verification")
    print("=" * 40)

    passed, total, results = run_checks(content, verbose=args.verbose)

    for ok, name, msg in results:
        icon = "\u2705 PASS" if ok else "\u274c FAIL"
        if args.verbose or not ok:
            print(f"  {icon}  {msg}")
        else:
            print(f"  {icon}  {name}")

    print()
    print(f"Score: {passed}/{total} checks passed")

    if passed == total:
        print("\nAll checks passed!")
    else:
        print(f"\n{total - passed} check(s) need attention.")
        sys.exit(1)


if __name__ == "__main__":
    main()
