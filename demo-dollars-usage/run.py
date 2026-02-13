#!/usr/bin/env python3
"""
Demo Dollars Usage Analysis — standalone one-pager.

Reads demo dollars data from a cache JSON (produced via Rube MCP workflow)
and assembles a self-contained HTML report.

Usage:
    python3 run.py --json /path/to/demo_dollars_cache.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Demo Dollars Usage Analysis")
    parser.add_argument("--json", required=True, help="Path to demo_dollars_cache.json")
    parser.add_argument("--html", default="demo_dollars_usage.html", help="Output filename")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args()

    cache = json.loads(Path(args.json).read_text())

    data = {
        "recipient_overview": cache.get("recipient_overview", []),
        "note_distribution": cache.get("note_distribution", []),
        "recipient_activity": cache.get("recipient_activity", []),
        "ambassador_summary": cache.get("ambassador_summary", []),
        "app_opens": cache.get("app_opens", []),
        "recipient_timing": cache.get("recipient_timing", []),
        "app_opens_detailed": cache.get("app_opens_detailed", []),
    }

    counts = (
        f"{len(data['recipient_overview'])} recipients, "
        f"{len(data['ambassador_summary'])} ambassadors, "
        f"{len(data['recipient_activity'])} activity rows"
    )

    if not data["recipient_overview"]:
        print("Error: no recipient data in cache JSON", file=sys.stderr)
        sys.exit(1)

    now_pkt = datetime.utcnow() + timedelta(hours=5)
    generated_at = now_pkt.strftime("%b %d, %Y %I:%M %p")

    base = Path(__file__).parent / "ui"
    shell = (base / "shell.html").read_text()
    css = (base / "style.css").read_text()
    js = (base / "app.js").read_text()
    blob = json.dumps(data, separators=(",", ":"))

    html = (shell
        .replace("/* __CSS__ */", css)
        .replace("// __DATA__", f"const RAW = {blob};")
        .replace("// __APP__", js)
        .replace("__GENERATED_AT__", generated_at))

    out_path = Path(__file__).resolve().parent / args.html
    out_path.write_text(html, encoding="utf-8")

    if not args.quiet:
        print(f"Generated {out_path}")
        print(f"  {counts}")


if __name__ == "__main__":
    main()
