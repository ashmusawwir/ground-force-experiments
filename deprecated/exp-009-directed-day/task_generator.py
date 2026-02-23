"""
Two-layer geo-clustering task generator for EXP-009 Directed Day.

Layer 1 — Geographic zones: K-means on merchant lat/lng, variable size,
          tight radius (≤2km target). Recomputed weekly.
Layer 2 — Daily routes:     Compose exactly N visits per ambassador from
          1-2 adjacent zones, mixing onboarding + reactivation targets.

Usage:
  python3 task_generator.py --json targets_cache.json                # Generate zones + daily routes
  python3 task_generator.py --json targets_cache.json --zones-only   # Just recompute zones
  python3 task_generator.py --json targets_cache.json --date 2026-02-17  # Routes for specific date
"""

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional

# ── Configuration ─────────────────────────────────────────────────────

VISITS_PER_AMBASSADOR = 8
ZONE_MAX_RADIUS_KM = 2.0
ZONE_ADJACENCY_KM = 3.0
KMEANS_ITERATIONS = 50
RANDOM_SEED = 42

AMBASSADORS = [
    "Arslan Ansari",
    "Sharoon Javed",
    "Muhammad Zahid",
    "Afsar Khan",
]

# Visit sheet names → canonical AMBASSADORS names
# (from show-dont-tell/config.py AMBASSADOR_NAMES)
AMBASSADOR_ALIASES = {
    "Arslan Ansari": "Arslan Ansari",
    "Afsar Khan": "Afsar Khan",
    "Sharoon Sam93": "Sharoon Javed",
    "Zahid Khan": "Muhammad Zahid",
    "Junaid Ahmed": "Junaid Ahmed",
    "irfan rana": "Muhammad Irfan",
    "Umer Daniyal": "Umer Daniyal",
    "Owais Feroz": "Owais Feroz",
}


# ── Data classes ──────────────────────────────────────────────────────

@dataclass
class Merchant:
    id: str
    name: str
    lat: float
    lng: float
    type: str          # "onboarding" or "reactivation"
    phone: str = ""
    days_inactive: Optional[int] = None
    lifetime_tx: int = 0
    decline_reason: str = ""
    ambassador_who_visited: str = ""

    @property
    def coords(self) -> tuple[float, float]:
        return (self.lat, self.lng)


@dataclass
class Zone:
    id: int
    centroid_lat: float
    centroid_lng: float
    merchant_ids: list[str] = field(default_factory=list)
    radius_km: float = 0.0

    @property
    def size(self) -> int:
        return len(self.merchant_ids)


@dataclass
class Task:
    merchant_id: str
    type: str
    shop_name: str
    lat: float
    lng: float
    phone: str
    objective: str
    zone_id: int
    is_affinity: bool = False  # True if assigned to the ambassador who originally demoed


@dataclass
class DailyRoute:
    ambassador: str
    date: str
    zone_ids: list[int]
    tasks: list[Task]

    @property
    def size(self) -> int:
        return len(self.tasks)


# ── Haversine ─────────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two lat/lng points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


# ══════════════════════════════════════════════════════════════════════
# LAYER 1 — GEOGRAPHIC ZONES (K-means)
# ══════════════════════════════════════════════════════════════════════

