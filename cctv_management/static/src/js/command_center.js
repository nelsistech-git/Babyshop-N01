/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { serializeDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { useDashboardRefresh } from "./dashboard_utils";

const { Component, useState } = owl;
const { DateTime } = luxon;

const SEVERITIES = [
    { key: "critical", label: "Critical", color: "linear-gradient(90deg,#f87171,#dc2626)" },
    { key: "high", label: "High", color: "linear-gradient(90deg,#fb923c,#ea580c)" },
    { key: "medium", label: "Medium", color: "linear-gradient(90deg,#fbbf24,#d97706)" },
    { key: "low", label: "Low", color: "linear-gradient(90deg,#60a5fa,#2563eb)" },
];

const HEALTH = [
    { key: "online", label: "Online", color: "#10b981" },
    { key: "offline", label: "Offline", color: "#ef4444" },
    { key: "unknown", label: "Unknown", color: "#94a3b8" },
];

// Quick-launch 3D buttons. `action` is an XML id of an existing action.
const LAUNCH = [
    { label: "Live Monitor", sub: "All cameras, live", icon: "fa-video-camera", tone: "indigo", action: "cctv_management.action_cctv_live_monitor" },
    { label: "Smart Alerts", sub: "Triage & acknowledge", icon: "fa-bell", tone: "red", action: "cctv_management.action_cctv_alert" },
    { label: "Incidents", sub: "Investigate & close", icon: "fa-shield", tone: "orange", action: "cctv_management.action_cctv_incident" },
    { label: "AI Events", sub: "Detections feed", icon: "fa-magic", tone: "violet", action: "cctv_management.action_cctv_event" },
    { label: "Facility Map", sub: "Camera pins", icon: "fa-map-marker", tone: "green", action: "cctv_management.action_cctv_facility_map" },
    { label: "Heat Map", sub: "Zone x hour", icon: "fa-fire", tone: "pink", action: "cctv_management.action_cctv_heat_map" },
    { label: "Cameras", sub: "Registry & health", icon: "fa-camera", tone: "cyan", action: "cctv_management.action_cctv_camera" },
    { label: "Violations", sub: "Approvals & fines", icon: "fa-gavel", tone: "amber", action: "cctv_management.action_cctv_violation" },
];

const countOf = (group, field) =>
    group.__count !== undefined ? group.__count : group[`${field}_count`] || 0;

class CctvCommandCenter extends Component {
    static template = "cctv_management.CommandCenter";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.launch = LAUNCH;
        this.state = useState({
            loading: true,
            cameras: { online: 0, offline: 0, unknown: 0, total: 0 },
            openAlerts: 0,
            severity: { critical: 0, high: 0, medium: 0, low: 0 },
            incidents: 0,
            eventsToday: 0,
            hours: Array.from({ length: 24 }, () => 0), // index = LOCAL hour of day
            types: [],
            pendingViolations: 0,
            recentAlerts: [],
        });
        // Access check + first load + auto-refresh (interval set in Configuration > Dashboard Access)
        this.dash = useDashboardRefresh("command_center", (silent) => this.reload(silent));
    }

    // ------------------------------------------------------------------ data
    async reload(silent) {
        if (!silent) {
            this.state.loading = true;
        }
        const dayStart = serializeDateTime(DateTime.now().startOf("day"));
        const today = [["event_time", ">=", dayStart]];
        // One section failing (e.g. the user cannot read violations) must not blank the page.
        const safe = (promise, fallback) => promise.catch(() => fallback);
        const orm = this.orm;
        const openAlert = [["state", "in", ["new", "acknowledged"]]];

        const [health, sev, newAlerts, incidents, hourly, types, violations, recent] = await Promise.all([
            safe(orm.readGroup("cctv.camera", [], ["health_status"], ["health_status"], { lazy: false }), []),
            safe(orm.readGroup("cctv.alert", openAlert, ["severity"], ["severity"], { lazy: false }), []),
            safe(orm.searchCount("cctv.alert", [["state", "=", "new"]]), 0),
            safe(orm.searchCount("cctv.incident", [["state", "!=", "closed"]]), 0),
            safe(orm.readGroup("cctv.event", today, ["hour_of_day"], ["hour_of_day"], { lazy: false }), []),
            safe(orm.readGroup("cctv.event", today, ["detection_type"], ["detection_type"], { lazy: false }), []),
            safe(orm.searchCount("cctv.violation", [["state", "in", ["manager_review", "hr_review"]]]), 0),
            safe(
                orm.searchRead("cctv.alert", openAlert, ["name", "severity", "state", "camera_id", "office_id", "create_date"], {
                    limit: 8,
                    order: "create_date desc",
                }),
                []
            ),
        ]);

        const cameras = { online: 0, offline: 0, unknown: 0, total: 0 };
        for (const g of health) {
            const key = g.health_status || "unknown";
            const n = countOf(g, "health_status");
            cameras[key] = (cameras[key] || 0) + n;
            cameras.total += n;
        }

        const severity = { critical: 0, high: 0, medium: 0, low: 0 };
        for (const g of sev) {
            if (g.severity in severity) {
                severity[g.severity] = countOf(g, "severity");
            }
        }

        // hour_of_day is stored in server time (UTC); show it in the browser's local time.
        const offsetMin = -new Date().getTimezoneOffset();
        const hours = Array.from({ length: 24 }, () => 0);
        let eventsToday = 0;
        for (const g of hourly) {
            const n = countOf(g, "hour_of_day");
            const local = (((Math.floor((g.hour_of_day * 60 + offsetMin) / 60) % 24) + 24) % 24);
            hours[local] += n;
            eventsToday += n;
        }

        const typeRows = types
            .map((g) => ({
                key: g.detection_type || "other",
                label: this.prettify(g.detection_type || "other"),
                count: countOf(g, "detection_type"),
            }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 6);

        Object.assign(this.state, {
            cameras,
            openAlerts: newAlerts,
            severity,
            incidents,
            eventsToday,
            hours,
            types: typeRows,
            pendingViolations: violations,
            recentAlerts: recent,
            loading: false,
        });
    }

    prettify(key) {
        return String(key).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }

    // ------------------------------------------------------------------ view model
    get kpis() {
        const s = this.state;
        const peak = this.peakHour;
        return [
            {
                key: "online",
                tone: "green",
                icon: "fa-video-camera",
                value: s.cameras.online,
                suffix: `/ ${s.cameras.total}`,
                label: "Cameras online",
                sub: s.cameras.total ? `${Math.round((s.cameras.online / s.cameras.total) * 100)}% healthy` : "No cameras yet",
                open: () => this.openAction("cctv_management.action_cctv_camera"),
            },
            {
                key: "offline",
                tone: "pink",
                icon: "fa-plug",
                value: s.cameras.offline,
                label: "Cameras offline",
                sub: s.cameras.offline ? "Needs attention" : "All reachable",
                open: () => this.openList("Offline cameras", "cctv.camera", [["health_status", "=", "offline"]], "kanban"),
            },
            {
                key: "alerts",
                tone: "red",
                icon: "fa-bell",
                value: s.openAlerts,
                label: "New alerts",
                sub: s.severity.critical ? `${s.severity.critical} critical open` : "No critical alerts",
                open: () => this.openList("New alerts", "cctv.alert", [["state", "=", "new"]]),
            },
            {
                key: "incidents",
                tone: "orange",
                icon: "fa-shield",
                value: s.incidents,
                label: "Active incidents",
                sub: "Open / investigation / action",
                open: () => this.openList("Active incidents", "cctv.incident", [["state", "!=", "closed"]]),
            },
            {
                key: "events",
                tone: "indigo",
                icon: "fa-magic",
                value: s.eventsToday,
                label: "AI events today",
                sub: peak === null ? "Quiet so far" : `Peak around ${String(peak).padStart(2, "0")}:00`,
                open: () => this.openAction("cctv_management.action_cctv_event"),
            },
            {
                key: "violations",
                tone: "violet",
                icon: "fa-gavel",
                value: s.pendingViolations,
                label: "Pending approvals",
                sub: "Manager / HR review",
                open: () => this.openAction("cctv_management.action_cctv_violation_pending_approval"),
            },
        ];
    }

    get peakHour() {
        const max = Math.max(...this.state.hours);
        return max > 0 ? this.state.hours.indexOf(max) : null;
    }

    get bars() {
        const hours = this.state.hours;
        const max = Math.max(1, ...hours);
        const now = DateTime.now().hour;
        return hours.map((count, h) => ({
            hour: h,
            count,
            style: `height:${count ? Math.max(6, Math.round((count / max) * 100)) : 3}%`,
            empty: !count,
            now: h === now,
            showHour: h % 3 === 0,
        }));
    }

    get healthRows() {
        return HEALTH.map((h) => ({ ...h, count: this.state.cameras[h.key] || 0 }));
    }

    get donutStyle() {
        const total = this.state.cameras.total;
        if (!total) {
            return "background:#e5e7eb";
        }
        let acc = 0;
        const stops = this.healthRows
            .filter((r) => r.count)
            .map((r) => {
                const from = acc;
                acc += (r.count / total) * 100;
                return `${r.color} ${from.toFixed(2)}% ${acc.toFixed(2)}%`;
            });
        return `background:conic-gradient(${stops.join(",")})`;
    }

    get severityRows() {
        const sev = this.state.severity;
        const max = Math.max(1, ...SEVERITIES.map((s) => sev[s.key]));
        return SEVERITIES.map((s) => ({
            ...s,
            count: sev[s.key],
            style: `width:${sev[s.key] ? Math.max(4, Math.round((sev[s.key] / max) * 100)) : 0}%;background:${s.color}`,
        }));
    }

    get typeBars() {
        const max = Math.max(1, ...this.state.types.map((t) => t.count));
        const tones = ["indigo", "violet", "pink", "orange", "cyan", "green"];
        return this.state.types.map((t, i) => ({
            ...t,
            tone: tones[i % tones.length],
            style: `width:${Math.max(4, Math.round((t.count / max) * 100))}%`,
        }));
    }

    toneGradient(tone) {
        const map = {
            indigo: "linear-gradient(90deg,#818cf8,#4f46e5)",
            violet: "linear-gradient(90deg,#c4b5fd,#7c3aed)",
            pink: "linear-gradient(90deg,#f9a8d4,#db2777)",
            orange: "linear-gradient(90deg,#fdba74,#ea580c)",
            cyan: "linear-gradient(90deg,#67e8f9,#0891b2)",
            green: "linear-gradient(90deg,#6ee7b7,#059669)",
        };
        return map[tone] || map.indigo;
    }

    alertAge(a) {
        try {
            return deserializeDateTime(a.create_date).toRelative() || "";
        } catch (e) {
            return "";
        }
    }

    alertTone(a) {
        return { critical: "red", high: "orange", medium: "amber", low: "blue" }[a.severity] || "slate";
    }

    // ------------------------------------------------------------------ navigation
    openAction(xmlId) {
        return this.action.doAction(xmlId);
    }

    openList(name, resModel, domain, viewType = "list") {
        const views = viewType === "kanban"
            ? [[false, "kanban"], [false, "list"], [false, "form"]]
            : [[false, "list"], [false, "form"]];
        return this.action.doAction({ type: "ir.actions.act_window", name, res_model: resModel, views, domain });
    }

    openAlert(alert) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: alert.name,
            res_model: "cctv.alert",
            res_id: alert.id,
            views: [[false, "form"]],
        });
    }
}

registry.category("actions").add("cctv_management.command_center", CctvCommandCenter);
