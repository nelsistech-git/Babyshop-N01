odoo.define('custom_stock.MiniInventoryAdjustment', function (require) {
"use strict";

var core = require('web.core');
var ListController = require('web.ListController');
    var SalesPriceVariantUpdate = ListController.include({
       renderButtons: function($node) {
       this._super.apply(this, arguments);
           if (this.$buttons) {
             this.$buttons.find('.oe_action_btn_mini_inventory_adjustment').click(this.proxy('action_in_adjustment'));
           }
        },

    action_in_adjustment: function (e) {
        var self = this;
        var active_id = this.model.get(this.handle).getContext()['active_ids'];
        var model_name = this.model.get(this.handle).getContext()['active_model'];
            this._rpc({
                    model: 'mini.product.inventory.adjustment',
                    method: 'js_python_method',
                    args: ["", model_name, active_id],
                }).then(function (result) {
                    self.do_action({
                        name: ("Inventory Adjustment (Qty .1 - Qty .99)"),
                        type: 'ir.actions.act_window',
                        res_model: 'mini.inventory.adjustment.wizard',
                        view_mode: 'form',
                        views: [[false, 'form']],
                        target: 'new'
                    });
                });
   },
});
});
