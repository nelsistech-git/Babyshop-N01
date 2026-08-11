odoo.define('@whatsapp_connector/chatroom_mod/patch-form-controller', ['@web/core/utils/patch', '@web/views/form/form_controller', '@odoo/owl', '@web/core/utils/hooks'], function (require) {
    'use strict'; let __exports = {}; const { patch } = require('@web/core/utils/patch')
    const { FormController } = require('@web/views/form/form_controller')
    const { useSubEnv } = require('@odoo/owl')
    const { useBus } = require('@web/core/utils/hooks')
    const chatroomForms = {
        setup() {
            super.setup()
            if (this.env.chatBus) {
                if (this.env.config) {
                    const config = { ...this.env.config }
                    config.historyBack = () => { }
                    useSubEnv({ config })
                }
                useBus(this.env.chatBus, 'updateChatroomAction', async ({ detail: chatroomTab }) => { if (this.props.chatroomTab === chatroomTab) { await this.model.load() } })
            }
        }, updateURL() { if (this.env.chatBus) { } else { super.updateURL() } }, async discard() {
            await super.discard()
            if (this.env.chatBus) { if (this.model.root.isNew && this.props.resId) { await this.model.load({ resId: this.props.resId }) } }
        }
    }
    patch(FormController.prototype, chatroomForms)
    patch(FormController.props, { chatroomTab: { type: String, optional: true }, searchButton: { type: Boolean, optional: true }, searchButtonString: { type: String, optional: true }, searchAction: { type: Function, optional: true }, })
    return __exports;
});;
