odoo.define('@whatsapp_connector/chatroom_mod/patch-action-dialog', ['@web/core/utils/patch', '@web/webclient/actions/action_dialog', '@odoo/owl'], function (require) {
    'use strict'; let __exports = {}; const { patch } = require('@web/core/utils/patch')
    const { ActionDialog } = require('@web/webclient/actions/action_dialog')
    const { onWillDestroy, useEffect } = require('@odoo/owl')
    const chatroomDialogHack = {
        setup() {
            super.setup()
            this.env.bus.trigger('last-dialog', this)
            onWillDestroy(() => this.env.bus.trigger('last-dialog', null))
            useEffect(() => {
                if (this.props?.actionProps?.context?.chatroom_wizard_search) {
                    const defaultButton = this.modalRef.el.querySelector('.modal-footer button.o-default-button')
                    defaultButton.classList.add('d-none')
                }
            }, () => [])
        },
    }
    patch(ActionDialog.prototype, chatroomDialogHack)
    return __exports;
});;
