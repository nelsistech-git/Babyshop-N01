odoo.define('@whatsapp_connector/chatroom_mod/product-model', ['@web/core/l10n/dates', '@whatsapp_connector/chatroom_mod/chat-base-model'], function (require) {
    'use strict'; let __exports = {}; const { parseDateTime, formatDateTime } = require('@web/core/l10n/dates')
    const { ChatBaseModel } = require('@whatsapp_connector/chatroom_mod/chat-base-model')
    const ProductModel = __exports.ProductModel = class ProductModel extends ChatBaseModel {
        constructor(comp, base) {
            super(comp)
            this.env
            this.id = false
            this.displayName = ''
            this.lstPrice = 0.0
            this.uom = { id: false, name: '' }
            this.writeDate = null
            this.productTmpl = { id: false, name: '' }
            this.name = ''
            this.type = ''
            this.defaultCode = ''
            this.qtyAvailable = 0.0
            this.showProductText = true
            this.uniqueHashImage = ''
            this.showOptions = true
            if (base) { this.updateFromJson(base) }
        }
        updateFromJson(base) {
            super.updateFromJson(base)
            if ('id' in base) { this.id = base.id }
            if ('display_name' in base) { this.displayName = base.display_name }
            if ('lst_price' in base) { this.lstPrice = base.lst_price }
            if ('uom_id' in base) { this.uom = this.convertRecordField(base.uom_id) }
            if ('write_date' in base) {
                this.writeDate = parseDateTime(base.write_date)
                this.uniqueHashImage = formatDateTime(this.writeDate).replace(/[^0-9]/g, '')
            }
            if ('product_tmpl_id' in base) { this.productTmpl = this.convertRecordField(base.product_tmpl_id) }
            if ('name' in base) { this.name = base.name }
            if ('type' in base) { this.type = base.type }
            if ('default_code' in base) { this.defaultCode = base.default_code }
            if ('qty_available' in base) { this.qtyAvailable = base.qty_available }
            if ('show_product_text' in base) { this.showProductText = base.show_product_text }
            if ('show_options' in base) { this.showOptions = base.show_options }
        }
    }
    return __exports;
});;
