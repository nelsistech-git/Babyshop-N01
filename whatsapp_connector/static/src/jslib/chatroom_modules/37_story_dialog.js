odoo.define('@whatsapp_connector/chatroom_mod/story-dialog', ['@web/core/l10n/translation', '@web/core/dialog/dialog', '@web/views/fields/many2one_avatar/many2one_avatar_field', '@odoo/owl', '@whatsapp_connector/chatroom_mod/attachment-list', '@whatsapp_connector/chatroom_mod/message-model', '@whatsapp_connector/chatroom_mod/audio-player', '@whatsapp_connector/chatroom_mod/message-metadata', '@whatsapp_connector/chatroom_mod/message-options'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation')
    const { Dialog } = require('@web/core/dialog/dialog')
    const { Many2OneAvatarField } = require('@web/views/fields/many2one_avatar/many2one_avatar_field')
    const { Component, xml, useRef } = require('@odoo/owl')
    const { AttachmentList } = require('@whatsapp_connector/chatroom_mod/attachment-list')
    const { MessageModel } = require('@whatsapp_connector/chatroom_mod/message-model')
    const { AudioPlayer } = require('@whatsapp_connector/chatroom_mod/audio-player')
    const { MessageMetadata } = require('@whatsapp_connector/chatroom_mod/message-metadata')
    const { MessageOptions } = require('@whatsapp_connector/chatroom_mod/message-options')
    const StoryDialog = __exports.StoryDialog = class StoryDialog extends Component {
        static template = xml`
<Dialog size="'xl'" fullscreen="true" bodyClass="'o_acrux_story_dialog'" title="props.title">
    <div class="acrux_story_dialog_frame d-flex justify-content-center align-items-center py-3">
        <img t-attf-src="{{props.url}}" alt="" loading="lazy" class="acrux_story_dialog_img img-fluid rounded-3 shadow-lg" style="max-width: min(960px, 100%); max-height: calc(100vh - 8rem);" />
    </div>
</Dialog>`; static components = { Dialog }
        static props = { close: { type: Function, optional: true }, mime: String, url: String, title: String, }
    }
    const Message = __exports.Message = class Message extends Component {
        setup() {
            super.setup()
            this.env; this.props; this.optionsRef = useRef('optionsRef')
        }
        messageCssClass() {
            const list = this.messageCssClassList()
            if (this.props.message.dateDelete) { list.push('o_chat_msg_deleted') }
            return list.join(' ')
        }
        messageCssClassList() { return [] }
        async onTranscribe() {
            const { orm } = this.env.services
            const data = await orm.call('acrux.chat.message', 'transcribe', [[this.props.message.id], this.env.canTranscribe()], { context: this.env.context })
            this.props.message.transcription = data
        }
        async onTranslate() {
            const { orm } = this.env.services
            const lang = this.env.getCurrentLang()
            const data = await orm.call('acrux.chat.message', 'translate', [[this.props.message.id], this.env.canTranslate(), lang], { context: this.env.context })
            this.props.message.traduction = data
        }
        get canTranslate() { return this.env.canTranslate() && this.props.message.ttype !== 'sticker' }
        get avatarProps() { return { name: 'createUid', relation: 'res.users', string: _t('Agent'), readonly: true, record: { data: { createUid: [this.props.message.createUid.id, this.props.message.createUid.name] } } } }
        openStoryImage() {
            const { mime, data } = this.props.message.resModelObj
            const url = `data:${mime};base64,${data}`
            this.env.services.dialog.add(StoryDialog, { url, mime, title: _t('Story') })
        }
        async openOdooChat() {
            const threadService = await odoo.__WOWL_DEBUG__.root.env.services["mail.thread"]
            threadService.openChat({ userId: this.props.message.createUid.id })
        }
        showMessageOption() {
            if (this.optionsPopoverCloseFn) {
                this.optionsPopoverCloseFn()
                this.optionsPopoverCloseFn = null
            } else {
                if (this.props.message.conversation?.isCurrent()) {
                    this.optionsPopoverCloseFn = this.env.services.popover.add(this.optionsRef.el, MessageOptions, {
                        message: this.props.message, env: this.env, close: () => {
                            if (this.optionsPopoverCloseFn) {
                                this.optionsPopoverCloseFn()
                                this.optionsPopoverCloseFn = null
                            }
                        },
                    }, { position: 'bottom', onClose: () => this.optionsPopoverCloseFn = null },)
                }
            }
        }
        clickQuoteMessage(ev) {
            ev.stopPropagation()
            const messages = this.props.message.conversation.messages
            const quote = messages.find(msg => msg.id === this.props.message.quote.id)
            const data = { message: quote ? quote : messages[0] }
            if (quote) {
                data.effect = 'blink'
                data.className = 'active_quote'
            }
            this.env.chatBus.trigger('inmediateScrollToMessage', data)
        }
    }
    Object.assign(Message, { template: 'chatroom.Message', props: { message: MessageModel.prototype, noAction: { type: Boolean, optional: true }, timeTick: { type: Number, optional: true }, }, defaultProps: { noAction: false, timeTick: 0 }, components: { AttachmentList, AudioPlayer, MessageMetadata, Many2OneAvatarField, MessageOptions, Message, } })
    return __exports;
});;
