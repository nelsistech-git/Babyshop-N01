odoo.define('@whatsapp_connector/chatroom_mod/chat-base-model', [], function (require) {
    'use strict'; let __exports = {}; const ChatBaseModel = __exports.ChatBaseModel = class ChatBaseModel {
        constructor(comp) { this.env = comp.env }
        updateFromJson() { }
        async buildExtraObj() { }
        convertRecordField(record, extraFields) {
            let out
            if (record) {
                out = { id: record[0], name: record[1] }
                for (let i = 2, j = 0; i < record.length && j < extraFields.length; ++i, ++j) { out[extraFields[j]] = record[i] }
            } else {
                out = { id: false, name: '' }
                if (extraFields) { for (const extraField of extraFields) { out[extraField] = '' } }
            }
            return out
        }
        convertFieldRecord(record, extraFields) {
            let out = [false, '']
            if (record) {
                out = [record.id, record.name]
                for (const extraField of extraFields) { out.push(record[extraField]) }
            } else { extraFields.forEach(() => out.push('')) }
            return out
        }
    }
    return __exports;
});;
