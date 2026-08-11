odoo.define('@whatsapp_connector/chatroom_mod/chatroom-header', ['@odoo/owl'], function (require) {
    'use strict'; let __exports = {}; const { Component } = require('@odoo/owl')
    const ChatroomHeader = __exports.ChatroomHeader = class ChatroomHeader extends Component { setup() { super.setup() } }
    Object.assign(ChatroomHeader, { template: 'chatroom.ChatroomHeader', props: { slots: Object, className: { type: String, optional: true } }, defaultProps: { className: '' } })
    return __exports;
});;
