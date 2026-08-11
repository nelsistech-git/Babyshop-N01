odoo.define('@whatsapp_connector/chatroom_mod/product', ['@odoo/owl', '@web/views/fields/formatters', '@whatsapp_connector/chatroom_mod/product-model'], function (require) {
    'use strict'; let __exports = {}; const { Component } = require('@odoo/owl')
    const { formatMonetary } = require('@web/views/fields/formatters')
    const { ProductModel } = require('@whatsapp_connector/chatroom_mod/product-model')
    const Product = __exports.Product = class Product extends Component {
        setup() {
            super.setup()
            this.env;
        }
        formatPrice(price) { return formatMonetary(price, { currencyId: this.env.getCurrency() }) }
        productOption(event) { this.env.chatBus.trigger('productOption', { product: this.props.product, event }) }
    }
    Object.assign(Product, { template: 'chatroom.Product', props: { product: ProductModel.prototype } })
    return __exports;
});;
