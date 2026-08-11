odoo.define('@whatsapp_connector/chatroom_mod/conversation-card', ['@odoo/owl', '@whatsapp_connector/chatroom_mod/conversation-model'], function (require) {
    'use strict'; let __exports = {}; const { Component } = require('@odoo/owl')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const ConversationCard = __exports.ConversationCard = class ConversationCard extends Component {
        setup() {
            super.setup()
            this.env;
        }
        onClick() { this.env.chatBus.trigger(this.props.selectTrigger, this.props.conversation) }
    }
    Object.assign(ConversationCard, { template: 'chatroom.ConversationCard', props: { conversation: ConversationModel.prototype, className: { type: String, optional: true }, selectTrigger: { type: String, optional: true }, }, defaultProps: { className: '', selectTrigger: 'initAndNotifyConversation', }, components: {} })
    return __exports;
});;
