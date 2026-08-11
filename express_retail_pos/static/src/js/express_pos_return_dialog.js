/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class ExpressPosReturnDialog extends Component {
    static template = "express_retail_pos.ExpressPosReturnDialog";
    static components = { Dialog };
    static props = {
        onDone: Function,
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            step: "search",
            query: "",
            results: [],
            sourceOrder: null,
            lines: [],
            returnQty: {},
            processing: false,
        });
    }

    async onSearchInput(ev) {
        this.state.query = ev.target.value;
        this.state.results = await this.orm.call("sale.order", "express_pos_search_source_orders", [this.state.query]);
    }

    async selectOrder(order) {
        const data = await this.orm.call("sale.order", "express_pos_get_order_lines_for_return", [order.id]);
        this.state.sourceOrder = data;
        this.state.lines = data.lines;
        this.state.returnQty = Object.fromEntries(data.lines.map((l) => [l.line_id, 0]));
        this.state.step = "lines";
    }

    onQtyChange(lineId, ev) {
        this.state.returnQty[lineId] = parseFloat(ev.target.value) || 0;
    }

    get hasSelection() {
        return Object.values(this.state.returnQty).some((q) => q > 0);
    }

    async executeReturn() {
        if (!this.hasSelection || this.state.processing) return;
        this.state.processing = true;
        const returnLines = Object.entries(this.state.returnQty)
            .map(([lineId, qty]) => ({ line_id: parseInt(lineId), qty: parseFloat(qty) || 0 }))
            .filter((rl) => rl.qty > 0);
        try {
            const result = await this.orm.call("sale.order", "express_pos_process_return", [
                this.state.sourceOrder.order_id, returnLines,
            ]);
            this.props.onDone(`Return processed for ${result.source_order}. Credit note: ${result.credit_note_names.join(", ") || "n/a"}`);
            this.props.close();
        } catch (error) {
            this.notification.add(error.data ? error.data.message : String(error), { type: "danger" });
        } finally {
            this.state.processing = false;
        }
    }

    backToSearch() {
        this.state.step = "search";
        this.state.sourceOrder = null;
        this.state.lines = [];
    }
}