def compute_zones(merchants: list[Merchant],
                  max_radius_km: float = ZONE_MAX_RADIUS_KM) -> list[Zone]:
    """K-means clustering with adaptive K to keep zone radii ≤ max_radius_km.

    Starts with K = n/6, then splits any oversized zone until all fit.
    """
    if not merchants:
        return []

    n = len(merchants)
    coords = [m.coords for m in merchants]
    random.seed(RANDOM_SEED)

    # Initial K estimate
    K = max(2, round(n / 6))

    for attempt in range(5):
        # K-means++ initialization
        centroids = [coords[random.randint(0, n - 1)]]
        for _ in range(K - 1):
            dists = [
                min(haversine(c[0], c[1], ct[0], ct[1]) ** 2 for ct in centroids)
                for c in coords
            ]
            total = sum(dists)
            if total == 0:
                centroids.append(coords[random.randint(0, n - 1)])
                continue
            r = random.random() * total
            s = 0
            for i, d in enumerate(dists):
                s += d
                if s >= r:
                    centroids.append(coords[i])
                    break

        # Run k-means
        assignments = [0] * n
        for _ in range(KMEANS_ITERATIONS):
            # Assign
            for i, c in enumerate(coords):
                assignments[i] = min(
                    range(K),
                    key=lambda k: haversine(c[0], c[1], centroids[k][0], centroids[k][1]),
                )
            # Update centroids
            for k in range(K):
                members = [coords[i] for i in range(n) if assignments[i] == k]
                if members:
                    centroids[k] = (
                        sum(m[0] for m in members) / len(members),
                        sum(m[1] for m in members) / len(members),
                    )

        # Check radii
        zones = []
        oversized = False
        for k in range(K):
            member_ids = [merchants[i].id for i in range(n) if assignments[i] == k]
            if not member_ids:
                continue
            member_coords = [coords[i] for i in range(n) if assignments[i] == k]
            radius = max(
                haversine(c[0], c[1], centroids[k][0], centroids[k][1])
                for c in member_coords
            )
            zones.append(Zone(
                id=k,
                centroid_lat=centroids[k][0],
                centroid_lng=centroids[k][1],
                merchant_ids=member_ids,
                radius_km=round(radius, 2),
            ))
            if radius > max_radius_km and len(member_ids) > 2:
                oversized = True

        if not oversized:
            break
        # Increase K and retry
        K = int(K * 1.4)

    # Re-number zones sequentially
    for i, z in enumerate(zones):
        z.id = i + 1

    return zones


def compute_adjacency(zones: list[Zone],
                      max_dist_km: float = ZONE_ADJACENCY_KM) -> dict[int, list[int]]:
    """Precompute which zones are adjacent (centroid-to-centroid ≤ max_dist_km)."""
    adj: dict[int, list[int]] = defaultdict(list)
    for i, z1 in enumerate(zones):
        for z2 in zones[i + 1:]:
            d = haversine(z1.centroid_lat, z1.centroid_lng,
                          z2.centroid_lat, z2.centroid_lng)
            if d <= max_dist_km:
                adj[z1.id].append(z2.id)
                adj[z2.id].append(z1.id)
    return dict(adj)


# ══════════════════════════════════════════════════════════════════════
# LAYER 2 — DAILY ROUTE COMPOSITION
# ══════════════════════════════════════════════════════════════════════

def _resolve_ambassador(raw_name: str) -> Optional[str]:
    """Map a visit-sheet ambassador name to a canonical AMBASSADORS name.

    Returns None if the ambassador isn't in the active AMBASSADORS list.
    """
    canonical = AMBASSADOR_ALIASES.get(raw_name, raw_name)
    return canonical if canonical in AMBASSADORS else None


