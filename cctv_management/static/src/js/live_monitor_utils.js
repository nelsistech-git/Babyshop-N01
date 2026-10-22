/** @odoo-module **/
// Pure helpers for the Live Monitor (no Odoo imports, so they can be unit-tested in plain node).

export const ZOOM_MIN = 1;
export const ZOOM_MAX = 8;

/**
 * Pick the columns x rows arrangement that makes the camera pictures as large as
 * possible while ALL `n` cameras stay inside a W x H area (no scrolling).
 *
 * @param {number} n        number of cameras
 * @param {number} W        usable width  (px)
 * @param {number} H        usable height (px)
 * @param {number} gap      gap between tiles (px)
 * @param {number} headerH  height of each tile's title bar (px)
 * @param {number} ar       picture aspect ratio (16/9)
 */
export function bestGrid(n, W, H, gap = 6, headerH = 26, ar = 16 / 9) {
    if (n <= 0) {
        return { cols: 1, rows: 1 };
    }
    let best = null;
    for (let cols = 1; cols <= n; cols++) {
        const rows = Math.ceil(n / cols);
        const cw = (W - gap * (cols - 1)) / cols;
        const ch = (H - gap * (rows - 1)) / rows - headerH;
        if (cw <= 0 || ch <= 0) {
            continue;
        }
        const w = Math.min(cw, ch * ar);
        const area = w * (w / ar);
        const empty = cols * rows - n;
        if (
            !best ||
            area > best.area * 1.01 ||
            (area >= best.area * 0.99 && empty < best.empty)
        ) {
            best = { cols, rows, area, empty };
        }
    }
    if (!best) {
        const cols = Math.ceil(Math.sqrt(n));
        return { cols, rows: Math.ceil(n / cols) };
    }
    return { cols: best.cols, rows: best.rows };
}

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** Keep the zoomed picture covering the viewport (no empty space dragged into view). */
export function clampPan(x, y, s, vw, vh) {
    return {
        x: clamp(x, Math.min(0, vw - vw * s), 0),
        y: clamp(y, Math.min(0, vh - vh * s), 0),
    };
}

/**
 * Zoom by `factor` keeping the point (px, py) - in viewport coordinates - fixed under the cursor.
 * `view` is {s, x, y} where the content is drawn with transform: translate(x,y) scale(s), origin 0 0.
 */
export function zoomAt(view, factor, px, py, vw, vh) {
    const s = clamp(view.s * factor, ZOOM_MIN, ZOOM_MAX);
    if (s <= ZOOM_MIN + 1e-6) {
        return { s: 1, x: 0, y: 0 };
    }
    const ratio = s / view.s;
    const x = px - (px - view.x) * ratio;
    const y = py - (py - view.y) * ratio;
    return { s, ...clampPan(x, y, s, vw, vh) };
}

/** "12s", "3m", "2h" */
export function fmtAge(sec) {
    sec = Math.max(0, Math.round(sec || 0));
    if (sec < 60) {
        return sec + "s";
    }
    if (sec < 3600) {
        return Math.round(sec / 60) + "m";
    }
    return Math.round(sec / 3600) + "h";
}
