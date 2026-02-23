/* EXP-009 Directed Day Dashboard — Client-side rendering */

(function () {
    "use strict";

    // ── Helpers ──────────────────────────────────────────────────────

    const $ = (id) => document.getElementById(id);
    const esc = (s) => String(s).replace(/</g, "&lt;").replace(/>/g, "&gt;");

    function badge(text, cls) {
        return `<span class="badge badge-${cls}">${esc(text)}</span>`;
    }

    function statBox(value, label) {
        return `<div class="stat-box"><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div>`;
    }

    function pct(n, d) {
        if (!d) return "0%";
        return (n / d * 100).toFixed(0) + "%";
    }

    function hasPhone(t) {
        const p = t.phone || t.phone_number || "";
        return p.replace(/\D/g, "").length >= 7;
    }

    // ── Zone colors ──────────────────────────────────────────────────

    const ZONE_COLORS = [
        "#B8992E", "#7BC4E8", "#FF4D9D", "#16a34a", "#dc2626",
        "#8b5cf6", "#f97316", "#06b6d4", "#ec4899", "#84cc16",
        "#a855f7", "#14b8a6", "#f43f5e", "#6366f1", "#22c55e",
        "#eab308", "#0ea5e9", "#d946ef", "#10b981", "#ef4444",
        "#3b82f6", "#f59e0b", "#8b5cf6", "#06b6d4", "#ec4899",
        "#84cc16", "#a855f7", "#14b8a6", "#f43f5e", "#6366f1",
    ];

    function zoneColor(zoneId) {
        return ZONE_COLORS[(zoneId - 1) % ZONE_COLORS.length];
    }

    // ══════════════════════════════════════════════════════════════════
    // CARD 1: Target Pool Overview (with phone tiers)
    // ══════════════════════════════════════════════════════════════════

    function renderPoolCard() {
        const onb = DATA.onboarding_targets || [];
        const react = DATA.reactivation_targets || [];
        const total = onb.length + react.length;
        const visited = (DATA.visited_ids || []).length;
        const remaining = total - visited;

        const onbT1 = onb.filter(t => hasPhone(t));
        const onbT2 = onb.filter(t => !hasPhone(t));

        $("pool-stats").innerHTML = [
            statBox(total, "Total Targets"),
            statBox(onbT1.length, "Onb T1 \u2014 has \ud83d\udcf1"),
            statBox(onbT2.length, "Onb T2 \u2014 no \ud83d\udcf1"),
            statBox(react.length, "Reactivation"),
            statBox(remaining, "Remaining"),
        ].join("");

        // Pool breakdown table — T1 first, then T2, then reactivation
        let rows = "";

        // T1 onboarding (first 15)
        for (const t of onbT1.slice(0, 15)) {
            rows += `<tr>
                <td>${badge("Onboarding", "onboarding")}${badge("T1", "tier1")}</td>
                <td>${esc(t.shop_name || t.business_name || "\u2014")}</td>
                <td>${esc(t.phone || "\u2014")}</td>
                <td>${t.lat ? t.lat.toFixed(4) : "\u2014"}, ${t.lng ? t.lng.toFixed(4) : "\u2014"}</td>
                <td>${esc(t.decline_reason || "\u2014")}</td>
            </tr>`;
        }

        // T2 onboarding (first 10)
        for (const t of onbT2.slice(0, 10)) {
            rows += `<tr>
                <td>${badge("Onboarding", "onboarding")}${badge("T2", "tier2")}</td>
                <td>${esc(t.shop_name || t.business_name || "\u2014")}</td>
                <td style="color:var(--warning)">\u2014 no phone</td>
                <td>${t.lat ? t.lat.toFixed(4) : "\u2014"}, ${t.lng ? t.lng.toFixed(4) : "\u2014"}</td>
                <td>${esc(t.decline_reason || "\u2014")}</td>
            </tr>`;
        }

        // Reactivation (first 10)
        for (const t of react.slice(0, 10)) {
            const days = t.days_since_last_activity;
            const daysText = days != null ? `${days}d ago` : "Never";
            rows += `<tr>
                <td>${badge("Reactivation", "reactivation")}</td>
                <td>${esc(t.business_name || "\u2014")}</td>
                <td>${esc(t.phone_number || "\u2014")}</td>
                <td>${t.latitude ? parseFloat(t.latitude).toFixed(4) : "\u2014"}, ${t.longitude ? parseFloat(t.longitude).toFixed(4) : "\u2014"}</td>
                <td>Last active: ${daysText}</td>
            </tr>`;
        }

        const shown = Math.min(onbT1.length, 15) + Math.min(onbT2.length, 10) + Math.min(react.length, 10);
        const truncated = total > shown ? `<div class="insight">Showing ${shown} of ${total} targets. T1 (has phone) prioritized in route composition.</div>` : "";

        $("pool-table-container").innerHTML = `
            <table>
                <thead><tr>
                    <th>Type</th><th>Shop</th><th>Phone</th><th>Location</th><th>Detail</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
            ${truncated}
        `;
    }

    // ══════════════════════════════════════════════════════════════════
    // CARD 2: Geographic Zones — Leaflet map with cluster overlays
    // ══════════════════════════════════════════════════════════════════

    // ── Convex hull (Graham scan) ────────────────────────────────────

    function cross(O, A, B) {
        return (A[0] - O[0]) * (B[1] - O[1]) - (A[1] - O[1]) * (B[0] - O[0]);
    }

    function convexHull(points) {
        if (points.length <= 1) return points.slice();
        const pts = points.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
        const n = pts.length;
        if (n <= 2) return pts;
        const lower = [];
        for (const p of pts) {
            while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
            lower.push(p);
        }
        const upper = [];
        for (let i = n - 1; i >= 0; i--) {
            const p = pts[i];
            while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
            upper.push(p);
        }
        lower.pop();
        upper.pop();
        return lower.concat(upper);
    }

    function expandHullGeo(hull, degrees) {
        if (hull.length < 3) return hull;
        let cx = 0, cy = 0;
        for (const p of hull) { cx += p[0]; cy += p[1]; }
        cx /= hull.length; cy /= hull.length;
        return hull.map(p => {
            const dx = p[0] - cx, dy = p[1] - cy;
            const dist = Math.sqrt(dx * dx + dy * dy) || 0.0001;
            return [p[0] + (dx / dist) * degrees, p[1] + (dy / dist) * degrees];
        });
    }

    function renderZonesCard() {
        const zones = DATA.zones || [];
        const onb = DATA.onboarding_targets || [];
        const react = DATA.reactivation_targets || [];

        if (!zones.length) {
            $("zone-map").innerHTML = "<p style='color:var(--text-secondary); padding:2rem;'>No zones computed yet. Run with --generate first.</p>";
            return;
        }

        // ── Build merchant lookup by ID ──────────────────────────────
        const merchantById = {};
        for (const t of onb) {
            if (t.lat && t.lng) {
                merchantById[t.id] = { lat: t.lat, lng: t.lng, type: "onboarding", name: t.shop_name || "Unknown", phone: t.phone || "" };
            }
        }
        for (const t of react) {
            if (t.latitude && t.longitude) {
                const id = t.merchant_id || t.id;
                merchantById[id] = { lat: parseFloat(t.latitude), lng: parseFloat(t.longitude), type: "reactivation", name: t.business_name || "Unknown", phone: t.phone_number || "" };
            }
        }

        // ── Build zone → merchants mapping ───────────────────────────
        const zoneMerchants = {};
        for (const z of zones) {
            zoneMerchants[z.id] = [];
            for (const mid of (z.merchant_ids || [])) {
                if (merchantById[mid]) {
                    zoneMerchants[z.id].push({ ...merchantById[mid], id: mid });
                }
            }
        }

        // ── Check Leaflet available ──────────────────────────────────
        if (typeof L === "undefined") {
            $("zone-map").innerHTML = "<p style='color:var(--text-secondary); padding:2rem;'>Map requires internet connection for map tiles.</p>";
            renderZoneTable(zones, zoneMerchants);
            renderZoneLegend(zones, onb, react);
            return;
        }

        // ── Initialize Leaflet map ───────────────────────────────────
        $("zone-map").innerHTML = "";
        const map = L.map("zone-map", {
            zoomControl: true,
            scrollWheelZoom: true,
        });

        // CartoDB Positron — clean light tiles
        L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
            attribution: '\u00a9 <a href="https://www.openstreetmap.org/copyright">OSM</a> \u00a9 <a href="https://carto.com/">CARTO</a>',
            maxZoom: 19,
            subdomains: "abcd",
        }).addTo(map);

        // Fit bounds to all merchants
        const allLatLngs = Object.values(merchantById).map(m => [m.lat, m.lng]);
        if (allLatLngs.length) {
            map.fitBounds(L.latLngBounds(allLatLngs), { padding: [40, 40] });
        }

        // ── Draw zone regions ────────────────────────────────────────
        for (const z of zones) {
            const members = zoneMerchants[z.id] || [];
            if (!members.length) continue;
            const color = zoneColor(z.id);
            const pts = members.map(m => [m.lat, m.lng]);
            const onbCount = members.filter(m => m.type === "onboarding").length;
            const rctCount = members.length - onbCount;

            let shape;
            if (pts.length <= 2) {
                const radius = Math.max(z.radius_km * 1000, 150) + 120;
                shape = L.circle([z.centroid_lat, z.centroid_lng], {
                    radius: radius,
                    color: color, fillColor: color, fillOpacity: 0.15,
                    weight: 1.5, opacity: 0.5, dashArray: "5 4",
                });
            } else {
                const hull = convexHull(pts);
                const expanded = expandHullGeo(hull, 0.0012);
                shape = L.polygon(expanded, {
                    color: color, fillColor: color, fillOpacity: 0.15,
                    weight: 1.5, opacity: 0.5, dashArray: "5 4",
                });
            }

            const tipHtml = `<div style="font-family:'DM Sans',sans-serif;font-weight:600;border-left:3px solid ${color};padding-left:8px;margin-bottom:3px;">Zone ${z.id}</div>` +
                `<div style="color:#6B6B6B;font-size:0.82rem;">${members.length} merchant${members.length !== 1 ? "s" : ""} \u00b7 ${z.radius_km} km<br>` +
                `<span style="color:#2980b9">\u25cf</span> ${onbCount} onboarding ` +
                `<span style="color:var(--zar-gold-dark,#9A7E24)">\u25c6</span> ${rctCount} reactivation</div>`;

            shape.bindTooltip(tipHtml, { sticky: true, className: "zone-tip" });
            shape.on("mouseover", function () {
                this.setStyle({ fillOpacity: 0.32, weight: 2.5, opacity: 0.85 });
            });
            shape.on("mouseout", function () {
                this.setStyle({ fillOpacity: 0.15, weight: 1.5, opacity: 0.5 });
            });
            shape.addTo(map);
        }

        // ── Draw merchant markers ────────────────────────────────────
        for (const z of zones) {
            const members = zoneMerchants[z.id] || [];
            const color = zoneColor(z.id);
            for (const m of members) {
                if (m.type === "onboarding") {
                    L.circleMarker([m.lat, m.lng], {
                        radius: 5, color: "white", weight: 1.5,
                        fillColor: color, fillOpacity: 1,
                    }).bindTooltip(esc(m.name), { direction: "top", offset: [0, -6] }).addTo(map);
                } else {
                    const s = 12;
                    L.marker([m.lat, m.lng], {
                        icon: L.divIcon({
                            className: "dm-icon",
                            html: `<svg width="${s}" height="${s}"><polygon points="${s/2},0.5 ${s-0.5},${s/2} ${s/2},${s-0.5} 0.5,${s/2}" fill="${color}" stroke="white" stroke-width="1.5"/></svg>`,
                            iconSize: [s, s], iconAnchor: [s / 2, s / 2],
                        }),
                    }).bindTooltip(esc(m.name), { direction: "top", offset: [0, -6] }).addTo(map);
                }
            }
        }

        // ── Zone labels at centroids ─────────────────────────────────
        for (const z of zones) {
            if (!(zoneMerchants[z.id] || []).length) continue;
            const color = zoneColor(z.id);
            L.marker([z.centroid_lat, z.centroid_lng], {
                icon: L.divIcon({
                    className: "zone-label-icon",
                    html: `<div style="background:${color};color:white;padding:1px 5px;border-radius:5px;font-size:10px;font-weight:700;font-family:'DM Sans',sans-serif;white-space:nowrap;border:1px solid rgba(255,255,255,0.8);line-height:1.4;text-align:center;">Z${z.id}</div>`,
                    iconSize: null, iconAnchor: [14, 8],
                }),
                interactive: false,
                zIndexOffset: 1000,
            }).addTo(map);
        }

        // ── Legend + table ────────────────────────────────────────────
        renderZoneLegend(zones, onb, react);
        renderZoneTable(zones, zoneMerchants);
    }

    function renderZoneLegend(zones, onb, react) {
        const totalOnb = onb.filter(t => t.lat && t.lng).length;
        const totalRct = react.filter(t => t.latitude && t.longitude).length;
        $("zone-legend").innerHTML = `
            <div class="legend-row">
                <div class="legend-item">
                    <svg width="14" height="14"><circle cx="7" cy="7" r="5" fill="#6B6B6B" stroke="white" stroke-width="1.5"/></svg>
                    <span>Onboarding target</span>
                </div>
                <div class="legend-item">
                    <svg width="14" height="14"><polygon points="7,1 13,7 7,13 1,7" fill="#6B6B6B" stroke="white" stroke-width="1.5"/></svg>
                    <span>Reactivation target</span>
                </div>
                <div class="legend-sep"></div>
                <div class="legend-summary">${zones.length} zones \u00b7 ${totalOnb} onboarding \u00b7 ${totalRct} reactivation</div>
            </div>
        `;
    }

    function renderZoneTable(zones, zoneMerchants) {
        let zoneRows = "";
        for (const z of zones) {
            const members = zoneMerchants[z.id] || [];
            const onbCount = members.filter(m => m.type === "onboarding").length;
            const rctCount = members.length - onbCount;
            zoneRows += `<tr>
                <td><div class="zone-color" style="background:${zoneColor(z.id)}; display:inline-block; width:12px; height:12px; border-radius:3px; vertical-align:middle;"></div> Zone ${z.id}</td>
                <td>${z.merchant_count}</td>
                <td>${onbCount}</td>
                <td>${rctCount}</td>
                <td>${z.radius_km} km</td>
                <td>${z.centroid_lat.toFixed(4)}, ${z.centroid_lng.toFixed(4)}</td>
            </tr>`;
        }
        $("zone-table-container").innerHTML = `
            <table>
                <thead><tr><th>Zone</th><th>Total</th><th>Onb</th><th>React</th><th>Radius</th><th>Center</th></tr></thead>
                <tbody>${zoneRows}</tbody>
            </table>
        `;
    }

    // ══════════════════════════════════════════════════════════════════
    // CARD 3: Daily Routes
    // ══════════════════════════════════════════════════════════════════

    function renderRoutesCard() {
        const routes = DATA.routes || [];

        if (!routes.length) {
            $("routes-container").innerHTML = `
                <div class="insight">No routes generated yet. Run: <code>python3 run.py --json targets_cache.json --generate</code></div>
            `;
            return;
        }

        let html = "";
        for (const route of routes) {
            const tasks = route.tasks || [];
            const onbCount = tasks.filter(t => t.type === "onboarding").length;
            const rctCount = tasks.length - onbCount;

            let taskRows = "";
            for (let i = 0; i < tasks.length; i++) {
                const t = tasks[i];
                const typeBadge = t.type === "onboarding"
                    ? badge("Onboarding", "onboarding")
                    : badge("Reactivation", "reactivation");
                const mapLink = t.lat && t.lng
                    ? `<a href="https://www.google.com/maps?q=${t.lat},${t.lng}" target="_blank" style="color:var(--zar-gold-dark); text-decoration:none;">\ud83d\udccd</a>`
                    : "";
                const affinityTag = t.is_affinity ? " " + badge("own", "affinity") : "";
                const phoneBadge = t.type === "onboarding"
                    ? (t.phone && t.phone.replace(/\D/g, "").length >= 7
                        ? " " + badge("T1", "tier1")
                        : " " + badge("T2", "tier2"))
                    : "";

                taskRows += `<tr>
                    <td>${i + 1}</td>
                    <td>${typeBadge}${affinityTag}${phoneBadge}</td>
                    <td>${esc(t.shop_name)}</td>
                    <td>${esc(t.phone || "\u2014")}</td>
                    <td>${mapLink}</td>
                    <td style="font-size:0.8rem; max-width:250px;">${esc(t.objective)}</td>
                </tr>`;
            }

            html += `
                <div class="route-card">
                    <div class="route-header">
                        <div class="route-ambassador">${esc(route.ambassador)}</div>
                        <div class="route-meta">
                            ${route.date} \u00b7 Zones ${(route.zone_ids || []).join(", ")} \u00b7
                            ${onbCount} onb + ${rctCount} react
                        </div>
                    </div>
                    <table>
                        <thead><tr><th>#</th><th>Type</th><th>Shop</th><th>Phone</th><th>Map</th><th>Objective</th></tr></thead>
                        <tbody>${taskRows}</tbody>
                    </table>
                </div>
            `;
        }

        $("routes-container").innerHTML = html;
    }

    // ══════════════════════════════════════════════════════════════════
    // CARD 4: Outcome Tracking
    // ══════════════════════════════════════════════════════════════════

    function renderOutcomesCard() {
        const outcomes = DATA.outcomes || [];

        if (!outcomes.length) {
            $("outcome-stats").innerHTML = [
                statBox("\u2014", "Directed Visits"),
                statBox("\u2014", "Onboarded"),
                statBox("\u2014", "Reactivated"),
                statBox("\u2014", "Conversion"),
            ].join("");
            $("outcome-table-container").innerHTML = `
                <div class="insight">No outcome data yet. Outcomes are tracked after directed visits are logged in the visit sheet and verified against the database.</div>
            `;
            return;
        }

        const totalVisits = outcomes.length;
        const onbVisits = outcomes.filter(o => o.type === "onboarding");
        const rctVisits = outcomes.filter(o => o.type === "reactivation");
        const onbConverted = onbVisits.filter(o => o.converted).length;
        const rctConverted = rctVisits.filter(o => o.converted).length;

        $("outcome-stats").innerHTML = [
            statBox(totalVisits, "Directed Visits"),
            statBox(`${onbConverted}/${onbVisits.length}`, "Onboarded"),
            statBox(`${rctConverted}/${rctVisits.length}`, "Reactivated"),
            statBox(pct(onbConverted + rctConverted, totalVisits), "Overall Rate"),
        ].join("");

        let rows = "";
        for (const o of outcomes) {
            const typeBadge = o.type === "onboarding"
                ? badge("Onboarding", "onboarding")
                : badge("Reactivation", "reactivation");
            const statusBadge = o.converted
                ? badge("Converted", "success")
                : badge("Pending", "pending");

            rows += `<tr>
                <td>${esc(o.date || "\u2014")}</td>
                <td>${esc(o.ambassador || "\u2014")}</td>
                <td>${typeBadge}</td>
                <td>${esc(o.shop_name || "\u2014")}</td>
                <td>${statusBadge}</td>
                <td>${o.hours_after_visit != null ? o.hours_after_visit + "h" : "\u2014"}</td>
            </tr>`;
        }

        $("outcome-table-container").innerHTML = `
            <table>
                <thead><tr><th>Date</th><th>Ambassador</th><th>Type</th><th>Shop</th><th>Status</th><th>Time to Convert</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>
        `;

        if (onbVisits.length >= 10 || rctVisits.length >= 10) {
            const onbRate = onbVisits.length ? (onbConverted / onbVisits.length * 100).toFixed(0) : 0;
            const rctRate = rctVisits.length ? (rctConverted / rctVisits.length * 100).toFixed(0) : 0;
            const onbVerdict = onbRate >= 30 ? "ON TARGET" : onbRate >= 15 ? "DIRECTIONAL" : "BELOW TARGET";
            const rctVerdict = rctRate >= 40 ? "ON TARGET" : rctRate >= 20 ? "DIRECTIONAL" : "BELOW TARGET";

            $("outcome-insight").style.display = "block";
            $("outcome-insight").innerHTML = `
                <strong>Onboarding:</strong> ${onbRate}% conversion (${onbConverted}/${onbVisits.length}) \u2014 ${onbVerdict}<br>
                <strong>Reactivation:</strong> ${rctRate}% conversion (${rctConverted}/${rctVisits.length}) \u2014 ${rctVerdict}
            `;
        }
    }

    // ── Init ─────────────────────────────────────────────────────────

    function init() {
        if (typeof DATA === "undefined") {
            document.body.innerHTML = "<h1>No data loaded</h1><p>Run: python3 run.py --json targets_cache.json</p>";
            return;
        }

        renderPoolCard();
        renderZonesCard();
        renderRoutesCard();
        renderOutcomesCard();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
