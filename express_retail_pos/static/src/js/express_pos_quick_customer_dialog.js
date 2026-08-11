/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";

export class ExpressPosQuickCustomerDialog extends Component {
    static template = "express_retail_pos.ExpressPosQuickCustomerDialog";
    static components = {Dialog};
    static props = {
        onConfirm: Function,
        close: Function,
    };

    setup() {
        this.state = useState({name: "", mobile: "", error: ""});
    }

    get canConfirm() {
        return /^\d{11}$/.test(this.state.mobile.trim());
    }

    async onConfirmClick() {
        const mobile = this.state.mobile.trim();
        if (!/^\d{11}$/.test(mobile)) {
            this.state.error = "Mobile number must be exactly 11 digits.";
            return;
        }
        this.state.error = "";
        await this.props.onConfirm(this.state.name.trim(), mobile);
        this.props.close();
    }
}