def compose_daily_routes(
    merchants: list[Merchant],
    zones: list[Zone],
    adjacency: dict[int, list[int]],
    ambassadors: list[str],
    visited_ids: set[str],
    visits_per_ambassador: int = VISITS_PER_AMBASSADOR,
    route_date: str = "",
) -> list[DailyRoute]:
    """Compose exactly N visits per ambassador from adjacent zones.

    Ambassador affinity: onboarding revisits are preferentially assigned to
    the ambassador who originally demoed the merchant (the existing
    relationship increases close probability).

    Spreads ambassadors across different geographic areas. Ensures a mix
    of onboarding + reactivation targets in each route.
    """
    if not route_date:
        route_date = date.today().isoformat()

    merchant_map = {m.id: m for m in merchants}

    # ── Build ambassador → "own" unvisited onboarding merchants ──────
    # These are merchants this ambassador originally demoed
    amb_own_merchants: dict[str, list[str]] = {a: [] for a in ambassadors}
    for m in merchants:
        if m.type == "onboarding" and m.ambassador_who_visited and m.id not in visited_ids:
            resolved = _resolve_ambassador(m.ambassador_who_visited)
            if resolved:
                amb_own_merchants[resolved].append(m.id)

    # ── Build zone → unvisited merchants mapping ─────────────────────
    zone_available: dict[int, list[str]] = {}
    for z in zones:
        available = [mid for mid in z.merchant_ids if mid not in visited_ids]
        if available:
            zone_available[z.id] = available

    # Build merchant → zone lookup
    mid_to_zone: dict[str, int] = {}
    for z in zones:
        for mid in z.merchant_ids:
            mid_to_zone[mid] = z.id

    zone_map = {z.id: z for z in zones}
    routes: list[DailyRoute] = []
    used_ids: set[str] = set()
    used_primary_zones: set[int] = set()

    for amb in ambassadors:
        tasks: list[Task] = []
        assigned_zones: list[int] = []
        affinity_ids: set[str] = set()  # Track which tasks are affinity-matched

        # ── Step 1: Find primary zone based on affinity ──────────────
        # Count this ambassador's own merchants per zone
        own_unvisited = [mid for mid in amb_own_merchants[amb] if mid not in used_ids]
        zone_own_count: dict[int, int] = defaultdict(int)
        for mid in own_unvisited:
            zid = mid_to_zone.get(mid)
            if zid and zid in zone_available:
                zone_own_count[zid] += 1

        # Pick primary zone: prefer zone with most "own" merchants,
        # then fall back to largest zone not yet claimed
        primary_zone_id = None

        if zone_own_count:
            # Sort by own-count desc, then by total available desc
            affinity_zones = sorted(
                zone_own_count.keys(),
                key=lambda zid: (zone_own_count[zid],
                                 len([m for m in zone_available.get(zid, []) if m not in used_ids])),
                reverse=True,
            )
            for zid in affinity_zones:
                if zid not in used_primary_zones:
                    primary_zone_id = zid
                    break

        # Fallback: largest available zone not yet claimed
        if primary_zone_id is None:
            sorted_zone_ids = sorted(
                zone_available.keys(),
                key=lambda zid: len([m for m in zone_available[zid] if m not in used_ids]),
                reverse=True,
            )
            for zid in sorted_zone_ids:
                remaining = [mid for mid in zone_available.get(zid, []) if mid not in used_ids]
                if remaining and zid not in used_primary_zones:
                    primary_zone_id = zid
                    break
            # Last resort: any zone with remaining merchants
            if primary_zone_id is None:
                for zid in sorted_zone_ids:
                    remaining = [mid for mid in zone_available.get(zid, []) if mid not in used_ids]
                    if remaining:
                        primary_zone_id = zid
                        break

        if primary_zone_id is None:
            routes.append(DailyRoute(ambassador=amb, date=route_date, zone_ids=[], tasks=[]))
            continue

        used_primary_zones.add(primary_zone_id)
        assigned_zones.append(primary_zone_id)

        # ── Step 2: Collect candidates from zone + adjacent zones ────
        candidate_zone_ids = [primary_zone_id] + adjacency.get(primary_zone_id, [])
        candidates: list[Merchant] = []
        for zid in candidate_zone_ids:
            for mid in zone_available.get(zid, []):
                if mid not in used_ids and mid in merchant_map:
                    candidates.append(merchant_map[mid])
                    if zid != primary_zone_id and zid not in assigned_zones:
                        assigned_zones.append(zid)

        # ── Step 3: Also pull own merchants from ANY zone ────────────
        # (affinity merchants outside the adjacent zone radius)
        own_outside = []
        for mid in own_unvisited:
            if mid not in used_ids and mid in merchant_map:
                m = merchant_map[mid]
                if m not in candidates:
                    own_outside.append(m)

        # ── Step 4: Select — own merchants first, then zone fill ─────
        own_set = set(own_unvisited)

        # Partition zone candidates into own vs non-own
        own_in_zone = [m for m in candidates if m.id in own_set and m.type == "onboarding"]
        other_candidates = [m for m in candidates if m.id not in own_set or m.type != "onboarding"]

        # Sort own: T1 (has phone) first, then zone proximity (in-zone before outside)
        own_all = own_in_zone + own_outside
        own_all.sort(key=lambda m: (0 if m.phone else 1, m.id))
        # Sort others: onboarding by phone (T1 first) then stable id, reactivation by most inactive
        other_onb = [m for m in other_candidates if m.type == "onboarding"]
        other_rct = [m for m in other_candidates if m.type == "reactivation"]
        other_onb.sort(key=lambda m: (0 if m.phone else 1, m.id))
        other_rct.sort(key=lambda m: -(m.days_inactive or 999))

        # Build final selection: own merchants first, then interleave remaining
        selected: list[Merchant] = []
        selected_set: set[str] = set()

        # Take own merchants (up to half the visits, to leave room for reactivation mix)
        max_own = min(len(own_all), visits_per_ambassador - 2)  # leave at least 2 for mix
        if len(other_rct) == 0:
            max_own = min(len(own_all), visits_per_ambassador)  # no react available, take all own
        for m in own_all[:max_own]:
            selected.append(m)
            selected_set.add(m.id)
            affinity_ids.add(m.id)

        # Fill remaining slots with interleaved onb + react
        remaining_slots = visits_per_ambassador - len(selected)
        fill_onb = [m for m in other_onb if m.id not in selected_set]
        fill_rct = [m for m in other_rct if m.id not in selected_set]

        oi, ri = 0, 0
        total_fill_onb = len(fill_onb)
        total_fill_rct = len(fill_rct)
        total_fill = total_fill_onb + total_fill_rct

        for _ in range(min(remaining_slots, total_fill)):
            onb_remaining = total_fill_onb - oi
            rct_remaining = total_fill_rct - ri
            if onb_remaining <= 0:
                selected.append(fill_rct[ri]); ri += 1
            elif rct_remaining <= 0:
                selected.append(fill_onb[oi]); oi += 1
            elif rct_remaining / (onb_remaining + rct_remaining) > 0.4:
                # Slightly favor reactivation in fill slots since own slots are all onboarding
                selected.append(fill_rct[ri]); ri += 1
            else:
                selected.append(fill_onb[oi]); oi += 1

        for m in selected:
            objective = _build_objective(m)
            is_affinity = m.id in affinity_ids
            tasks.append(Task(
                merchant_id=m.id,
                type=m.type,
                shop_name=m.name,
                lat=m.lat,
                lng=m.lng,
                phone=m.phone,
                objective=objective,
                zone_id=_find_zone_for_merchant(m.id, zones),
                is_affinity=is_affinity,
            ))
            used_ids.add(m.id)

        routes.append(DailyRoute(
            ambassador=amb,
            date=route_date,
            zone_ids=assigned_zones,
            tasks=tasks,
        ))

    return routes


