odoo.define('@whatsapp_connector/chatroom_mod/conversation-form', ['@web/core/utils/patch', '@whatsapp_connector/chatroom_mod/chatroom-action-tab'], function (require) {
    'use strict'; let __exports = {}; const { patch } = require('@web/core/utils/patch')
    const { ChatroomActionTab } = require('@whatsapp_connector/chatroom_mod/chatroom-action-tab')
    const ConversationForm = __exports.ConversationForm = class ConversationForm extends ChatroomActionTab {
        setup() {
            super.setup()
            this.env;
        }
        async onSave(record) {
            await super.onSave(record)
            await this.env.services.orm.call(this.env.chatModel, 'update_conversation_bus', [record.resIds], { context: this.env.context })
        }
    }
    ConversationForm.props = Object.assign({}, ConversationForm.props)
    ConversationForm.defaultProps = Object.assign({}, ConversationForm.defaultProps)
    patch(ConversationForm.props, { viewResId: { type: Number }, viewModel: { type: String, optional: true }, viewType: { type: String, optional: true }, viewKey: { type: String, optional: true }, })
    patch(ConversationForm.defaultProps, { viewModel: 'acrux.chat.conversation', viewType: 'form', viewKey: 'conv_form', })
    return __exports;
});;
