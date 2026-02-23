"""
EXP-009 Directed Day — Entry point.

Two modes:
  1. Generate routes:  python3 run.py --json targets_cache.json --generate
  2. Build dashboard:  python3 run.py --json targets_cache.json

The dashboard assembles ui/shell.html + ui/style.css + ui/app.js into
a single self-contained HTML file (directed_day_dashboard.html).
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT_HTML = HERE / "directed_day_dashboard.html"


def assemble_dashboard(cache_path: str) -> None:
    """Assemble self-contained HTML dashboard from ui/ components."""
    ui = HERE / "ui"
    shell = (ui / "shell.html").read_text()
    css = (ui / "style.css").read_text()
    js = (ui / "app.js").read_text()

    with open(cache_path) as f:
        data = json.load(f)

    blob = f"const DATA = {json.dumps(data, indent=2)};"

    html = (
        shell
        .replace("/* __CSS__ */", css)
        .replace("// __DATA__", blob)
        .replace("// __APP__", js)
    )

    OUTPUT_HTML.write_text(html)
    print(f"Dashboard written to {OUTPUT_HTML}")
    print(f"  Onboarding targets: {len(data.get('onboarding_targets', []))}")
    print(f"  Reactivation targets: {len(data.get('reactivation_targets', []))}")
    print(f"  Routes: {len(data.get('routes', []))}")


def generate_routes(cache_path: str, route_date: str) -> None:
    """Run the task generator and update the cache with routes."""
    from task_generator import (
        load_merchants_from_cache, compute_zones, compute_adjacency,
        compose_daily_routes, print_zones_summary, print_routes,
        routes_to_json, AMBASSADORS,
    )

    merchants = load_merchants_from_cache(cache_path)
    if not merchants:
        print("ERROR: No merchants loaded.")
        sys.exit(1)

    print(f"Loaded {len(merchants)} merchants")

    zones = compute_zones(merchants)
    adjacency = compute_adjacency(zones)
    print_zones_summary(zones, merchants)

    with open(cache_path) as f:
        cache_data = json.load(f)

    visited_ids = set(cache_data.get("visited_ids", []))

    routes = compose_daily_routes(
        merchants=merchants,
        zones=zones,
        adjacency=adjacency,
        ambassadors=AMBASSADORS,
        visited_ids=visited_ids,
        route_date=route_date,
    )
    print_routes(routes)

    # Update cache with routes and zone data
    cache_data["routes"] = routes_to_json(routes)
    cache_data["zones"] = [
        {
            "id": z.id,
            "centroid_lat": z.centroid_lat,
            "centroid_lng": z.centroid_lng,
            "radius_km": z.radius_km,
            "merchant_count": z.size,
            "merchant_ids": z.merchant_ids,
        }
        for z in zones
    ]

    with open(cache_path, "w") as f:
        json.dump(cache_data, f, indent=2)
    print(f"\nCache updated with routes at {cache_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EXP-009 Directed Day")
    parser.add_argument("--json", required=True, help="Path to targets cache JSON")
    parser.add_argument("--generate", action="store_true", help="Generate routes (then build dashboard)")
    parser.add_argument("--date", default="", help="Route date (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.generate:
        from datetime import date
        route_date = args.date or date.today().isoformat()
        generate_routes(args.json, route_date)

    assemble_dashboard(args.json)


if __name__ == "__main__":
    main()
