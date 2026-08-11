odoo.define('@whatsapp_connector/chatroom_mod/conversation-header', ['@web/core/l10n/translation', '@odoo/owl', '@whatsapp_connector/chatroom_mod/conversation-model'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation')
    const { Component } = require('@odoo/owl')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const ConversationHeader = __exports.ConversationHeader = class ConversationHeader extends Component {
        setup() {
            super.setup()
            this.env
            this.props
        }
        avatarInitials() {
            const n = (this.props.selectedConversation?.name || '').trim()
            if (!n) {
                return '?'
            }
            const parts = n.split(/\s+/).filter(Boolean)
            if (parts.length >= 2) {
                return (parts[0][0] + parts[1][0]).toUpperCase()
            }
            return n.slice(0, 2).toUpperCase()
        }
        statusLabel() {
            const s = this.props.selectedConversation?.status
            if (s === 'new') {
                return _t('Waiting')
            }
            if (s === 'current') {
                return _t('Attending')
            }
            if (s === 'done') {
                return _t('Closed')
            }
            return s || ''
        }
        statusBadgeClass() {
            const s = this.props.selectedConversation?.status
            if (s === 'new') {
                return 'badge rounded-pill text-bg-warning'
            }
            if (s === 'current') {
                return 'badge rounded-pill text-bg-success'
            }
            if (s === 'done') {
                return 'badge rounded-pill text-bg-secondary'
            }
            return 'badge rounded-pill text-bg-light border'
        }
        connectorLabel() {
            const n = this.props.selectedConversation?.connector?.name
            return n || ''
        }
        agentLabel() {
            const conv = this.props.selectedConversation
            if (!conv?.agent?.id || conv.isMine()) {
                return ''
            }
            return _t('Agent: %s', conv.agent.name)
        }
        assignedShortLabel() {
            return _t('Assigned')
        }
        assignedHint() {
            return _t('Needs attention')
        }
    }
    Object.assign(ConversationHeader, { template: 'chatroom.ConversationHeader', props: { selectedConversation: ConversationModel.prototype, }, components: {}, })
    return __exports;
});;
