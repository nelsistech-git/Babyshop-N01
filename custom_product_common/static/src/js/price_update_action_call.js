odoo.define('custom_product_common.SalesPriceUpdate', function (require) {
"use strict";

var core = require('web.core');
var ListController = require('web.ListController');
    var SalesPriceUpdate = ListController.include({
       renderButtons: function($node) {
       this._super.apply(this, arguments);
           if (this.$buttons) {
             this.$buttons.find('.oe_action_btn_price_update').click(this.proxy('action_price_update'));
           }
        },

    action_price_update: function (e) {
        var self = this;
        var active_id = this.model.get(this.handle).getContext()['active_ids'];
        var model_name = this.model.get(this.handle).getContext()['active_model'];
            this._rpc({
                    model: 'sales.price.update',
                    method: 'js_python_method',
                    args: ["", model_name, active_id],
                }).then(function (result) {
                    self.do_action({
                        name: ("Sales Price Update"),
                        type: 'ir.actions.act_window',
                        res_model: 'sales.price.update.wizard',
                        view_mode: 'form',
                        views: [[false, 'form']],
                        target: 'new'
                    });
                });
   },
});
});
