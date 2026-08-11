odoo.define('@whatsapp_connector/chatroom_mod/user-model', ['@whatsapp_connector/chatroom_mod/chat-base-model'], function (require) {
    'use strict'; let __exports = {}; const { ChatBaseModel } = require('@whatsapp_connector/chatroom_mod/chat-base-model')
    const UserModel = __exports.UserModel = class UserModel extends ChatBaseModel {
        constructor(comp, base) {
            super(comp)
            this.env
            this.id = 0
            this.status = false
            this.signingActive = false
            this.tabOrientation = 'vertical'
            if (base) { this.updateFromJson(base) }
        }
        updateFromJson(base) {
            super.updateFromJson(base)
            if ('id' in base) { this.id = base.id }
            if ('acrux_chat_active' in base) { this.status = base.acrux_chat_active }
            if ('chatroom_signing_active' in base) { this.signingActive = base.chatroom_signing_active }
            if ('chatroom_tab_orientation' in base) { this.tabOrientation = base.chatroom_tab_orientation }
        }
    }
    return __exports;
});;
