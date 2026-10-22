/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDashboardRefresh } from "./dashboard_utils";

const { Component, useState } = owl;

const HOURS = Array.from({ length: 24 }, (_, i) => i);

class CctvHeatMap extends Component {
    static template = "cctv_management.HeatMap";

    setup() {
        this.orm = useService("orm");
        this.hours = HOURS;
        this.state = useState({
            offices: [],
            activeOfficeId: null,
            departments: [],
            grid: {},     // grid[deptId][hour] = count
            maxCount: 1,
            loading: true,
        });
        // Access check + first load + auto-refresh (interval set in Configuration > Dashboard Access)
        this.dash = useDashboardRefresh("heat_map", (silent) => this.reload(silent));
    }

    async reload(silent) {
        const offices = await this.orm.searchRead("cctv.office", [], ["id", "name"]);
        this.state.offices = offices;
        if (!offices.length) {
            this.state.activeOfficeId = null;
            this.state.departments = [];
            this.state.loading = false;
            return;
        }
        const keep = offices.find((o) => o.id === this.state.activeOfficeId);
        await this.selectOffice(keep ? keep.id : offices[0].id, silent);
    }

    async selectOffice(officeId, silent = false) {
        if (!silent) {
            this.state.loading = true;
        }
        this.state.activeOfficeId = officeId;

        const departments = await this.orm.searchRead(
            "cctv.department", [["office_id", "=", officeId]], ["id", "name"]
        );

        const groups = await this.orm.readGroup(
            "cctv.event",
            [["office_id", "=", officeId]],
            ["department_id", "hour_of_day"],
            ["department_id", "hour_of_day"],
            { lazy: false }
        );

        const grid = {};
        let maxCount = 1;
        for (const dept of departments) grid[dept.id] = {};
        for (const g of groups) {
            const deptId = g.department_id ? g.department_id[0] : null;
            if (!deptId || !(deptId in grid)) continue;
            const hour = g.hour_of_day;
            const count = g.__count !== undefined ? g.__count : g.department_id_count;
            grid[deptId][hour] = count;
            if (count > maxCount) maxCount = count;
        }
        if (this.state.activeOfficeId !== officeId) {
            return; // the user switched site while this request was running
        }
        this.state.departments = departments;
        this.state.grid = grid;
        this.state.maxCount = maxCount;
        this.state.loading = false;
    }

    cellCount(deptId, hour) {
        return (this.state.grid[deptId] && this.state.grid[deptId][hour]) || 0;
    }

    cellOpacity(deptId, hour) {
        const count = this.cellCount(deptId, hour);
        return count ? Math.min(1, 0.15 + (count / this.state.maxCount) * 0.85) : 0;
    }
}

registry.category("actions").add("cctv_management.heat_map", CctvHeatMap);
