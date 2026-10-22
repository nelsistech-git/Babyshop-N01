/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { bestGrid, clampPan, zoomAt, fmtAge, ZOOM_MAX } from "./live_monitor_utils";

const {
    Component, useState, useRef, onWillStart, onMounted, onWillUnmount, useExternalListener,
} = owl;

const GAP = 6;              // px between tiles (keep in sync with $cctv-gap in cctv.scss)
const TILE_HEADER_H = 26;   // px, tile title bar
const POLL_MS = 3000;       // tracking refresh
const COUNTER_EVERY = 5;    // queue / footfall refresh every 5th poll (~15 s)
const EMPTY_TRACKING = Object.freeze({
    health_status: "unknown", frame_w: 0, frame_h: 0, tracks: [], green: 0, red: 0,
    people: 0, alerts: [], caps: [], ai_state: "off", drive: false,
});

class CctvLiveMonitor extends Component {
    static template = "cctv_management.LiveMonitor";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rootRef = useRef("root");
        this.stageRef = useRef("stage");
        this.fsRef = useRef("fs");
        this.fsViewRef = useRef("fsView");
        this.fmtAge = fmtAge;

        this.state = useState({
            groups: [],
            activeGroupId: null,
            cameras: [],
            loading: true,
            // auto-fit layout (recomputed whenever the screen or the camera count changes)
            cols: 1,
            rows: 1,
            rootH: 0,
            // live data
            tracking: {},          // camera id -> get_live_tracking() payload
            natural: {},           // camera id -> natural aspect ratio of the stream picture
            retry: {},             // camera id -> reconnect counter (MJPEG dropped)
            showOverlay: this._loadPref("overlay", true),
            wall: false,           // whole grid in browser full screen
            // single-camera full screen viewer
            fsId: null,
            zoom: { s: 1, x: 0, y: 0 },
            dragging: false,
        });

        this._ptrs = new Map();
        this._tick = 0;
        this._fsRequested = false;

        useExternalListener(window, "resize", () => this.onResize());
        useExternalListener(window, "keydown", (ev) => this.onKey(ev));
        useExternalListener(document, "fullscreenchange", () => this.onFullscreenChange());

