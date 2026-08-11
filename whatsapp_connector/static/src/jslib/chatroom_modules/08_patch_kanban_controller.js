odoo.define('@whatsapp_connector/chatroom_mod/patch-kanban-controller', ['@web/core/utils/patch', '@web/views/kanban/kanban_controller', '@web/core/utils/hooks'], function (require) {
    'use strict'; let __exports = {}; const { patch } = require('@web/core/utils/patch')
    const { KanbanController } = require('@web/views/kanban/kanban_controller')
    const { useBus } = require('@web/core/utils/hooks')
    const chatroomKanban = {
        setup() {
            super.setup()
            if (this.props?.chatroomTab && this.env.chatBus) {
                useBus(this.env.chatBus, 'updateChatroomAction', async ({ detail: chatroomTab }) => {
                    if (this.props.chatroomTab === chatroomTab) {
                        await this.model.root.load()
                        await this.onUpdatedPager()
                        this.render(true)
                    }
                })
            }
        }, async openRecord(record, mode) { if (this.props?.chatroomTab && this.props?.chatroomOpenRecord) { await this.props?.chatroomOpenRecord(record, mode) } else { await super.openRecord(record, mode) } }
    }
    patch(KanbanController.prototype, chatroomKanban)
    patch(KanbanController.props, { chatroomTab: { type: String, optional: true }, chatroomOpenRecord: { type: Function, optional: true }, })
    return __exports;
});;
