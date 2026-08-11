/** @odoo-module */

// odoo.define('pos_receipt_image_odoo.models', function (require) {
// "use strict";

//var models = require('point_of_sale.models');
//var _super_Orderline = models.Orderline.prototype;

//models.Orderline = models.Orderline.extend({
//    export_for_printing: function () {
//        var receipt_line = _super_Orderline.export_for_printing.apply(this, arguments);
//        var product = this.get_product();
//        var image_url = `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
//        receipt_line = _.extend(receipt_line, {
//            'product_logo': image_url,
//        })
//        return receipt_line
//    },
//});
    // var { Order, Orderline } = require('point_of_sale.models');
    import { Order, Orderline } from "@point_of_sale/app/store/models";
    import { patch } from "@web/core/utils/patch";

    // const Registries = require('point_of_sale.Registries');

    // const PosrecSaleOrderline = (Orderline) => class PosrecSaleOrderline extends Orderline {
    patch(Orderline.prototype, {

        // export_for_printing() {
        getDisplayData() {
            return {
                ...super.getDisplayData(),
                product_logo: this.get_product().getImageUrl(),

            };
            // var product = this.get_product();
            // var json = super.export_for_printing(...arguments);
            // var image_url = `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
            // json.product_logo = image_url;
            // return json;
        },
    });
// Registries.Model.extend(Orderline, PosrecSaleOrderline);

// });
