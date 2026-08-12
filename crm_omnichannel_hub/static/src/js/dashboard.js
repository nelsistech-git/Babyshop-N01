/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class OmniDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.type = (this.props.action && this.props.action.context && this.props.action.context.dashboard_type) || "executive";
        this.state = useState({ data: null, loading: true, error: false });
        onWillStart(async () => {
            await this.loadData();
        });
    }

    get title() {
        if (this.type === "manager") {
            return "Manager Dashboard";
        } else if (this.type === "agent") {
            return "My Dashboard";
        }
        return "Executive Dashboard";
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = false;
        let method = "get_executive_dashboard";
        if (this.type === "manager") {
            method = "get_manager_dashboard";
        } else if (this.type === "agent") {
            method = "get_agent_dashboard";
        }
        try {
            const result = await this.orm.call("crm.omni.dashboard", method, []);
            this.state.data = result;
        } catch (err) {
            this.state.error = true;
        } finally {
            this.state.loading = false;
        }
    }

    async openInbox(domain) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Conversations",
            res_model: "crm.chat.session",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain || [],
        });
    }

    onRefresh() {
        this.loadData();
    }
}

OmniDashboard.template = "crm_omnichannel_hub.OmniDashboard";

registry.category("actions").add("crm_omni_dashboard", OmniDashboard);
