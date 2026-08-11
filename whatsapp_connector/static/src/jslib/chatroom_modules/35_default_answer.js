odoo.define('@whatsapp_connector/chatroom_mod/default-answer', ['@web/core/l10n/translation', '@web/core/errors/error_dialogs', '@odoo/owl', '@whatsapp_connector/chatroom_mod/conversation-model', '@whatsapp_connector/chatroom_mod/default-answer-model', '@whatsapp_connector/chatroom_mod/default-answer-send'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation')
    const { WarningDialog } = require('@web/core/errors/error_dialogs')
    const { Component } = require('@odoo/owl')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const { DefaultAnswerModel } = require('@whatsapp_connector/chatroom_mod/default-answer-model')
    const { buildSendOptions, snippetNeedsAttachment } = require('@whatsapp_connector/chatroom_mod/default-answer-send')
    const DefaultAnswer = __exports.DefaultAnswer = class DefaultAnswer extends Component {
        setup() {
            super.setup()
            this.env
            this.props
        }
        async sendAnswer(event) {
            let out = Promise.resolve()
            if (event) { event.target.disabled = true }
            if (this.props.selectedConversation && this.props.selectedConversation.isCurrent()) {
                const da = this.props.defaultAnswer
                let codeResult = undefined
                if (da.ttype === 'code') {
                    try {
                        codeResult = await this.env.services.orm.call('acrux.chat.default.answer', 'eval_answer', [[da.id], this.props.selectedConversation.id], { context: this.env.context })
                    } catch (e) {
                        this.env.services.dialog.add(WarningDialog, { message: String(e.message || e) })
                        return out.finally(() => { if (event) { event.target.disabled = false } })
                    }
                    if (codeResult === null || codeResult === undefined) {
                        this.env.services.dialog.add(WarningDialog, { message: _t('This snippet did not return any text (set `result` in the Python code).') })
                        return out.finally(() => { if (event) { event.target.disabled = false } })
                    }
                    if (String(codeResult).trim() === '') {
                        this.env.services.dialog.add(WarningDialog, { message: _t('The Python snippet returned an empty message.') })
                        return out.finally(() => { if (event) { event.target.disabled = false } })
                    }
                }
                const options = buildSendOptions(da, da.ttype === 'code' ? { codeResult } : {})
                let text = options.text
                if ((da.ttype === 'text' || da.ttype === 'code') && (text !== null && text !== undefined && String(text).trim() !== '')) {
                    text = typeof text !== 'string' ? String(text) : text
                    this.env.chatBus.trigger('setInputText', text)
                } else {
                    if (snippetNeedsAttachment(da) && (!da.resModel || !da.resId)) {
                        this.env.services.dialog.add(WarningDialog, { message: _t('This default reply has no file attached. Configure it under Default Answers.') })
                        return out.finally(() => { if (event) { event.target.disabled = false } })
                    }
                    out = this.props.selectedConversation.createMessage(options)
                }
            } else { this.env.services.dialog.add(WarningDialog, { message: _t('You must select a conversation.') }) }
            return out.finally(() => { if (event) { event.target.disabled = false } })
        }
    }
    Object.assign(DefaultAnswer, { template: 'chatroom.DefaultAnswer', props: { selectedConversation: ConversationModel.prototype, defaultAnswer: DefaultAnswerModel.prototype, }, })
    return __exports;
});;
