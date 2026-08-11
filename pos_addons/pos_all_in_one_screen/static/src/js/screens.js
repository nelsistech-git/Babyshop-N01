/** @odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { Order } from "@point_of_sale/app/store/models";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";

patch(PosStore.prototype, {
    async _processData(loadedData) {
        await super._processData(...arguments);
        var self = this;
        var wk_order_lines = loadedData['pos.order.line'];

        if (!self.config.order_action || (self.config.order_action && self.config.order_action == 'validation')) {
            self.db.pos_all_kitchen_order_lines = wk_order_lines;
            self.db.kitchen_line_by_id = {};
            wk_order_lines.forEach(function (line) {
                self.db.kitchen_line_by_id[line.id] = line;
            });
        }

        var wk_order = loadedData['pos.order']
        if (!self.config.order_action || (self.config.order_action && self.config.order_action == 'validation')) {
            self.db.pos_all_kitchen_orders = [];
            self.db.kitchen_order_by_id = {};
            self.db.next_order_token = false;
            self.db.orders_in_queue_by_id = {};
            self.db.orders_in_queue = [];

            if (!self.config.order_action || (self.config.order_action && self.config.order_action == 'validation')) {
                wk_order.forEach(function (order) {
                    var order_date = new Date(order['date_order']);
                    var utc = order_date.getTime() - (order_date.getTimezoneOffset() * 60000);
                    order['date_order'] = new Date(utc).toLocaleString();
                    self.db.kitchen_order_by_id[order.id] = order;
                    self.db.pos_all_kitchen_orders.push(order.id);
                });
                if (self.db.pos_all_kitchen_orders.length) self.db.pos_all_kitchen_orders.reverse();
                var order_array = self.db.pos_all_kitchen_orders
                if (self.db.pos_screen_data && self.db.pos_screen_data.queue_order == 'new2old') {
                    order_array = self.db.pos_all_kitchen_orders.reverse();
                } 
                else{
                    order_array = self.db.pos_all_kitchen_orders;
                }
            }
        }
    },
    update_token_number() {
        var self = this;
        return this.env.services.orm('pos.order', 'get_token_number').then(function (data) {
            if (data) self.db.next_order_token = data;
            else self.db.next_order_token = '#0000';
        });
    },
    update_kitchen_orders() {
        var self = this;
        if (self.db.kitchen_order_by_id)
            var promise = self.orm.call('pos.order', 'update_order_progress', [Object.keys(self.db.kitchen_order_by_id)]
            ).then(function (data) {
                if (data) {
                    data.forEach(obj => {
                        self.db.kitchen_order_by_id[obj.id.toString()]['order_progress'] = obj.order_progress;
                    });
                }
            }).catch(function (error) {
                console.log("error", error);
            });
        return promise
    },
    _save_to_server(orders, options) {
        var self = this;
        return super._save_to_server(orders, options).then(function (return_dict) {
            if (return_dict) {
                return_dict.forEach(data => {
                    if (data.orders != null) {
                        data.orderlines.forEach(function (orderline) {
                            if (self.db.pos_all_kitchen_order_lines)
                                self.db.pos_all_kitchen_order_lines.unshift(orderline);
                            self.db.kitchen_line_by_id[orderline.id] = orderline;
                        });
                        data.orders.forEach(function (order) {
                            var order_date = new Date(order['date_order'])
                            var utc = order_date.getTime() - (order_date.getTimezoneOffset() * 60000);
                            order['date_order'] = new Date(utc).toLocaleString();
                            if (self.db.pos_screen_data[2] && self.db.pos_screen_data[2].queue_order == 'new2old') {
                                self.db.pos_all_kitchen_orders.unshift(order.id);
                            }
                            else {
                                self.db.pos_all_kitchen_orders.push(order.id);
                            }
                            self.db.kitchen_order_by_id[order.id] = order;
                            if (self.db.kitchen_order_by_id)
                                self.update_kitchen_orders();
                        });
                        delete data.orders;
                        delete data.orderlines;
                    }
                });
            }
            return return_dict
        });
    }
});

patch(Order.prototype, {
    export_for_printing() {
        var self = this
        var receipt = super.export_for_printing()
        if (self.pos.db.next_order_token && self.pos.get_order().validate_order_for_kitchen()) {
            var next_order_token = self.pos.db.next_order_token;
            var new_token = '';
            var token = next_order_token.split("#")[1]
            var new_number = parseInt(token) + 1;
            new_token = "#" + (new_number / 10000).toString().split('.')[1]
            receipt.token_no = new_token;
        }
        return receipt
    }
});
    
patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        var self = this;
        if (self.pos.get_order().validate_order_for_kitchen() && (self.pos.config.order_action == 'validation' && self.pos.config.order_action) && (!self.pos.get_order().token_no || self.pos.get_order().token_no == '')) {
            const {confirmed} = await this.showPopup('ConfirmPopup', {
                'title': _t('A Kitchen Order?'),
                'body': _t('Do you want to send this order to kitchen screen?'),
            });
            if (confirmed) {
                var res = self.pos.get_order().add_token_number();
                super.validateOrder(isForceValidate);
            }
        } else {
            var res = self.pos.get_order().send_order_button_on_validate();
            super.validateOrder(isForceValidate);
        }
    }
});

patch(ReceiptScreen.prototype, {
    async orderDone() {
        this.orm.call('pos.screen.config', 'update_review_screen_status', [false, []]);
        await super.orderDone();
    },
    send_review_to_screen() {
        if(this.pos){
            var order = this.pos.get_order();
            this.orm.call('pos.screen.config', 'update_review_screen_status', {
                'reload': true,
                'name': order.name,
            });
        }
    }	
});

patch(ProductScreen.prototype, {
    onMounted() {
        super.onMounted();
        this.pos.get_order().orderlines.forEach(function (line) {
            if (line.mp_dirty) $('.order-submit').addClass('highlight');
        })
    },
    update_orderline_status(product) {
        var self = this;
        var order = self.pos.get_order()
        var curr_line = product;
        order.orderlines.forEach(function (line) {
            if (line.product.id == product.id) {
                curr_line = line;
            }
        });
        if (curr_line) {
            var product_id = curr_line.product ? curr_line.product.id : curr_line.id;
            var promise = self.orm.call('pos.kitchen.order', 'fetch_same_product_orderlines', [self.pos.get_order().export_as_JSON(), product_id, curr_line.quantity]
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
            })
            return promise
        }
    },
    async _addProduct(product, options) {
        var self = this;
        var promise = self.update_orderline_status(product)
        if (promise) {
            promise.then(function (res) {
                self.currentOrder.add_product(product, options);
            })
        } else {
            super._addProduct(product, options);
        }
    },
    async _setValue(val) {
        var self = this;
        var pos = self.pos;
        var order = self.currentOrder;
        var pos_categ_ids = [];
        var curr_orderline = order.get_selected_orderline();

        Object.values(pos.db.pos_screen_data).forEach(data => {
            pos_categ_ids = pos_categ_ids.concat(data.pos_category_ids);
        });

        if (curr_orderline) {
            if(pos_categ_ids.filter(categ => curr_orderline.product.pos_categ_ids.includes(categ))){
                curr_orderline.mp_dirty = true;
                $('.order-submit').addClass('highlight')
            }

            if (pos.numpadMode === 'quantity') {
                var product_id = curr_orderline.product ? curr_orderline.product.id : curr_orderline.id;
                var promise = await self.orm.call('pos.kitchen.order', 'fetch_same_product_orderlines', [order.export_as_JSON(), product_id, curr_orderline.quantity]
                ).then(function (res) {
                    order.orderlines.forEach(function (line) {
                        res.forEach(function (res_line) {
                            if (res_line[0].wk_cid == line.wk_cid) {
                                line.is_orderline_done = res_line[0].is_orderline_done;
                            }
                        })
                    });

                    if (pos.config.is_done_orderline_restricted && curr_orderline && curr_orderline.is_orderline_done) {
                        if(pos_categ_ids.filter(categ => curr_orderline.product.pos_categ_ids.includes(categ))){
                            curr_orderline.mp_dirty = false;
                            $('.order-submit').removeClass('highlight')
                        }

                        self.showPopup('WkErrorKSPopopWidget', {
                            title: self._t('Not Allowed'),
                            body: self._t("This orderline is marked as done so it cannot be modified now."),
                        });
                    } else if (val === 'remove' && !curr_orderline.is_orderline_done) {
                        if (order.removed_line.lines) {
                            order.removed_line.lines.push({
                                wk_cid: curr_orderline.wk_cid,
                                product_id: curr_orderline.product.id,
                                name: curr_orderline.get_full_product_name(),
                                note: curr_orderline.note,
                                quantity: curr_orderline.kitchen_sent_qty,
                                discount: curr_orderline.discount,
                                price: curr_orderline.price,
                            });
                        }
                        self.currentOrder.removeOrderline(curr_orderline);
                    } else if (!curr_orderline.is_orderline_done) {
                        const wk_result = curr_orderline.set_quantity(val);
                        if (!wk_result) NumberBuffer.reset();
                    }
                }).catch(function (error) {
                    console.log("error", error);
                });
            } else {
                super._setValue(val);
            }
        }
    }
});

patch(ClosePosPopup.prototype, {
    async confirm() {
        var pendingOrders = this.props.info.pendingOrders;
        if(pendingOrders){
            const { confirmed } = await this.showPopup('ConfirmPopup', {
                title: this._t('Pending Kitchen Orders'),
                body: `There are ${pendingOrders} pending kitchen orders related to this session, Do you want to cancel those Orders and Proceed?`,
            });
            if (confirmed) {
                this.orm.call('pos.kitchen.order', 'done_pos_pending_order', [this.pos.config.current_session_id[0]],
                ).catch(function (error) {
                    console.log("error", error);
                });
                super.confirm();
            }
        }
        else super.confirm();
    }
});