def _build_objective(m: Merchant) -> str:
    """Generate a clear visit objective based on merchant type."""
    if m.type == "reactivation":
        days = m.days_inactive or 0
        if days > 30:
            return f"Reactivation: inactive {days}d. Communicate current incentive, do dummy transaction (self-purchase + trader purchase)."
        return "Reactivation: communicate incentive, do dummy transaction (self-purchase + trader purchase)."

    # Onboarding revisit
    parts = ["Onboarding revisit: reference previous demo"]
    if m.decline_reason:
        parts.append(f"address concern: '{m.decline_reason}'")
    parts.append("complete onboarding on the spot")
    return ". ".join(parts) + "."


def _find_zone_for_merchant(merchant_id: str, zones: list[Zone]) -> int:
    """Find which zone a merchant belongs to."""
    for z in zones:
        if merchant_id in z.merchant_ids:
            return z.id
    return -1


# ══════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════

def load_merchants_from_cache(cache_path: str) -> list[Merchant]:
    """Load merchants from the targets cache JSON.

    Expected format:
    {
        "onboarding_targets": [...],
        "reactivation_targets": [...],
        "visited_ids": [...]
    }
    """
    with open(cache_path) as f:
        data = json.load(f)

    merchants: list[Merchant] = []

    for t in data.get("onboarding_targets", []):
        merchants.append(Merchant(
            id=t.get("id", f"onb_{t.get('phone', t.get('shop_name', ''))}"),
            name=t.get("shop_name", "Unknown"),
            lat=float(t["lat"]),
            lng=float(t["lng"]),
            type="onboarding",
            phone=t.get("phone", ""),
            decline_reason=t.get("decline_reason", ""),
            ambassador_who_visited=t.get("ambassador", ""),
        ))

    for t in data.get("reactivation_targets", []):
        merchants.append(Merchant(
            id=t["merchant_id"],
            name=t.get("business_name", "Unknown"),
            lat=float(t["latitude"]),
            lng=float(t["longitude"]),
            type="reactivation",
            phone=t.get("phone_number", ""),
            days_inactive=t.get("days_since_last_activity"),
            lifetime_tx=t.get("lifetime_tx_count", 0),
        ))

    return merchants


# ══════════════════════════════════════════════════════════════════════
# OUTPUT
# ══════════════════════════════════════════════════════════════════════

def print_zones_summary(zones: list[Zone], merchants: list[Merchant]) -> None:
    """Print zone summary table to terminal."""
    merchant_map = {m.id: m for m in merchants}
    print(f"\n{'Zone':>5} | {'Size':>4} | {'Onb':>3} | {'Rct':>3} | {'Radius':>7} | Center")
    print("-" * 62)
    for z in sorted(zones, key=lambda z: z.id):
        onb = sum(1 for mid in z.merchant_ids
                  if mid in merchant_map and merchant_map[mid].type == "onboarding")
        rct = z.size - onb
        print(f"{z.id:>5} | {z.size:>4} | {onb:>3} | {rct:>3} | "
              f"{z.radius_km:>5.1f}km | ({z.centroid_lat:.4f}, {z.centroid_lng:.4f})")
    print(f"\nTotal: {sum(z.size for z in zones)} merchants in {len(zones)} zones")