        onWillStart(async () => this.loadGroups());
        onMounted(() => {
            this.fitHeight();
            this._ro = new ResizeObserver(() => this.recomputeLayout());
            if (this.stageRef.el) {
                this._ro.observe(this.stageRef.el);
            }
            this.recomputeLayout();
            this._timer = setInterval(() => {
                this._tick += 1;
                this.poll(this._tick % COUNTER_EVERY === 0);
            }, POLL_MS);
            this.poll(true);
        });
        onWillUnmount(() => {
            clearInterval(this._timer);
            if (this._ro) {
                this._ro.disconnect();
            }
            if (document.fullscreenElement) {
                document.exitFullscreen().catch(() => {});
            }
        });
    }

    // ------------------------------------------------------------------ prefs
    _loadPref(key, fallback) {
        try {
            const v = window.localStorage.getItem("cctv_live_" + key);
            return v === null ? fallback : v === "1";
        } catch {
            return fallback;
        }
    }

    _savePref(key, value) {
        try {
            window.localStorage.setItem("cctv_live_" + key, value ? "1" : "0");
        } catch {
            /* private mode etc. - the preference just won't persist */
        }
    }

    // ------------------------------------------------------------------ data
    async loadGroups() {
        const groups = await this.orm.searchRead(
            "cctv.camera.group",
            [],
            ["id", "name", "layout", "camera_ids", "is_default"]
        );
        this.state.groups = groups;
        const defaultGroup = groups.find((g) => g.is_default) || groups[0];
        if (defaultGroup) {
            await this.selectGroup(defaultGroup.id);
        } else {
            this.state.loading = false;
        }
    }

    async selectGroup(groupId) {
        this.state.loading = true;
        this.closeFullscreen();
        this.state.activeGroupId = groupId;
        const group = this.state.groups.find((g) => g.id === groupId);
        const cameras = await this.orm.searchRead(
            "cctv.camera",
            [["id", "in", group.camera_ids]],
            ["id", "name", "health_status", "stream_bridge_url", "ptz_supported", "office_id"]
        );
        // keep the order the grid was configured with
        const order = new Map(group.camera_ids.map((id, i) => [id, i]));
        cameras.sort((a, b) => order.get(a.id) - order.get(b.id));
        this.state.cameras = cameras;
        this.state.tracking = {};
        this.state.loading = false;
        this.recomputeLayout();
        this.poll(true);
    }

    async poll(withCounters = false) {
        const cams = this.state.cameras;
        if (this._polling || document.hidden || !cams.length) {
            return;
        }
        this._polling = true;
        try {
            const data = await this.orm.call(
                "cctv.camera", "get_live_tracking", [cams.map((c) => c.id)],
                { window_seconds: 8, include_counters: withCounters }
            );
            const next = {};
            for (const cam of cams) {
                const d = data[cam.id];
                if (!d) {
                    continue;
                }
                const prev = this.state.tracking[cam.id];
                if (!withCounters && prev) {
                    // queue/footfall are only fetched every ~15 s: keep the last values in between
                    d.queue = prev.queue;
                    d.footfall = prev.footfall;
                }
                next[cam.id] = d;
            }
            this.state.tracking = next;
            this.state.cameras = cams.map((c) =>
                data[c.id] && data[c.id].health_status !== c.health_status
                    ? { ...c, health_status: data[c.id].health_status }
                    : c
            );
        } catch (err) {
            if (!this._warned) {
                this._warned = true;
                console.warn("CCTV live tracking unavailable (upgrade the cctv_management module?)", err);
            }
        } finally {
            this._polling = false;
        }
    }

    // ------------------------------------------------------------------ layout
    onResize() {
        this.fitHeight();
        this.recomputeLayout();
        if (this.state.fsId) {
            this.clampZoom();
        }
    }

    /** Give the page exactly the visible height so the grid never needs a scrollbar. */
    fitHeight() {
        const el = this.rootRef.el;
        if (!el) {
            return;
        }
        const top = el.getBoundingClientRect().top;
        this.state.rootH = Math.max(240, Math.floor(window.innerHeight - top - 2));
    }

    recomputeLayout() {
        const stage = this.stageRef.el;
        if (!stage) {
            return;
        }
        const { cols, rows } = bestGrid(
            this.state.cameras.length, stage.clientWidth, stage.clientHeight, GAP, TILE_HEADER_H
        );
        if (cols !== this.state.cols) {
            this.state.cols = cols;
        }
        if (rows !== this.state.rows) {
            this.state.rows = rows;
        }
    }

    get gridStyle() {
        const { cols, rows } = this.state;
        // two grid units per tile so a short last row can be centred
        return `grid-template-columns: repeat(${cols * 2}, minmax(0, 1fr)); ` +
               `grid-template-rows: repeat(${rows}, minmax(0, 1fr));`;
    }

    tileStyle(index) {
        const n = this.state.cameras.length;
        const cols = this.state.cols;
        const rem = n % cols;
        if (rem && index === n - rem) {
            return `grid-column: ${cols - rem + 1} / span 2;`;
        }
        return "";
    }

    get rootStyle() {
        return this.state.rootH ? `height: ${this.state.rootH}px;` : "";
    }

    // ------------------------------------------------------------------ tracking helpers
    trackOf(cam) {
        return this.state.tracking[cam.id] || EMPTY_TRACKING;
    }

    get totals() {
        let green = 0, red = 0, online = 0;
        for (const cam of this.state.cameras) {
            const t = this.trackOf(cam);
            green += t.green;
            red += t.red;
            if (cam.health_status === "online") {
                online += 1;
            }
        }
        return { green, red, online, cameras: this.state.cameras.length };
    }

    /** One object the panel / tile classes are rendered from. */
    panelModel(cam) {
        const t = this.trackOf(cam);
        const live = t.green + t.red;
        let status = "idle";
        if (t.red > 0) {
            status = "red";
        } else if (live > 0) {
            status = "green";
        }
        return {
            status,
            green: t.green,
            red: t.red,
            people: t.people,
            alerts: t.alerts || [],
            queue: t.queue || null,
            footfall: t.footfall || null,
            tracks: t.tracks,
            caps: t.caps || [],
            aiState: t.ai_state || "off",
            drive: !!t.drive,
        };
    }

    tileClass(cam) {
        const m = this.panelModel(cam);
        return `cctv-tile cctv-tile-${m.status}` +
               (cam.health_status !== "online" ? " cctv-tile-offline" : "");
    }

    /** CSS aspect-ratio of the picture: real stream ratio > AI frame ratio > 16:9. */
    frameAr(cam) {
        const nat = this.state.natural[cam.id];
        if (nat) {
            return nat;
        }
        const t = this.trackOf(cam);
        return t.frame_w && t.frame_h ? t.frame_w / t.frame_h : 16 / 9;
    }

    boxStyle(cam, tr) {
        const t = this.trackOf(cam);
        const fw = t.frame_w, fh = t.frame_h;
        if (!fw || !fh) {
            return "display:none;";
        }
        return `left:${(tr.x / fw) * 100}%;top:${(tr.y / fh) * 100}%;` +
               `width:${(tr.w / fw) * 100}%;height:${(tr.h / fh) * 100}%;`;
    }

    fmtWait(sec) {
        return sec >= 60 ? Math.round(sec / 60) + " min" : sec + " s";
    }

    // ------------------------------------------------------------------ streams
    isMjpeg(url) {
        return !!url && !url.split("?")[0].endsWith(".m3u8");
    }

    streamSrc(cam) {
        const n = this.state.retry[cam.id];
        if (!n) {
            return cam.stream_bridge_url;
        }
        return cam.stream_bridge_url + (cam.stream_bridge_url.includes("?") ? "&" : "?") + "_r=" + n;
    }

    onStreamLoad(cam, ev) {
        const img = ev.target;
        if (img.naturalWidth && img.naturalHeight) {
            const ar = img.naturalWidth / img.naturalHeight;
            if (Math.abs((this.state.natural[cam.id] || 0) - ar) > 0.001) {
                this.state.natural[cam.id] = ar;
            }
        }
    }

    onStreamError(cam) {
        // MJPEG connection dropped: try again in 5 s
        clearTimeout(this._retryTimers?.[cam.id]);
        this._retryTimers = this._retryTimers || {};
        this._retryTimers[cam.id] = setTimeout(() => {
            this.state.retry[cam.id] = (this.state.retry[cam.id] || 0) + 1;
        }, 5000);
    }

    // ------------------------------------------------------------------ toolbar
    toggleOverlay() {
        this.state.showOverlay = !this.state.showOverlay;
        this._savePref("overlay", this.state.showOverlay);
    }

    toggleWall() {
        if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => {});
        } else if (this.rootRef.el && this.rootRef.el.requestFullscreen) {
            this.rootRef.el.requestFullscreen().catch(() => {});
        }
    }

    onFullscreenChange() {
        const fe = document.fullscreenElement;
        this.state.wall = !!fe && fe === this.rootRef.el;
        if (!fe && this.state.fsId && this._fsRequested) {
            // user left browser full screen with Esc: close the single-camera viewer too
            this.closeFullscreen(false);
        }
        setTimeout(() => this.onResize(), 50);
    }

    // ------------------------------------------------------------------ single camera full screen
    get fsCamera() {
        return this.state.cameras.find((c) => c.id === this.state.fsId) || null;
    }

    openFullscreen(camId) {
        this.state.fsId = camId;
        this.state.zoom = { s: 1, x: 0, y: 0 };
        setTimeout(() => {
            const el = this.fsRef.el;
            if (el && el.requestFullscreen) {
                // also works from "wall" mode: the viewer simply becomes the full-screen element
                el.requestFullscreen()
                    .then(() => { this._fsRequested = true; })
                    .catch(() => { /* the fixed-position overlay is the fallback */ });
            }
        }, 0);
    }

    closeFullscreen(exitBrowserFs = true) {
        this.state.fsId = null;
        this.state.zoom = { s: 1, x: 0, y: 0 };
        this.state.dragging = false;
        this._ptrs.clear();
        this._fsRequested = false;
        if (exitBrowserFs && document.fullscreenElement) {
            document.exitFullscreen().catch(() => {});
        }
    }

    stepFullscreen(delta) {
        const cams = this.state.cameras;
        if (!cams.length) {
            return;
        }
        const i = cams.findIndex((c) => c.id === this.state.fsId);
        const next = cams[(i + delta + cams.length) % cams.length];
        this.state.fsId = next.id;
        this.state.zoom = { s: 1, x: 0, y: 0 };
    }

    onKey(ev) {
        if (!this.state.fsId) {
            return;
        }
        switch (ev.key) {
            case "Escape":
                this.closeFullscreen();
                break;
            case "+":
            case "=":
                this.zoomBy(1.4);
                break;
            case "-":
            case "_":
                this.zoomBy(1 / 1.4);
                break;
            case "0":
                this.resetZoom();
                break;
            case "ArrowRight":
                this.stepFullscreen(1);
                break;
            case "ArrowLeft":
                this.stepFullscreen(-1);
                break;
            default:
                return;
        }
        ev.preventDefault();
    }

    // ---- zoom / pan
    get zoomPct() {
        return Math.round(this.state.zoom.s * 100);
    }

    get zoomStyle() {
        const { s, x, y } = this.state.zoom;
        return `transform: translate(${x}px, ${y}px) scale(${s});`;
    }

    _viewRect() {
        const el = this.fsViewRef.el;
        return el ? el.getBoundingClientRect() : { width: 1, height: 1, left: 0, top: 0 };
    }

    zoomBy(factor, px, py) {
        const r = this._viewRect();
        if (px === undefined) {
            px = r.width / 2;
            py = r.height / 2;
        }
        this.state.zoom = zoomAt(this.state.zoom, factor, px, py, r.width, r.height);
    }

    resetZoom() {
        this.state.zoom = { s: 1, x: 0, y: 0 };
    }

    clampZoom() {
        const r = this._viewRect();
        const z = this.state.zoom;
        this.state.zoom = { s: z.s, ...clampPan(z.x, z.y, z.s, r.width, r.height) };
    }

    onWheel(ev) {
        ev.preventDefault();
        const r = this._viewRect();
        this.zoomBy(Math.exp(-ev.deltaY * 0.0016), ev.clientX - r.left, ev.clientY - r.top);
    }

    onDblClick(ev) {
        const r = this._viewRect();
        if (this.state.zoom.s > 1) {
            this.resetZoom();
        } else {
            this.zoomBy(2.5, ev.clientX - r.left, ev.clientY - r.top);
        }
    }

    onPointerDown(ev) {
        if (ev.target.closest(".cctv-fs-bar, .cctv-panel")) {
            return;
        }
        this.fsViewRef.el.setPointerCapture(ev.pointerId);
        this._ptrs.set(ev.pointerId, { x: ev.clientX, y: ev.clientY });
        this.state.dragging = this.state.zoom.s > 1;
    }

    onPointerMove(ev) {
        const prev = this._ptrs.get(ev.pointerId);
        if (!prev) {
            return;
        }
        const cur = { x: ev.clientX, y: ev.clientY };
        const r = this._viewRect();
        if (this._ptrs.size === 1) {
            if (this.state.zoom.s > 1) {
                const z = this.state.zoom;
                this.state.zoom = {
                    s: z.s, ...clampPan(z.x + cur.x - prev.x, z.y + cur.y - prev.y, z.s, r.width, r.height),
                };
            }
        } else if (this._ptrs.size === 2) {
            // pinch: compare the two fingers before / after this move
            const other = [...this._ptrs.entries()].find(([id]) => id !== ev.pointerId)[1];
            const dOld = Math.hypot(prev.x - other.x, prev.y - other.y) || 1;
            const dNew = Math.hypot(cur.x - other.x, cur.y - other.y) || 1;
            const cOld = { x: (prev.x + other.x) / 2, y: (prev.y + other.y) / 2 };
            const cNew = { x: (cur.x + other.x) / 2, y: (cur.y + other.y) / 2 };
            let z = this.state.zoom;
            z = { s: z.s, ...clampPan(z.x + cNew.x - cOld.x, z.y + cNew.y - cOld.y, z.s, r.width, r.height) };
            this.state.zoom = zoomAt(z, dNew / dOld, cNew.x - r.left, cNew.y - r.top, r.width, r.height);
        }
        this._ptrs.set(ev.pointerId, cur);
    }

    onPointerUp(ev) {
        this._ptrs.delete(ev.pointerId);
        if (!this._ptrs.size) {
            this.state.dragging = false;
        }
    }

    get zoomMax() {
        return ZOOM_MAX;
    }

    // ------------------------------------------------------------------ misc
    noop() {}

    openCameraForm(cameraId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cctv.camera",
            res_id: cameraId,
            views: [[false, "form"]],
            target: "new",
        });
    }
}

registry.category("actions").add("cctv_management.live_monitor", CctvLiveMonitor);
