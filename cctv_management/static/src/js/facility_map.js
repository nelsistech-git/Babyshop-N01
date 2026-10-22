/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useDashboardRefresh } from "./dashboard_utils";

const { Component, useState } = owl;

class CctvFacilityMap extends Component {
    static template = "cctv_management.FacilityMap";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            offices: [],
            activeOfficeId: null,
            mapImageUrl: null,
            cameras: [],
            loading: true,
        });
        // Access check + first load + auto-refresh (interval set in Configuration > Dashboard Access)
        this.dash = useDashboardRefresh("facility_map", (silent) => this.reload(silent));
    }

    async reload(silent) {
        const offices = await this.orm.searchRead("cctv.office", [], ["id", "name"]);
        this.state.offices = offices;
        if (!offices.length) {
            this.state.activeOfficeId = null;
            this.state.cameras = [];
            this.state.loading = false;
            return;
        }
        // keep the site the user is looking at; fall back to the first one
        const keep = offices.find((o) => o.id === this.state.activeOfficeId);
        await this.selectOffice(keep ? keep.id : offices[0].id, silent);
    }

    async selectOffice(officeId, silent = false) {
        if (!silent) {
            this.state.loading = true;
        }
        this.state.activeOfficeId = officeId;
        this.state.mapImageUrl = `/web/image/cctv.office/${officeId}/map_image`;

        const cameras = await this.orm.searchRead(
            "cctv.camera",
            [["office_id", "=", officeId]],
            ["id", "name", "health_status", "map_x", "map_y"]
        );
        // One extra read_group to get today's open-alert count per camera,
        // so pins can show a red badge for cameras with unresolved alerts.
        const alertGroups = await this.orm.readGroup(
            "cctv.alert",
            [["camera_id", "in", cameras.map((c) => c.id)], ["state", "=", "new"]],
            ["camera_id"],
            ["camera_id"]
        );
        const alertCountByCamera = {};
        for (const g of alertGroups) {
            if (g.camera_id) alertCountByCamera[g.camera_id[0]] = g.camera_id_count;
        }
        if (this.state.activeOfficeId !== officeId) {
            return; // the user switched site while this request was running
        }
        this.state.cameras = cameras.map((c) => ({
            ...c,
            alert_count: alertCountByCamera[c.id] || 0,
            has_position: c.map_x || c.map_y,
        }));
        this.state.loading = false;
    }

    openCamera(cameraId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cctv.camera",
            res_id: cameraId,
            views: [[false, "form"]],
            target: "new",
        });
    }
}

registry.category("actions").add("cctv_management.facility_map", CctvFacilityMap);
