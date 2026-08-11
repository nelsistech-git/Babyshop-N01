odoo.define('custom_product_common.ProductUpload', function (require) {
"use strict";

    var core = require('web.core');
    var KanbanController = require('web.KanbanController');
    var ListController = require('web.ListController');

    var ProductUploadKanban = KanbanController.include({
           renderButtons: function($node) {
           this._super.apply(this, arguments);
               if (this.$buttons) {
                 this.$buttons.find('.oe_action_btn_product_upload').click(this.proxy('action_product_upload'));
               }
            },

        action_product_upload: function (e) {
            var self = this;
            var active_id = this.model.get(this.handle).getContext()['active_ids'];
            var model_name = this.model.get(this.handle).getContext()['active_model'];
                this._rpc({
                        model: 'product.template',
                        method: 'js_python_method',
                        args: ["", model_name, active_id],
                    }).then(function (result) {
                        self.do_action({
                            name: ("Product Upload"),
                            type: 'ir.actions.act_window',
                            res_model: 'product.upload.wizard',
                            view_mode: 'form',
                            views: [[false, 'form']],
                            target: 'new'
                        });
                    });
       },
    });

    var ProductUploadList = ListController.include({
           renderButtons: function($node) {
           this._super.apply(this, arguments);
               if (this.$buttons) {
                 this.$buttons.find('.oe_action_btn_product_upload').click(this.proxy('action_product_upload'));
               }
            },

        action_product_upload: function (e) {
            var self = this;
            var active_id = this.model.get(this.handle).getContext()['active_ids'];
            var model_name = this.model.get(this.handle).getContext()['active_model'];
                this._rpc({
                        model: 'product.template',
                        method: 'js_python_method',
                        args: ["", model_name, active_id],
                    }).then(function (result) {
                        self.do_action({
                            name: ("Product Upload"),
                            type: 'ir.actions.act_window',
                            res_model: 'product.upload.wizard',
                            view_mode: 'form',
                            views: [[false, 'form']],
                            target: 'new'
                        });
                    });
       },
    });
});