def print_routes(routes: list[DailyRoute]) -> None:
    """Print daily route assignments to terminal."""
    for r in routes:
        print(f"\n{'=' * 60}")
        print(f"Ambassador: {r.ambassador}")
        print(f"Date: {r.date}")
        print(f"Zones: {r.zone_ids}")
        print(f"Tasks: {r.size}")
        if not r.tasks:
            print("  (no tasks — pool exhausted)")
            continue
        print(f"{'#':>3} | {'Type':>12} | {'Own':>3} | {'Shop':>25} | Objective")
        print("-" * 96)
        for i, t in enumerate(r.tasks, 1):
            shop = t.shop_name[:25]
            obj = t.objective[:45]
            own = " ✓ " if t.is_affinity else "   "
            print(f"{i:>3} | {t.type:>12} | {own} | {shop:>25} | {obj}")


def routes_to_json(routes: list[DailyRoute]) -> list[dict]:
    """Serialize routes for JSON output."""
    return [
        {
            "ambassador": r.ambassador,
            "date": r.date,
            "zone_ids": r.zone_ids,
            "tasks": [
                {
                    "merchant_id": t.merchant_id,
                    "type": t.type,
                    "shop_name": t.shop_name,
                    "lat": t.lat,
                    "lng": t.lng,
                    "phone": t.phone,
                    "objective": t.objective,
                    "zone_id": t.zone_id,
                    "is_affinity": t.is_affinity,
                }
                for t in r.tasks
            ],
        }
        for r in routes
    ]


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="EXP-009 Directed Day task generator")
    parser.add_argument("--json", required=True, help="Path to targets cache JSON")
    parser.add_argument("--zones-only", action="store_true", help="Only recompute zones, no routes")
    parser.add_argument("--date", default=date.today().isoformat(), help="Route date (YYYY-MM-DD)")
    parser.add_argument("--output", help="Write routes JSON to file")
    args = parser.parse_args()

    # Load merchants
    merchants = load_merchants_from_cache(args.json)
    if not merchants:
        print("ERROR: No merchants loaded from cache.")
        sys.exit(1)

    print(f"Loaded {len(merchants)} merchants "
          f"({sum(1 for m in merchants if m.type == 'onboarding')} onboarding, "
          f"{sum(1 for m in merchants if m.type == 'reactivation')} reactivation)")

    # Layer 1: Compute zones
    zones = compute_zones(merchants)
    adjacency = compute_adjacency(zones)
    print_zones_summary(zones, merchants)

    if args.zones_only:
        return

    # Layer 2: Compose daily routes
    with open(args.json) as f:
        cache_data = json.load(f)
    visited_ids = set(cache_data.get("visited_ids", []))

    routes = compose_daily_routes(
        merchants=merchants,
        zones=zones,
        adjacency=adjacency,
        ambassadors=AMBASSADORS,
        visited_ids=visited_ids,
        route_date=args.date,
    )
    print_routes(routes)

    # Write output
    if args.output:
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "date": args.date,
            "zones": [
                {
                    "id": z.id,
                    "centroid_lat": z.centroid_lat,
                    "centroid_lng": z.centroid_lng,
                    "radius_km": z.radius_km,
                    "merchant_count": z.size,
                }
                for z in zones
            ],
            "routes": routes_to_json(routes),
        }
        Path(args.output).write_text(json.dumps(output_data, indent=2))
        print(f"\nRoutes written to {args.output}")

    # Summary stats
    total_tasks = sum(r.size for r in routes)
    onb_tasks = sum(1 for r in routes for t in r.tasks if t.type == "onboarding")
    rct_tasks = total_tasks - onb_tasks
    print(f"\n--- Summary ---")
    print(f"Total tasks assigned: {total_tasks} ({onb_tasks} onboarding, {rct_tasks} reactivation)")
    print(f"Ambassadors: {len(routes)}")
    print(f"Tasks per ambassador: {', '.join(str(r.size) for r in routes)}")


if __name__ == "__main__":
    main()
