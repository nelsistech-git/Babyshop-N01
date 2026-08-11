odoo.define('@whatsapp_connector/chatroom_mod/patch-control-panel', ['@web/core/utils/patch', '@web/search/control_panel/control_panel'], function (require) {
    'use strict'; let __exports = {}; const { patch } = require('@web/core/utils/patch')
    const { ControlPanel } = require('@web/search/control_panel/control_panel')
    const chatroomBreadcrumb = { onBreadcrumbClicked(jsId) { if (this.env.chatBus) { if (this.breadcrumbs.findIndex(item => item.jsId === jsId)) { super.onBreadcrumbClicked(jsId) } else { } } else { super.onBreadcrumbClicked(jsId) } } }
    patch(ControlPanel.prototype, chatroomBreadcrumb)
    return __exports;
});;
