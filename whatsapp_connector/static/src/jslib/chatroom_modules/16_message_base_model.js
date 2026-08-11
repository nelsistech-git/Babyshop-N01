odoo.define('@whatsapp_connector/chatroom_mod/message-base-model', ['@odoo/owl', '@whatsapp_connector/chatroom_mod/chat-base-model'], function (require) {
    'use strict'; let __exports = {}; const { markup } = require('@odoo/owl')
    const { ChatBaseModel } = require('@whatsapp_connector/chatroom_mod/chat-base-model')
    const MessageBaseModel = __exports.MessageBaseModel = class MessageBaseModel extends ChatBaseModel {
        constructor(comp, base) {
            super(comp)
            this.env
            this.id = false
            this.text = ''
            this.textHTML = ''
            this.ttype = ''
            this.resModel = ''
            this.resId = 0
            this.isProduct = false
            this.buttons = []
            this.chatList = { id: false, name: '', buttonText: '' }
            if (base) { this.updateFromJson(base) }
        }
        updateFromJson(base) {
            super.updateFromJson(base)
            if ('id' in base) { this.id = base.id }
            if ('text' in base) {
                this.text = base.text
                this.textHTML = markup(this.parseHTML(this.text))
            }
            if ('ttype' in base) { this.ttype = base.ttype }
            if ('res_model' in base) { this.resModel = base.res_model }
            if ('res_id' in base) { this.resId = base.res_id }
            if ('is_product' in base) { this.isProduct = base.is_product }
            if ('button_ids' in base) { this.buttons = [...base.button_ids] }
            if ('chat_list_id' in base) { this.chatList = this.convertRecordField(base.chat_list_id, ['buttonText']) }
        }
        get chatListRecord() { return this.convertFieldRecord(this.chatList, ['buttonText']) }
        parseHTML(text) {
            const regexBold = /(?:^\*|\s\*)(?:(?!\s))((?:(?!\*|\n|<|>).)+)(?:\*)(?=(\s|,|\.|$))/g
            const textBold = (text || '').replace(regexBold, ' <strong>$1</strong>')
            const regexDel = /(?:^~|\s~)(?:(?!\s))((?:(?!~|\n|<|>).)+)(?:~)(?=(\s|,|\.|$))/g
            const textDel = textBold.replace(regexDel, ' <del>$1</del>')
            const regexUnder = /(?:^_|\s_)(?:(?!\s))((?:(?!_|\n|<|>).)+)(?:_)(?=(\s|,|\.|$))/g
            const textUnder = textDel.replace(regexUnder, ' <em>$1</em>')
            const regexURLs = /(https?:\/\/[^\s]+)/g
            const textHTML = textUnder.replace(regexURLs, url => { url = url.replace(/<\/?[^>]+(>|$)/g, ""); return `<a href="${url}" target="_blank">${url}</a>` })
            return textHTML
        }
    }
    return __exports;
});;
