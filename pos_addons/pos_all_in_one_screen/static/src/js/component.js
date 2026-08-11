/** @odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { Component } from "@odoo/owl";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { renderToString } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { SelectOrderTypePopup } from "@pos_all_in_one_screen/js/popup";
import { registry } from "@web/core/registry";

export class KitchenScreenWidget extends Component {
    static template = "KitchenScreenWidget";

    setup() {
        this.pos = usePos();
        var self = this;
        setTimeout(function () {
            var orders = self.pos.db.pos_all_kitchen_orders;
            self.render_list(orders, undefined);
        }, 150);
    }
    render_list(orders, input_txt) {
        var self = this;
        var kitchen_order;
        var new_order_data = [];
        new_order_data = new_order_data.concat(self.pos.db.kitchen_order_by_id[orders[i]]);
        if (input_txt != undefined && input_txt != '') {
            var new_order_data = [];
            var search_text = input_txt.toLowerCase()
            for (var i = 0; i < orders.length; i++) {
                kitchen_order = self.pos.db.kitchen_order_by_id[orders[i]]
                if(kitchen_order){
                    if (kitchen_order.partner_id == '') {
                        kitchen_order.partner_id = [0, '-'];
                    }
                    if (kitchen_order.name && kitchen_order.pos_reference && kitchen_order.kitchen_order_name && kitchen_order.order_progress && kitchen_order.date_order) {
                        if (((kitchen_order.name.toLowerCase()).indexOf(search_text) != -1) || ((kitchen_order.pos_reference.toLowerCase()).indexOf(search_text) != -1) || (kitchen_order.kitchen_order_name.indexOf(search_text) != -1) || ((kitchen_order.order_progress.toLowerCase()).indexOf(search_text) != -1) || ((kitchen_order.date_order).indexOf(search_text) != -1)) {
                            new_order_data = new_order_data.concat(orders[i]);
                        }
                    } else {
                        if(kitchen_order.pos_reference && kitchen_order.kitchen_order_name && kitchen_order.order_progress && kitchen_order.date_order){
                            if (((kitchen_order.pos_reference.toLowerCase()).indexOf(search_text) != -1) || (kitchen_order.kitchen_order_name.indexOf(search_text) != -1) || ((kitchen_order.order_progress.toLowerCase()).indexOf(search_text) != -1) || ((kitchen_order.date_order).indexOf(search_text) != -1)) {
                                new_order_data = new_order_data.concat(orders[i]);
                            }
                        }
                    }
                }
            }
            orders = new_order_data;
        }
        var count = 0;
        orders.forEach(order => {
            self.pos.db.kitchen_order_by_id[order].lines.forEach(function (line_id) {
                if (self.pos.db.kitchen_line_by_id[line_id]) count++
            });
            self.pos.db.kitchen_order_by_id[order].items = self.pos.db.kitchen_order_by_id[order].lines.length;
            count = 0;
        });
        var contents = $('div.partnerlist-screen.screen')[0].querySelector('.wk-kitchen-list-contents');
        contents.innerHTML = "";

        var wk_orders = orders;
        if (wk_orders && wk_orders.length) {
            for (var i = 0, len = Math.min(wk_orders.length, 1000); i < len; i++) {
                var wk_order = wk_orders[i];
                var orderline_html = renderToString('WkKitchenOrderLine', {
                    env : self.env,
                    pos : self.pos, 
                    order: self.pos.db.kitchen_order_by_id[wk_orders[i]],
                    customer_id: self.pos.db.kitchen_order_by_id[wk_orders[i]].partner_id[0],
                });
                var orderline = document.createElement('tbody');
                orderline.innerHTML = orderline_html;
                orderline = orderline.childNodes[1];
                contents.appendChild(orderline);
            }
        }
    }
    keyup_order_search(event) {
        var orders = this.pos.db.pos_all_kitchen_orders;
        this.render_list(orders, event.target.value);
    }
    clickBack(event) {
        this.pos.showScreen('ProductScreen');
    }
}
registry.category("pos_screens").add("KitchenScreenWidget", KitchenScreenWidget);

export class SendOrderButton extends Component {
    static template = "SendOrderButton";

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.pos = usePos();
        this._currentOrder = this.pos.get_order();
    }
    check_orderline_qty() {
        var self = this;
        var order = this.pos.get_order();
        order.order_changes.new = []
        order.order_changes.cancelled = []
        if (order.removed_line.lines && order.removed_line.lines.length > 0) {
            order.removed_line.lines.forEach(function (line) {
                order.order_changes.cancelled.push({
                    wk_cid: line.wk_cid,
                    product_id: line.product_id,
                    name: line.name,
                    note: line.note,
                    quantity: line.quantity,
                    discount: line.discount,
                    price: line.price,
                });
            })
        }
        order.orderlines.forEach(function (line) {
            const productId = line.get_product().id;
            const note = line.getNote();
            if (line.kitchen_sent_qty == 0) {
                order.order_changes.new.push({
                    wk_cid: line.wk_cid,
                    product_id: productId,
                    name: line.get_full_product_name(),
                    note: note,
                    quantity: line.quantity,
                    discount: line.discount,
                    price: line.price,
                })
            } else if (line.kitchen_sent_qty > line.quantity) {
                order.order_changes.cancelled.push({
                    wk_cid: line.wk_cid,
                    product_id: productId,
                    name: line.get_full_product_name(),
                    note: note,
                    quantity: line.kitchen_sent_qty - line.quantity,
                    discount: line.discount
                })
            } else if (line.kitchen_sent_qty < line.quantity) {
                order.order_changes.new.push({
                    wk_cid: line.wk_cid,
                    product_id: productId,
                    name: line.get_full_product_name(),
                    note: note,
                    discount: line.discount,
                    quantity: line.quantity - line.kitchen_sent_qty,
                })
            }

            line.kitchen_sent_qty = line.quantity;
            line.is_kitchen_sent = true;
        });
    }
    async onClick() {
        var self = this;
        var order = this.pos.get_order();
        self.check_orderline_qty();

        if (order) {
            order.orderlines.forEach(function (line) {
                if (line.mp_dirty) line.mp_dirty = false;
            });
            $('.order-submit').removeClass('highlight');
            order.is_order_sent = false;
        }
        var is_order_validate = false;
        try {
            if (order) {
                self.orm.call('pos.kitchen.order', 'get_kitchen_order_data', [order.export_as_JSON(), is_order_validate, order.order_changes]
                ).then(function (return_dict) {
                    order.is_order_sent = true;
                    self.add_data_for_updation(return_dict);
                });
            }
        }
        catch{}
    }
    add_data_for_updation(data) {
        var self = this;
        if (data != null) {
            data.forEach(function (order) {
                var order_date = new Date(order['date_order']);
                var utc = order_date.getTime() - (order_date.getTimezoneOffset() * 60000);
                order['date_order'] = new Date(utc).toLocaleString();
                self.pos.db.pos_all_kitchen_orders.push(order.id);
                self.pos.db.kitchen_order_by_id[order.id] = order;
                if (Object.keys(self.pos.db.kitchen_order_by_id).length) self.pos.update_kitchen_restaurant_orders();
            });
        }
    }
}
ProductScreen.addControlButton({
    component: SendOrderButton,
    condition: function () {
        if (this.pos.config.order_action == 'order_button') return true;
    },
});

export class OrderTypeButton extends Component {
    static template = "OrderTypeButton";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
        this._currentOrder = this.pos.get_order();
    }
    async onClick() {
        const { confirmed } = await this.popup.add(SelectOrderTypePopup, {
            title: 'Select the Order Type',
            list: ['Takeaway', 'Dining'],
        });
    }
}
ProductScreen.addControlButton({
    component: OrderTypeButton,
});

export class KitchenOrdersButton extends Component {
    static template = "KitchenOrdersButton";
    
    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
    }
    async onclick() {
        var self = this;
        await self.orm.call('pos.kitchen.order', 'get_kitchen_orders', [[], self.pos.config.id],
        ).then(function (res) {
            res.forEach(order => {
                var order_date = new Date(order['date_order']);
                var utc = order_date.getTime() - (order_date.getTimezoneOffset() * 60000);
                order['date_order'] = new Date(utc).toLocaleString();
                self.pos.db.kitchen_order_by_id[order.id] = order;
            });
        }).catch(function(error){
            console.log("error", error);
        });
        self.pos.showScreen('KitchenScreenWidget', { env: self.env });
    }
}
ProductScreen.addControlButton({
    component: KitchenOrdersButton,
    condition: function () {
        return true;
    },
});