odoo.define('@whatsapp_connector/chatroom_mod/conversation-panel-form', ['@web/core/utils/patch', '@whatsapp_connector/chatroom_mod/chatroom-action-tab'], function (require) {
    'use strict'; let __exports = {}; const { patch } = require('@web/core/utils/patch')
    const { ChatroomActionTab } = require('@whatsapp_connector/chatroom_mod/chatroom-action-tab')
    const ConversationPanelForm = __exports.ConversationPanelForm = class ConversationPanelForm extends ChatroomActionTab {
        setup() {
            super.setup()
            this.env;
        }
    }
    ConversationPanelForm.props = Object.assign({}, ConversationPanelForm.props)
    ConversationPanelForm.defaultProps = Object.assign({}, ConversationPanelForm.defaultProps)
    patch(ConversationPanelForm.props, { viewModel: { type: String, optional: true }, viewType: { type: String, optional: true }, viewKey: { type: String, optional: true }, })
    patch(ConversationPanelForm.defaultProps, { viewModel: 'acrux.chat.panel', viewType: 'form', viewKey: 'conv_panel_form', })
    return __exports;
});;
