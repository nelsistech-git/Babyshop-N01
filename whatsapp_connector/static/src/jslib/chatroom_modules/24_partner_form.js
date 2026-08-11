odoo.define('@whatsapp_connector/chatroom_mod/partner-form', ['@web/core/utils/patch', '@whatsapp_connector/chatroom_mod/chatroom-action-tab', '@whatsapp_connector/chatroom_mod/conversation-model'], function (require) {
    'use strict'; let __exports = {}; const { patch } = require('@web/core/utils/patch')
    const { ChatroomActionTab } = require('@whatsapp_connector/chatroom_mod/chatroom-action-tab')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const PartnerForm = __exports.PartnerForm = class PartnerForm extends ChatroomActionTab {
        setup() {
            super.setup()
            this.env; this.props
        }
        getExtraContext(props) { return Object.assign(super.getExtraContext(props), { default_mobile: props.selectedConversation.numberFormat, default_phone: props.selectedConversation.numberFormat, default_name: props.selectedConversation.name, default_user_id: this.env.services.user.userId, }) }
        async onSave(record) {
            await super.onSave(record)
            if (record.resId !== this.props.selectedConversation.partner.id) { await this.savePartner([record.resId, record.data.display_name]) }
        }
    }
    PartnerForm.props = Object.assign({}, PartnerForm.props)
    PartnerForm.defaultProps = Object.assign({}, PartnerForm.defaultProps)
    patch(PartnerForm.props, { selectedConversation: { type: ConversationModel.prototype }, viewModel: { type: String, optional: true }, viewType: { type: String, optional: true }, viewKey: { type: String, optional: true }, })
    patch(PartnerForm.defaultProps, { viewModel: 'res.partner', viewType: 'form', viewKey: 'partner_form', })
    return __exports;
});;
