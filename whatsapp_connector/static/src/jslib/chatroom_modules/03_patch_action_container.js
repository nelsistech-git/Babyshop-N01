odoo.define('@whatsapp_connector/chatroom_mod/patch-action-container', ['@web/core/utils/patch', '@web/webclient/actions/action_container'], function (require) {
    'use strict'; let __exports = {}; const { patch } = require('@web/core/utils/patch')
    const { ActionContainer } = require('@web/webclient/actions/action_container')
    const chatroomActions = {
        setup() {
            super.setup()
            this.env.bus.removeEventListener('ACTION_MANAGER:UPDATE', this.onActionManagerUpdate)
            const superOnActionManagerUpdate = this.onActionManagerUpdate
            this.onActionManagerUpdate = ({ detail: info }) => { if (info?.componentProps?.chatroomTab) { } else { superOnActionManagerUpdate({ detail: info }) } }
            this.env.bus.addEventListener('ACTION_MANAGER:UPDATE', this.onActionManagerUpdate)
        },
    }
    patch(ActionContainer.prototype, chatroomActions)
    return __exports;
});;
