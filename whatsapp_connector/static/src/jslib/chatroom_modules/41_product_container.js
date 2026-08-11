odoo.define('@whatsapp_connector/chatroom_mod/product-container', ['@web/core/l10n/translation', '@web/core/errors/error_dialogs', '@odoo/owl', '@web/core/utils/hooks', '@whatsapp_connector/chatroom_mod/chatroom-header', '@whatsapp_connector/chatroom_mod/chat-search', '@whatsapp_connector/chatroom_mod/product', '@whatsapp_connector/chatroom_mod/conversation-model', '@whatsapp_connector/chatroom_mod/product-model'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation')
    const { WarningDialog } = require('@web/core/errors/error_dialogs')
    const { Component, useState, onWillStart } = require('@odoo/owl')
    const { useBus } = require('@web/core/utils/hooks')
    const { ChatroomHeader } = require('@whatsapp_connector/chatroom_mod/chatroom-header')
    const { ChatSearch } = require('@whatsapp_connector/chatroom_mod/chat-search')
    const { Product } = require('@whatsapp_connector/chatroom_mod/product')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const { ProductModel } = require('@whatsapp_connector/chatroom_mod/product-model')
    const ProductContainer = __exports.ProductContainer = class ProductContainer extends Component {
        setup() {
            super.setup()
            this.env; this.state = useState({ products: [] })
            this.placeHolder = _t('Search')
            useBus(this.env.chatBus, 'productSearch', this.searchProduct)
            useBus(this.env.chatBus, 'productOption', this.productOption)
            onWillStart(async () => this.searchProduct({ detail: {} }))
        }
        async searchProduct({ detail: { search } }) {
            let val = search || ''
            const { orm } = this.env.services
            const result = await orm.call(this.env.chatModel, 'search_product', [val.trim()], { context: this.env.context })
            this.state.products = result.map(product => new ProductModel(this, product))
        }
        async productOption({ detail: { product, event } }) { if (this.props.selectedConversation) { if (this.props.selectedConversation.isCurrent()) { await this.doProductOption({ product, event }) } else { this.env.services.dialog.add(WarningDialog, { message: _t('Yoy are not writing in this conversation.') }) } } else { this.env.services.dialog.add(WarningDialog, { message: _t('You must select a conversation.') }) } }
        async doProductOption({ product }) {
            await this.props.selectedConversation.sendProduct(product.id)
            this.env.chatBus.trigger('mobileNavigate', 'middleSide')
        }
    }
    Object.assign(ProductContainer, { template: 'chatroom.ProductContainer', props: { selectedConversation: ConversationModel.prototype, className: { type: String, optional: true } }, defaultProps: { className: '' }, components: { ChatroomHeader, Product, ChatSearch, } })
    return __exports;
});;
