/** @odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order, Orderline } from "@point_of_sale/app/store/models";
import { KitchenOrdersButton } from "@pos_all_in_one_screen/js/component";
import { renderToString } from "@web/core/utils/render";
import { roundDecimals as round_di, floatIsZero } from "@web/core/utils/numbers";

patch(PosStore.prototype, {
    async _processData(loadedData) {
        var self = this; 
        await super._processData(...arguments);
        var result = loadedData['pos.screen.config'];
        self.db.pos_screen_data = {};
        self.db.recent_notifications = [];
        result.forEach(data => {
            if (data && ((data.pos_config_ids.indexOf(self.config.id) != -1) || data.related_id[0] == self.config.id)) {
                self.db.pos_screen_data[data.id] = data;
                if(data.type === 'cart') self.db.cart_screen = data;
            }
        });
    },
    async getClosePosInfo() {
        const closingData = await this.env.services.orm.call('pos.session', 'get_closing_control_data', [[this.pos_session.id]]);
        const ordersDetails = closingData.orders_details;
        const paymentsAmount = closingData.payments_amount;
        const payLaterAmount = closingData.pay_later_amount;
        const openingNotes = closingData.opening_notes;
        const defaultCashDetails = closingData.default_cash_details;
        const otherPaymentMethods = closingData.other_payment_methods;
        const isManager = closingData.is_manager;
        const amountAuthorizedDiff = closingData.amount_authorized_diff;
        const cashControl = this.config.cash_control;
        const pendingOrders = closingData.pending_orders;

        // component state and refs definition
        const state = {notes: '', acceptClosing: false, payments: {}};
        if (cashControl) {
            state.payments[defaultCashDetails.id] = {counted: 0, difference: -defaultCashDetails.amount, number: 0};
        }
        if (otherPaymentMethods.length > 0) {
            otherPaymentMethods.forEach(pm => {
                if (pm.type === 'bank') {
                    state.payments[pm.id] = {counted: this.round_decimals_currency(pm.amount), difference: 0, number: pm.number}
                }
            })
        }
        return {
            ordersDetails, paymentsAmount, payLaterAmount, openingNotes, defaultCashDetails, otherPaymentMethods,
            isManager, amountAuthorizedDiff, state, cashControl, pendingOrders
        }
    }
});

patch(PosStore.prototype, {
    async _processData(loadedData) {
        await super._processData(...arguments);
        // Load pos.kitchen.orderline
        var self = this;
        var today = new Date();
        var today = new Date(today.setDate(today.getDate())).toISOString();
        var date = today.split('T');
        var validation_date = date[0];

        if (this.db.pos_screen_data) {
            var pos_categ_ids = [];
            Object.values(this.db.pos_screen_data).forEach(data => {
                pos_categ_ids = pos_categ_ids.concat(data.pos_category_ids);
            });

            var pos_kitchen_orderline_domain = [
                ['product_id.pos_categ_ids', 'in', pos_categ_ids],
                ['order_id.config_id.order_action', '=', 'order_button'],
                ['order_id.date_order', '>=', validation_date],
                ['order_id.session_id', '=', this.pos_session.name]
            ]
        }
        await this.env.services.orm.call("pos.kitchen.orderline", "fetch_pos_kitchen_orderline", [{pos_kitchen_orderline_domain: pos_kitchen_orderline_domain}],
        ).then(function (result) {
            if (self.config.order_action == 'order_button') {
                self.db.pos_all_kitchen_order_lines = result;
                self.db.kitchen_line_by_id = {};
                result.forEach(function (line) {
                    self.db.kitchen_line_by_id[line.id] = line;
                });
            }
        }).catch(function (error) {
            console.log("error", error);
        });

        // Load pos.kitchen.order
        var orders = new Set();
        if(self.db.pos_all_kitchen_order_lines){
            self.db.pos_all_kitchen_order_lines.forEach(line => {
                orders.add(line.order_id[0]);
            });
        }
        var pos_kitchen_order_domain = [
            ['id', 'in', Array.from(orders)],
            ['kitchen_order_name', '!=', false]
        ];
        await this.env.services.orm.call("pos.kitchen.order", "fetch_pos_kitchen_order", [{pos_kitchen_order_domain: pos_kitchen_order_domain}],
        ).then(function (result) {
            if (self.config.order_action == 'order_button') {
                self.db.pos_all_kitchen_orders = [];
                self.db.kitchen_order_by_id = {};
                self.db.next_order_token = false;
                self.db.orders_in_queue_by_id = {};
                self.db.orders_in_queue = [];

                result.forEach(function (order) {
                    var order_date = new Date(order['date_order']);
                    var utc = order_date.getTime() - (order_date.getTimezoneOffset() * 60000);
                    order['date_order'] = new Date(utc).toLocaleString();
                    self.db.kitchen_order_by_id[order.id] = order;
                    self.db.pos_all_kitchen_orders.push(order.id);
                });
                if (self.db.pos_all_kitchen_orders.length)
                    self.db.pos_all_kitchen_orders.reverse();
                var order_array = self.db.pos_all_kitchen_orders;
                if (self.db.pos_screen_data && self.db.pos_screen_data.queue_order == 'old2new')
                    self.db.pos_all_kitchen_orders = order_array.reverse();
            }
        }).catch(function (error) {
            console.log("error", error);
        });
    },
    async update_kitchen_restaurant_orders() {
        var self = this;
        var promise = await self.env.services.orm.call('pos.kitchen.order', 'update_kitchen_order_progress', [Object.keys(self.db.kitchen_order_by_id)]
        ).then(function (data) {
            if (data) {
                if (data.progress){
                    data.progress.forEach(obj => {
                        self.db.kitchen_order_by_id[obj.id.toString()]['order_progress'] = obj.order_progress;
                    });
                }
                if (data.qtys){
                    data.qtys.forEach(obj => {
                        if (Object.keys(self.db.kitchen_line_by_id).indexOf(obj.id.toString()) != -1){
                            self.db.kitchen_line_by_id[obj.id.toString()]['total_qtys'] = obj.total_qtys;
                        }
                    });
                }
            }
        }).catch(function (error) {
            console.log("error", error);
        });
        return promise
    },
    getReceiptHeaderData() {
        return {
            ...super.getReceiptHeaderData(...arguments),
            token_number: this.get_order().token_number,
        };
    },
});

patch(PosStore.prototype, {
    is_product_in_category: function (category_ids, product_id) {
        var self = this;
        if (!(category_ids instanceof Array)) {
            category_ids = [category_ids];
        }
        var categs = self.get_product_by_id(product_id).pos_categ_ids;
        var count = 0
        var res = false;
        categs.forEach(cat => {
            while (cat) {
                for (var i = 0; i < category_ids.length; i++) {
                    if (cat == category_ids[i]) {
                        count++
                        res = true;
                    }
                }
                cat = self.get_category_parent_id(cat);
            }
        });
        return res;
    },
});

patch(Order.prototype, {
    electronic_payment_in_progress() {
        return this.get_paymentlines()
            .some(function (pl) {
                if (pl.payment_status) {
                    return !['done', 'reversed'].includes(pl.payment_status);
                } else {
                    return false;
                }
            });
    },
    send_order_button_on_validate() {
        var self = this;
        var pos_categ_ids = []
        var order = self;
        var is_order_validate = true;
        try {
            if (order) {
                self.orm.call('pos.kitchen.order', 'get_kitchen_order_data', [order.export_as_JSON(), is_order_validate, order.order_changes]
                ).then(function (return_dict) {
                    order.is_order_sent = true;
                    self.add_data_for_updation(return_dict);
                }).catch(function (error) {
                    console.log("error", error);
                });
            }
        }
        catch { }
    },
    add_data_for_updation(data) {
        var self = this;
        if (data) {
            if (data.orders != null) {
                data.orderlines.forEach(function (orderline) {
                    self.pos.db.pos_all_kitchen_order_lines.unshift(orderline);
                    self.pos.db.kitchen_line_by_id[orderline.id] = orderline;
                });
                data.orders.forEach(function (order) {
                    var order_date = new Date(order['date_order'])
                    var utc = order_date.getTime() - (order_date.getTimezoneOffset() * 60000);
                    order['date_order'] = new Date(utc).toLocaleString();
                    if (self.pos.db.pos_screen_data && self.pos.db.pos_screen_data.queue_order == 'new2old'){
                        self.pos.db.pos_all_kitchen_orders.unshift(order.id);
                    }else{
                        self.pos.db.pos_all_kitchen_orders.push(order.id);
                    }
                    self.pos.db.kitchen_order_by_id[order.id] = order;
                    if (Object.keys(self.pos.db.kitchen_order_by_id).length)
                        self.pos.update_kitchen_restaurant_orders();
                });

                delete data.orders;
                delete data.orderlines;
            }
        }
    },
    get_queue_no() {
        var self = this;
        return self.pos.get_order().token_number;
    },
    export_as_JSON() {
        var self = this;
        var loaded = super.export_as_JSON();
        loaded.is_kitchen_order = self.validate_order_for_kitchen();
        loaded.token_no = self.token_no;
        if(self.pos.config.pos_kitchen_screen.length){
            var id = self.pos.config.pos_kitchen_screen[0];
            if(id) loaded.screen_session_id = self.pos.db.pos_screen_data[id].current_session_id[0];
        }
        return loaded;
    },
    add_paymentline(cashregister) {
        var self = this;
        if (!self.pos.config.order_action || (self.pos.config.order_action && self.pos.config.order_action == 'validation')) {
            if (!self.pos.get_order().token_no && self.pos.get_order().validate_order_for_kitchen())
                self.add_token_number();
        }
        return super.add_paymentline(...arguments);
    },
    add_token_number() {
        var self = this;
        var res = self.env.services.orm.call('pos.order', 'get_token_number',).then(function (res) {
            self.pos.get_order().token_no = res;
        }).catch(function (e) {
            console.log("e", e)
        })
        return res;
    },
    validate_order_for_kitchen() {
        var self = this;
        var screen_data = self.pos.db.pos_screen_data;
        var is_kitchen_order = false;
        var pos_categ_ids = [];
        Object.values(self.pos.db.pos_screen_data).forEach(data => {
            pos_categ_ids = pos_categ_ids.concat(data.pos_category_ids);
        });
        if (screen_data && !self.is_return_order) {
            if (screen_data && !pos_categ_ids) is_kitchen_order = true;
            if (!is_kitchen_order){
                self.get_orderlines().forEach(line => {
                    if (line.product.pos_categ_ids) {
                        line.product.pos_categ_ids.forEach(cat => {
                            if (pos_categ_ids && pos_categ_ids.indexOf(cat) != -1) is_kitchen_order = true;
                        });
                    }
                });
            }
        }
        return is_kitchen_order
    }
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.is_order_sent = false;
        this.order_progress = this.order_progress || false;
        this.order_changes = { new: [], cancelled: []};
        this.removed_line = {lines: []};
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (json.is_order_sent) {
            this.is_order_sent = json.is_order_sent;
        }
        this.order_changes = json.order_changes
        this.order_progress = json.order_progress
        this.removed_line = json.removed_line
        // this.order_type = json.order_type
    },
    export_as_JSON() {
        var json = super.export_as_JSON(...arguments);
        var current_order = this;
        if (current_order != null) {
            json.is_order_sent = this.is_order_sent;
            json.order_changes = this.order_changes
            json.order_progress = this.order_progress
            json.removed_line = this.removed_line
            json.order_type = this.order_type
        }
        if (this.pos.db.pos_screen_data && Object.values(this.pos.db.pos_screen_data)[0] && Object.values(this.pos.db.pos_screen_data)[0].id) {
            json.kitchen_config_id = Object.values(this.pos.db.pos_screen_data)[0].id;
        }
        return json;
    },
    add_product(product, options) {
        var self = this;
        super.add_product(product, options);
        var pos_categ_ids = [];
        Object.values(self.pos.db.pos_screen_data).forEach(data => {
            pos_categ_ids = pos_categ_ids.concat(data.pos_category_ids);
        });
        var curr_line = self.get_selected_orderline();
        if(pos_categ_ids.filter(categ => curr_line.product.pos_categ_ids.includes(categ))){
            $('.order-submit').addClass('highlight')
            if (curr_line) curr_line.mp_dirty = true;
        }
    },
    _wkgetPrintingCategoriesChanges(printingChanges, categories) {
        var self = this;
        if (!this.pos.config.iface_printers) {
            var result = {
                new: printingChanges['new'].filter(change => this.pos.db.is_product_in_category(categories, change['product_id'])),
                cancelled: printingChanges['cancelled'].filter(change => this.pos.db.is_product_in_category(categories, change['product_id'])),
            }
        }
        return result
    },
    async showChanges() {
        try {
            var self = this;
            var pos_categ_ids = [];
            this.pos.db.pos_screen_data.forEach(data => {
                pos_categ_ids = pos_categ_ids.concat(data.pos_category_ids);
            });
            if (self) {
                var changes = this._getPrintingCategoriesChanges(pos_categ_ids);
                if (changes && changes['new'].length > 0 || changes['cancelled'].length > 0) {
                    var receipt = renderToString('OrderChangeReceipt', {
                        changes: changes,
                        widget: this
                    });
                    await printers[i].print_receipt(receipt);
                }
            }
        } catch { }
    },
    wkhasChangesToShow() {
        var pos_categ_ids = []
        var self = this;
        this.pos.db.pos_screen_data.forEach(data => {
            pos_categ_ids = pos_categ_ids.concat(data.pos_category_ids);
        });
        try {
            if (self && self.order_changes) {
                var changes = self.order_changes;
                if (changes && changes['new'].length > 0 || changes['cancelled'].length > 0) {
                    return true;
                }
                return false;
            }
        } catch { }
    },
    hasSkippedChanges() {
        var orderlines = this.get_orderlines();

        for (var i = 0; i < orderlines.length; i++) {
            if (orderlines[i].mp_skip) {
                return true;
            }
        }
        return false;
    }
});

patch(Orderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.mp_dirty = this.mp_dirty || false;
        if (!this.mp_skip) {
            this.mp_skip = false;
        }
        this.kitchen_sent_qty = this.kitchen_sent_qty || 0;
        this.is_kitchen_sent = this.is_kitchen_sent || false;
        this.is_orderline_done = this.is_orderline_done || false;
        this.state = this.state || false;
        if (!this.wk_cid) {
            this.wk_cid = this.cid
        } else {
            this.wk_cid = this.wk_cid;
        }
    },
    can_be_merged_with(orderline) {
        var self = this;
        var price = parseFloat(round_di(this.price || 0, this.pos.dp['Product Price']).toFixed(this.pos.dp['Product Price']));
        var order_line_price = orderline.get_product().get_price(orderline.order.pricelist, this.get_quantity());
        order_line_price = round_di(orderline.compute_fixed_price(order_line_price), this.pos.currency.decimal_places);
        if (self.get_product().id !== orderline.get_product().id) {    //only orderline of the same product can be merged
            return false;
        }
        else if (self.is_orderline_done) {
            return false;
        }
        else if (!self.get_unit() || !self.get_unit().is_pos_groupable) {
            return false;
        } else if (self.get_discount() > 0) {             // we don't merge discounted orderlines
            return false;
        } else if (!floatIsZero(price - order_line_price - orderline.get_price_extra(),
            self.pos.currency.decimal_places)) {
            return false;
        } else if (self.product.tracking == 'lot' && (self.pos.picking_type.use_create_lots || self.pos.picking_type.use_existing_lots)) {
            return false;
        } else if (self.description !== orderline.description) {
            return false;
        } else if (orderline.get_customer_note() !== self.get_customer_note()) {
            return false;
        } else if (self.refunded_orderline_id) {
            return false;
        } else {
            return true;
        }
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        if (json.mp_dirty) {
            this.mp_dirty = json.mp_dirty
        }
        if (json.mp_skip) {
            this.mp_skip = json.mp_skip
        }
        if (json.kitchen_sent_qty) {
            this.kitchen_sent_qty = json.kitchen_sent_qty
        }
        if (json.is_kitchen_sent) {
            this.is_kitchen_sent = json.is_kitchen_sent
        }
        this.state = json.state;
        this.is_orderline_done = json.is_orderline_done;
        this.wk_cid = json.wk_cid;
    },
    export_as_JSON() {
        var json = super.export_as_JSON(...arguments);
        var current_line = this;
        if (current_line) {
            json.mp_dirty = current_line.mp_dirty;
            json.mp_skip = current_line.mp_skip;
            json.total_qtys = current_line.get_quantity();
            json.kitchen_sent_qty = current_line.kitchen_sent_qty;
            json.is_kitchen_sent = current_line.is_kitchen_sent;
            json.state = current_line.state;
            json.is_orderline_done = current_line.is_orderline_done;
            json.wk_cid = current_line.wk_cid;
            json.customerNote = current_line.customerNote;
        }
        return json;
    },
    can_be_shown_to_kitchen() {
        var temp_cat = [];
        this.pos.db.pos_screen_data.forEach(data => {
            temp_cat = temp_cat.concat(data.pos_category_ids);
        });
        return this.pos.db.is_product_in_category(temp_cat, this.get_product().id);
    },
    update_orderline_status(product) {
        var self = this;
        var order = self.order;
        var curr_line = product;
        order.orderlines.forEach(function (line) {
            if (line.product.id == product.id) {
                curr_line = line;
            }
        });

        if (curr_line) {
            var product_id = curr_line.product ? curr_line.product.id : curr_line.id;
            var promise = self.orm.call('pos.kitchen.order', 'fetch_same_product_orderlines', [order.export_as_JSON(), product_id, curr_line.quantity]
            ).then(function (result) {
                order.orderlines.forEach(function (line) {
                    result.forEach(function (res_line) {
                        if (res_line[0].wk_cid == line.wk_cid) {
                            line.is_orderline_done = res_line[0].is_orderline_done;
                        }
                    })
                })
            }).catch(function (error) {
                console.log("error", error);
            });
            return promise
        }
    }
});

patch(KitchenOrdersButton.prototype, {
    async onClick() {
        var self = this;
        var promise_obj = null;
        if (self.pos.config.module_pos_restaurant && Object.keys(self.pos.db.kitchen_order_by_id).length)
            promise_obj = self.pos.update_kitchen_restaurant_orders();
        else
            promise_obj = self.pos.update_kitchen_orders();
        promise_obj.then(function (res) {
            self.pos.showScreen('KitchenScreenWidget', { env: self.env });
        })
    }
});