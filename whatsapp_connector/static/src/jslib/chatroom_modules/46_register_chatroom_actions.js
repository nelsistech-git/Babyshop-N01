odoo.define('@whatsapp_connector/chatroom_mod/register-chatroom-actions', ['@web/core/registry', '@whatsapp_connector/chatroom_mod/chatroom'], function (require) {
    'use strict'; let __exports = {}; const { registry } = require('@web/core/registry')
    const { Chatroom } = require('@whatsapp_connector/chatroom_mod/chatroom')
    registry.category('actions').add('acrux.chat.conversation_tag', Chatroom)
    registry.category('actions').add('acrux.chat.null_action_tag', () => { })
    return __exports;
});;
