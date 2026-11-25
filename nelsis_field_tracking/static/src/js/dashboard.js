/** @odoo-module **/
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onPatched, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";

const localDate = (d) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const PALETTE = ["#0b5fb8", "#7c3aed", "#4b1a7a", "#16a34a", "#f59e0b", "#dc2626", "#06b6d4", "#64748b"];

export class NelsisDashboard extends Component {
    static template = "nelsis_field_tracking.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const today = new Date();
        const from = new Date(today.getTime() - 13 * 864e5);
        this.state = useState({
            data: null, from: localDate(from), to: localDate(today), dept: "", loading: true,
        });
        this.refs = { trend: useRef("trend"), hours: useRef("hours"), dist: useRef("dist"), flags: useRef("flags"), exp: useRef("exp"), adv: useRef("adv") };
        this.charts = {};
        onWillStart(async () => { await loadBundle("web.chartjs_lib"); });
        onMounted(() => this.load());
        onPatched(() => { if (this.needDraw) { this.needDraw = false; this.draw(); } });
        onWillUnmount(() => Object.values(this.charts).forEach((c) => c.destroy()));
    }

    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("nelsis.location.log", "get_dashboard_data", [this.state.from, this.state.to, this.state.dept || false]);
        this.state.loading = false;
        this.needDraw = true; // canvases exist only after the next patch
    }

    mk(key, cfg) {
        const el = this.refs[key] && this.refs[key].el;
        if (!el) return;
        if (this.charts[key]) this.charts[key].destroy();
        this.charts[key] = new window.Chart(el, cfg);
    }

    draw() {
        const d = this.state.data;
        if (!d || !d.kpis) return;
        const grid = { color: "rgba(100,116,139,.15)" };
        const base = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } };
        this.mk("trend", {
            type: "line",
            data: { labels: d.attendance_trend.labels, datasets: [{ data: d.attendance_trend.values, borderColor: "#4b1a7a", backgroundColor: "rgba(124,58,237,.18)", fill: true, tension: 0.4, pointRadius: 3 }] },
            options: { ...base, scales: { y: { beginAtZero: true, grid, ticks: { precision: 0 } }, x: { grid: { display: false } } } },
        });
        this.mk("hours", {
            type: "bar",
            data: { labels: d.top_hours.map((x) => x[0]), datasets: [{ data: d.top_hours.map((x) => x[1]), backgroundColor: "#0b5fb8", borderRadius: 8 }] },
            options: { ...base, indexAxis: "y", scales: { x: { grid }, y: { grid: { display: false } } } },
        });
        this.mk("dist", {
            type: "bar",
            data: { labels: d.top_distance.map((x) => x[0]), datasets: [{ data: d.top_distance.map((x) => x[1]), backgroundColor: "#7c3aed", borderRadius: 8 }] },
            options: { ...base, indexAxis: "y", scales: { x: { grid }, y: { grid: { display: false } } } },
        });
        const fl = Object.entries(d.flags);
        this.mk("flags", {
            type: "doughnut",
            data: { labels: fl.map((x) => x[0]), datasets: [{ data: fl.map((x) => x[1]), backgroundColor: PALETTE, borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: "68%", plugins: { legend: { position: "right" } } },
        });
        if (d.expense_by_state) {
            const ex = Object.entries(d.expense_by_state);
            this.mk("exp", {
                type: "bar",
                data: { labels: ex.map((x) => x[0]), datasets: [{ data: ex.map((x) => x[1]), backgroundColor: PALETTE, borderRadius: 8 }] },
                options: { ...base, scales: { y: { beginAtZero: true, grid }, x: { grid: { display: false } } } },
            });
        }
        if (d.advance_by_state) {
            const ad = Object.entries(d.advance_by_state);
            this.mk("adv", {
                type: "doughnut",
                data: { labels: ad.map((x) => x[0]), datasets: [{ data: ad.map((x) => x[1]), backgroundColor: PALETTE, borderWidth: 0 }] },
                options: { responsive: true, maintainAspectRatio: false, cutout: "65%", plugins: { legend: { position: "right" } } },
            });
        }
    }

    onChange(field, ev) { this.state[field] = ev.target.value; this.load(); }
    openMap() { this.action.doAction("nelsis_field_tracking.nelsis_live_map_action"); }
    fmt(n) { return new Intl.NumberFormat().format(Math.round(n || 0)); }
}

registry.category("actions").add("nelsis_dashboard", NelsisDashboard);
