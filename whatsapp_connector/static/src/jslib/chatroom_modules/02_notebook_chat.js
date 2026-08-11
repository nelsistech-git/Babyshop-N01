odoo.define('@whatsapp_connector/chatroom_mod/notebook-chat', ['@web/core/notebook/notebook'], function (require) {
    'use strict'; let __exports = {}; const { Notebook } = require('@web/core/notebook/notebook')
    const NotebookChat = __exports.NotebookChat = class NotebookChat extends Notebook { }
    NotebookChat.template = 'chatroom.Notebook'
    return __exports;
});;
