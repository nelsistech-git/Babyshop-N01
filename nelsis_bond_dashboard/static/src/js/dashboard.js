/** @odoo-module **/
// Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

const SEVERITY_BADGE = { critical: "text-bg-danger", warning: "text-bg-warning", info: "text-bg-info" };

export class BondDashboard extends Component {
    static template = "nelsis_bond_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, failed: false, data: null });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.failed = false;
        try {
            this.state.data = await this.orm.call("bond.dashboard", "get_dashboard_data", []);
        } catch (error) {
            this.state.failed = true;
            this.state.data = null;
        }
        this.state.loading = false;
    }

    cardClass(card) {
        const classes = ["o_nbd_card"];
        if (card.status !== "ok") {
            classes.push("o_nbd_card_muted");
        } else if (card.danger_if_positive && card.value > 0) {
            classes.push("o_nbd_tone_danger");
        } else {
            classes.push("o_nbd_tone_" + card.color);
        }
        if (card.type === "breakdown") {
            classes.push("o_nbd_card_wide");
        }
        return classes.join(" ");
    }

    severityClass(severity) {
        return SEVERITY_BADGE[severity] || "text-bg-secondary";
    }

    openCard(card) {
        if (card.status !== "ok") {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: card.name,
            res_model: card.model,
            views: [[false, "list"], [false, "form"]],
            domain: card.domain,
            target: "current",
        });
    }

    onCardKey(ev, card) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this.openCard(card);
        }
    }

    openAlert(alert) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: alert.name,
            res_model: "bond.dashboard.alert",
            res_id: alert.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllAlerts() {
        this.action.doAction("nelsis_bond_dashboard.action_bond_dashboard_alert");
    }
}

registry.category("actions").add("nelsis_bond_dashboard.main", BondDashboard);
