odoo.define('@whatsapp_connector/chatroom_mod/message-options', ['@web/core/l10n/translation', '@web/core/dialog/dialog', '@whatsapp_connector/chatroom_mod/message-model'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation')
    const { Dialog } = require('@web/core/dialog/dialog')
    const { MessageModel } = require('@whatsapp_connector/chatroom_mod/message-model')
    const { Component } = owl
    const { DateTime } = luxon
    const MessageOptions = __exports.MessageOptions = class MessageOptions extends Component {
        setup() {
            super.setup()
            this.env; this.props;
        }
        answerMessage() {
            this.props.env.chatBus.trigger('quoteMessage', this.props.message)
            this.props.close()
        }
        deleteMessageDialog() {
            class DeleteDialog extends Component {
                deleteForMe() {
                    this.props.deleteMessage(true)
                    this.props.close()
                }
                deleteForAll() {
                    this.props.deleteMessage(false)
                    this.props.close()
                }
            }
            DeleteDialog.components = { Dialog }
            DeleteDialog.template = 'chatroom.DeleteMessage'
            this.props.close()
            const props = { allowDeleteAll: this.getAllowDeleteAll(), deleteMessage: this.deleteMessage.bind(this), title: _t('Confirmation') }
            this.env.services.dialog.add(DeleteDialog, props)
        }
        getAllowDeleteAll() {
            let allowDeleteAll = true
            if (this.props.message.fromMe) {
                const now = DateTime.now()
                const { days } = now.diff(this.props.message.dateMessage, 'days').toObject()
                const { minutes } = now.diff(this.props.message.dateMessage, 'minutes').toObject()
                if (Math.floor(days) > 0) { allowDeleteAll = false } else if (Math.floor(minutes) > 59) { allowDeleteAll = false }
            } else { allowDeleteAll = false }
            return allowDeleteAll
        }
        async deleteMessage(forMe) {
            const msgData = await this.env.services.orm.call(this.props.env.chatModel, 'delete_message', [[this.props.message.conversation.id], this.props.message.id, forMe], { context: this.props.env.context })
            this.props.message.conversation.appendMessages(msgData)
        }
    }
    Object.assign(MessageOptions, { template: 'chatroom.MessageOptions', props: { message: MessageModel.prototype, close: Function, env: Object, }, })
    return __exports;
});;
