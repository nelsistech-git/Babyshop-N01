/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { createMap, STATUS_COLOR } from "./map_adapters";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const toDate = (s) => (s ? new Date(s.replace(" ", "T") + "Z") : null);
export const fmtDT = (s) => { const d = toDate(s); return d ? d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "—"; };
export const fmtT = (s) => { const d = toDate(s); return d ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"; };
const ago = (s) => {
    const d = toDate(s); if (!d) return "never";
    const m = Math.max(0, Math.round((Date.now() - d.getTime()) / 60000));
    if (m < 1) return "just now"; if (m < 60) return `${m} min ago`;
    if (m < 1440) return `${Math.floor(m / 60)} h ago`; return `${Math.floor(m / 1440)} d ago`;
};
export const localDate = (d = new Date()) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const TF = (b) => (b ? '<b style="color:#166534">TRUE</b>' : '<b style="color:#991b1b">FALSE</b>');

export class NelsisLiveMap extends Component {
    static template = "nelsis_field_tracking.LiveMap";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.canvas = useRef("canvas");
        const ctx = (this.props.action && this.props.action.context) || {};
        this.state = useState({
            employees: [], summary: {}, sites: [], departments: [], filter: "all", search: "", departmentId: "",
            date: ctx.focus_date || localDate(), selectedId: ctx.focus_employee_id || null,
            route: null, auto: true, provider: "", loading: true, updated: "", error: "",
        });
        this.map = null;
        this.timer = null;
        onMounted(() => this.start());
        onWillUnmount(() => { clearInterval(this.timer); if (this.map) this.map.destroy(); });
    }

    async start() {
        const data = await this.fetch();
        if (!data) return;
        const { adapter, provider } = await createMap(this.canvas.el, data.google_key);
        this.map = adapter;
        this.state.provider = provider;
        this.renderMarkers(true);
        if (this.state.selectedId) await this.select(this.state.selectedId, true);
        this.timer = setInterval(() => this.state.auto && this.refresh(), 15000);
    }

    async fetch() {
        const f = { date: this.state.date, department_id: this.state.departmentId || false };
        try {
            const data = await this.orm.call("nelsis.location.log", "get_live_map_data", [], { filters: f });
            if (data.error) { this.state.error = "You need the Field Force Administrator role."; return null; }
            Object.assign(this.state, {
                employees: data.employees, summary: data.summary, sites: data.sites, departments: data.departments,
                loading: false, updated: new Date().toLocaleTimeString(),
            });
            return data;
        } catch (e) {
            this.state.error = "Could not load live data."; this.state.loading = false; return null;
        }
    }

    async refresh() {
        await this.fetch();
        this.renderMarkers(false);
        if (this.state.selectedId && this.state.date === localDate()) {
            await this.loadRoute(false);
        }
    }

    colorOf(e) {
        if (e.flags) return STATUS_COLOR.flagged;
        return e.online ? STATUS_COLOR.online : STATUS_COLOR.offline;
    }

    get filtered() {
        const s = this.state.search.trim().toLowerCase();
        return this.state.employees.filter((e) => {
            if (s && !e.name.toLowerCase().includes(s)) return false;
            switch (this.state.filter) {
                case "online": return e.online;
                case "offline": return !e.online;
                case "in": return e.attendance === "punched_in";
                case "flagged": return e.flags > 0;
                default: return true;
            }
        });
    }

    get selected() { return this.state.employees.find((e) => e.id === this.state.selectedId); }

    renderMarkers(fit) {
        if (!this.map) return;
        const items = this.filtered.filter((e) => e.lat !== null && e.lng !== null).map((e) => ({
            id: e.id, lat: e.lat, lng: e.lng, color: this.colorOf(e), title: e.name,
        }));
        this.map.setEmployees(items, (id) => this.select(id));
        if (fit && !this.state.selectedId) this.map.fit(items);
    }

    popupHtml(e) {
        return `<div style="min-width:190px"><b>${esc(e.name)}</b><br><small>${esc(e.job)} ${e.department ? "· " + esc(e.department) : ""}</small>
          <hr style="margin:6px 0"><div>${e.online ? "🟢 Online" : "⚪ Offline"} · last seen ${ago(e.last_seen)}</div>
          <div>🔋 ${e.battery || 0}% · ${e.distance_km} km today</div></div>`;
    }

    async select(id, silent) {
        this.state.selectedId = id;
        const e = this.selected;
        if (e && this.map && e.lat !== null) {
            this.map.focus(e.lat, e.lng);
            if (!silent) this.map.popupFor(id, this.popupHtml(e));
        }
        await this.loadRoute(true);
    }

    pointHtml(p) {
        return `<div style="min-width:210px"><b>${fmtT(p.time)}</b> <small>(${esc(p.source)})</small><br>
          Phone time: ${fmtDT(p.time)}<br>Server time: ${fmtDT(p.server_time)}<br>
          Sync delay: ${p.delay_min} min · Accuracy: ${Math.round(p.acc)} m<br>
          Genuine: ${TF(p.genuine)} · Mock GPS: ${p.mock ? "YES" : "no"}<br>
          Time check: ${esc(p.trust)} ${p.jump ? "· GPS JUMP" : ""}</div>`;
    }
    punchHtml(p) {
        return `<div style="min-width:210px"><b>Punch ${p.type === "in" ? "IN" : "OUT"}</b> — ${fmtDT(p.time)}<br>
          Location check: <b>${esc(p.status)}</b>${p.site ? " (" + esc(p.site) + ")" : ""}<br>
          Distance to site: ${Math.round(p.distance_m)} m<br>Genuine: ${TF(p.genuine)} · Offline punch: ${p.offline ? "YES" : "no"}</div>`;
    }

    async loadRoute(fit) {
        const id = this.state.selectedId;
        if (!id) return;
        const r = await this.orm.call("nelsis.location.log", "get_route_data", [id, this.state.date]);
        this.state.route = r;
        if (!this.map) return;
        const pts = r.points.map((p) => ({ ...p, html: this.pointHtml(p) }));
        const pun = r.punches.map((p) => ({ ...p, html: this.punchHtml(p) }));
        this.map.drawRoute(pts, pun, this.state.sites);
        if (fit) {
            const all = [...pts, ...pun];
            if (all.length) this.map.fit(all);
        }
    }

    onFilterChange() { this.renderMarkers(false); }
    setFilter(f) { this.state.filter = f; this.renderMarkers(false); }
    async onDeptChange(ev) { this.state.departmentId = ev.target.value; await this.refresh(); }
    async onDateChange(ev) {
        this.state.date = ev.target.value;
        await this.fetch();
        this.renderMarkers(false);
        if (this.state.selectedId) await this.loadRoute(true);
    }
    toggleAuto() { this.state.auto = !this.state.auto; }
    closePanel() {
        this.state.selectedId = null; this.state.route = null;
        if (this.map) this.map.clearOverlay();
    }
    openEmployee() {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "hr.employee", res_id: this.state.selectedId, views: [[false, "form"]] });
    }
    openLogs() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Location Logs", res_model: "nelsis.location.log",
            views: [[false, "tree"], [false, "form"]], domain: [["employee_id", "=", this.state.selectedId], ["log_date", "=", this.state.date]],
        });
    }
    statusLabel(e) {
        return { punched_in: "Punched in", punched_out: "Punched out", no_attendance: "No attendance" }[e.attendance];
    }
    ago(s) { return ago(s); }
    fmtT(s) { return fmtT(s); }
    fmtDT(s) { return fmtDT(s); }
    get routeStats() {
        const r = this.state.route;
        if (!r) return null;
        const bad = r.points.filter((p) => !p.genuine).length;
        const late = r.points.filter((p) => p.trust === "delayed").length;
        return { total: r.points.length, bad, late, km: r.distance_km };
    }
}

registry.category("actions").add("nelsis_live_map", NelsisLiveMap);
