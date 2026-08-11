odoo.define('@whatsapp_connector/chatroom_mod/default-answer-model', ['@whatsapp_connector/chatroom_mod/message-base-model'], function (require) {
    'use strict'; let __exports = {}; const { MessageBaseModel } = require('@whatsapp_connector/chatroom_mod/message-base-model')
    const DefaultAnswerModel = __exports.DefaultAnswerModel = class DefaultAnswerModel extends MessageBaseModel {
        constructor(comp, base) {
            super(comp)
            this.env
            this.name = ''
            this.sequence = 0
            if (base) { this.updateFromJson(base) }
        }
        updateFromJson(base) {
            super.updateFromJson(base)
            if ('name' in base) { this.name = base.name }
            if ('sequence' in base) { this.sequence = base.sequence }
        }
    }
    return __exports;
});;
