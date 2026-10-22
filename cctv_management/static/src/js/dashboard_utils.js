/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { useState, onWillStart, onMounted, onWillUnmount } = owl;

/**
 * Shared by the Facility Map and the Heat Map.
 *
 * - asks the server whether this user may open the dashboard (Configuration > Dashboard Access)
 * - runs `loadFn(silent)` once before the first render, then every `refresh_seconds`
 *   (setting on the same screen; 0 = off)
 * - skips ticks while the browser tab is hidden and catches up when it becomes visible again
 * - never runs two loads at once
 *
 * `loadFn(silent)` must reload the data; with silent=true it must not show the loading
 * placeholder, so the page does not flicker.
 */
export function useDashboardRefresh(key, loadFn) {
    const orm = useService("orm");
    const state = useState({
        allowed: true,
        missing: [],
        refreshSeconds: 0,
        lastUpdated: "",
    });
    let timer = null;
    let busy = false;
    let lastRun = 0;

    const run = async (silent) => {
        if (busy || !state.allowed || state.missing.length) {
            return;
        }
        busy = true;
        try {
            await loadFn(silent);
            state.lastUpdated = new Date().toLocaleTimeString();
        } finally {
            busy = false;
            lastRun = Date.now();
        }
    };

    const onVisibility = () => {
        const every = state.refreshSeconds * 1000;
        if (!document.hidden && every && Date.now() - lastRun >= every) {
            run(true);
        }
    };

    onWillStart(async () => {
        const res = await orm.call("cctv.dashboard.access", "get_dashboard_state", [key]);
        state.allowed = res.allowed;
        state.missing = res.missing_models || [];
        state.refreshSeconds = res.refresh_seconds || 0;
        await run(false);
    });

    onMounted(() => {
        if (state.refreshSeconds > 0) {
            timer = setInterval(() => {
                if (!document.hidden) {
                    run(true);
                }
            }, state.refreshSeconds * 1000);
        }
        document.addEventListener("visibilitychange", onVisibility);
    });

    onWillUnmount(() => {
        clearInterval(timer);
        document.removeEventListener("visibilitychange", onVisibility);
    });

    return { state, refresh: () => run(true) };
}
