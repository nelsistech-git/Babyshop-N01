/** @odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class WkErrorKSPopopWidget extends AbstractAwaitablePopup {
    static template = "WkErrorKSPopopWidget";
    static defaultProps = { body: "" };
}

export class SelectOrderTypePopup extends AbstractAwaitablePopup {
    static template = "SelectOrderTypePopup";
    static defaultProps = { 
        cancelText: ('Cancel'),
        title: ('Select'),
        body: '',
        list: [],
        confirmKey: false,
    };

    setup() {
        super.setup();
        this.pos = usePos();
    }
    selectItem(order_type) {
        this.pos.get_order().order_type = order_type;
        this.confirm();
    }
}