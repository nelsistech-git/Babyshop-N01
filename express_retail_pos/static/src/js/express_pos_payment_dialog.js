/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";

export class ExpressPosPaymentDialog extends Component {
    static template = "express_retail_pos.ExpressPosPaymentDialog";
    static components = {Dialog};
    static props = {
        amountDue: Number,
        journals: Array,
        currencySymbol: String,
        isWalkin: {type: Boolean, optional: true},
        onConfirm: Function,
        close: Function,
    };

    setup() {
        this.state = useState({
            amounts: Object.fromEntries(this.props.journals.map((j) => [j.id, 0])),
            giftCardCode: "",
            giftCardAmount: 0,
            allowDue: false,
        });
        if (this.props.journals.length) {
            this.state.amounts[this.props.journals[0].id] = this.props.amountDue;
        }
    }

    get totalEntered() {
        const journalTotal = Object.values(this.state.amounts).reduce((a, b) => a + (parseFloat(b) || 0), 0);
        return journalTotal + (parseFloat(this.state.giftCardAmount) || 0);
    }

    get remaining() {
        return this.props.amountDue - this.totalEntered;
    }

    get change() {
        return this.totalEntered > this.props.amountDue ? this.totalEntered - this.props.amountDue : 0;
    }

    get canConfirm() {
        if (this.state.allowDue) {
            return this.totalEntered >= 0 && !this.props.isWalkin;
        }
        return this.remaining <= 0.001 && this.totalEntered > 0;
    }

    onAmountChange(journalId, ev) {
        this.state.amounts[journalId] = parseFloat(ev.target.value) || 0;
    }

    selectTender(journalId) {
        // Quick-select: put the full remaining amount on this journal, zero the rest.
        for (const id of Object.keys(this.state.amounts)) {
            this.state.amounts[id] = 0;
        }
        this.state.amounts[journalId] = Math.max(0, this.props.amountDue - (parseFloat(this.state.giftCardAmount) || 0));
    }

    fillRemaining(journalId) {
        this.state.amounts[journalId] = (parseFloat(this.state.amounts[journalId]) || 0) + this.remaining;
    }

    quickCash(journalId, amount) {
        this.state.amounts[journalId] = amount;
    }

    toggleDue() {
        this.state.allowDue = !this.state.allowDue;
    }

    async onConfirmClick() {
        const paymentLines = Object.entries(this.state.amounts)
            .map(([journalId, amount]) => ({journal_id: parseInt(journalId), amount: parseFloat(amount) || 0}))
            .filter((pl) => pl.amount > 0);
        const giftCardLines = [];
        const gcAmount = parseFloat(this.state.giftCardAmount) || 0;
        if (this.state.giftCardCode.trim() && gcAmount > 0) {
            giftCardLines.push({code: this.state.giftCardCode.trim(), amount: gcAmount});
        }
        await this.props.onConfirm(paymentLines, giftCardLines, this.state.allowDue);
        this.props.close();
    }
}