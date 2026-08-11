odoo.define('@whatsapp_connector/chatroom_mod/conversation', ['@web/session', '@odoo/owl', '@mail/core/common/relative_time', '@whatsapp_connector/chatroom_mod/conversation-model'], function (require) {
    'use strict'; let __exports = {}; const { session } = require('@web/session')
    const { Component } = require('@odoo/owl')
    const { RelativeTime } = require('@mail/core/common/relative_time')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const Conversation = __exports.Conversation = class Conversation extends Component {
        setup() {
            super.setup()
            this.env
            this.props
        }
        onSelect() { this.env.chatBus.trigger(this.props.selectTrigger, { conv: this.props.conversation }) }
        async onClose(event) {
            event.stopPropagation()
            if (session.chatroom_release_conv_on_close) { await this.props.conversation.close() }
            this.env.chatBus.trigger(this.props.deleteTrigger, this.props.conversation)
        }
        get isSelected() {
            const { selectedConversation, conversation } = this.props
            return (conversation.id === selectedConversation?.id)
        }
    }
    Object.assign(Conversation, { template: 'chatroom.Conversation', props: { conversation: ConversationModel.prototype, selectedConversation: { type: ConversationModel.prototype, optional: true }, hideClose: { type: Boolean, optional: true }, selectTrigger: { type: String, optional: true }, deleteTrigger: { type: String, optional: true }, listTick: { type: Number, optional: true }, }, defaultProps: { hideClose: false, selectTrigger: 'selectConversation', deleteTrigger: 'deleteConversation', listTick: 0, }, components: { RelativeTime, } })
    return __exports;
});;
