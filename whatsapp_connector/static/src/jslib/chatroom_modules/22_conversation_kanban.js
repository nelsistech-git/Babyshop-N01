odoo.define('@whatsapp_connector/chatroom_mod/conversation-kanban', ['@web/core/l10n/translation', '@web/core/utils/patch', '@whatsapp_connector/chatroom_mod/chatroom-action-tab'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation')
    const { patch } = require('@web/core/utils/patch')
    const { ChatroomActionTab } = require('@whatsapp_connector/chatroom_mod/chatroom-action-tab')
    const ConversationKanban = __exports.ConversationKanban = class ConversationKanban extends ChatroomActionTab {
        setup() {
            super.setup()
            this.env;
        }
        getActionProps(props) {
            const out = super.getActionProps(props)
            Object.assign(out, { chatroomOpenRecord: this.openRecord.bind(this) })
            return out
        }
        getExtraContext(props) { return { chatroom_fold_null_group: true, ...super.getExtraContext(props) } }
        async openRecord(record, mode) {
            if (mode === 'edit') {
                const action = { type: 'ir.actions.act_window', name: _t('Edit'), view_type: 'form', view_mode: 'form', res_model: this.env.chatModel, views: [[this.props.formViewId, 'form']], target: 'new', res_id: record.resId, context: { ...this.env.context, only_edit: true }, }
                const onSave = async () => {
                    await this.env.services.orm.call(this.env.chatModel, 'update_conversation_bus', [[record.resId]], { context: this.env.context })
                    await this.env.services.action.doAction({ type: 'ir.actions.act_window_close' })
                }
                await this.env.services.action.doAction(action, { props: { onSave } })
            } else { await this.env.services.orm.call(this.env.chatModel, 'init_and_notify', [[record.resId]], { context: this.env.context },) }
        }
        async onSave(record) { await super.onSave(record) }
    }
    ConversationKanban.props = Object.assign({}, ConversationKanban.props)
    ConversationKanban.defaultProps = Object.assign({}, ConversationKanban.defaultProps)
    patch(ConversationKanban.props, { viewModel: { type: String, optional: true }, viewType: { type: String, optional: true }, viewKey: { type: String, optional: true }, formViewId: { type: Number, optional: true }, })
    patch(ConversationKanban.defaultProps, { viewModel: 'acrux.chat.conversation', viewType: 'kanban', viewKey: 'conv_kanban', })
    return __exports;
});;
