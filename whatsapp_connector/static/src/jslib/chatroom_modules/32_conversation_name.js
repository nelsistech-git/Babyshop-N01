odoo.define('@whatsapp_connector/chatroom_mod/conversation-name', ['@odoo/owl', '@whatsapp_connector/chatroom_mod/conversation-model'], function (require) {
    'use strict'; let __exports = {}; const { Component } = require('@odoo/owl')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const ConversationName = __exports.ConversationName = class ConversationName extends Component {
        setup() {
            super.setup()
            this.env
            this.props
        }
    }
    Object.assign(ConversationName, { template: 'chatroom.ConversationName', props: { selectedConversation: ConversationModel.prototype, }, })
    return __exports;
});;
