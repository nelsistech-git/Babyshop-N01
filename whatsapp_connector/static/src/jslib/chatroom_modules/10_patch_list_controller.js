odoo.define('@whatsapp_connector/chatroom_mod/patch-list-controller', ['@web/core/utils/patch', '@web/views/list/list_controller', '@web/core/utils/hooks'], function (require) {
    'use strict'; let __exports = {}; const { patch } = require('@web/core/utils/patch')
    const { ListController } = require('@web/views/list/list_controller')
    const { useBus } = require('@web/core/utils/hooks')
    const chatroomLits = {
        setup() {
            super.setup()
            if (this.props?.chatroomTab) {
                this.archInfo.headerButtons = []
                if (this.env.chatBus) { useBus(this.env.chatBus, 'updateChatroomAction', async ({ detail: chatroomTab }) => { if (this.props.chatroomTab === chatroomTab) { await this.model.load() } }) }
            }
        }, async chatroomSelect() {
            const [selected] = await this.getSelectedResIds()
            if (this.model?.root?.records) {
                const record = this.model.root.records.find(record => record.resId === selected)
                if (record) { await this.props.chatroomSelect(record) }
            }
        }
    }
    patch(ListController.prototype, chatroomLits)
    patch(ListController.props, { showButtons: { type: Boolean, optional: true }, chatroomTab: { type: String, optional: true }, chatroomSelect: { type: Function, optional: true }, })
    return __exports;
});;
