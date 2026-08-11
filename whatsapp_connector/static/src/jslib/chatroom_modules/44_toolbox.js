odoo.define('@whatsapp_connector/chatroom_mod/toolbox', ['@web/core/browser/browser', '@web/core/checkbox/checkbox', '@web/core/utils/hooks', '@web/core/transition', '@web/core/select_menu/select_menu', '@web/core/l10n/translation', '@web/core/errors/error_dialogs', '@odoo/owl', '@whatsapp_connector/chatroom_mod/emojis', '@whatsapp_connector/chatroom_mod/activity-button', '@whatsapp_connector/chatroom_mod/use-attachment-uploader', '@whatsapp_connector/chatroom_mod/conversation-model', '@whatsapp_connector/chatroom_mod/message-model', '@whatsapp_connector/chatroom_mod/user-model', '@whatsapp_connector/chatroom_mod/attachment-list', '@whatsapp_connector/chatroom_mod/file-uploader', '@whatsapp_connector/chatroom_mod/story-dialog', '@whatsapp_connector/chatroom_mod/default-answer-send'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation'); const { browser } = require('@web/core/browser/browser')
    const { CheckBox } = require('@web/core/checkbox/checkbox')
    const { useAutofocus } = require('@web/core/utils/hooks')
    const { Transition } = require('@web/core/transition')
    const { SelectMenu } = require('@web/core/select_menu/select_menu')
    const { Component, useRef, useState, useEffect, onWillStart, onWillUpdateProps } = require('@odoo/owl')
    const { useBus } = require('@web/core/utils/hooks')
    const { Emojis } = require('@whatsapp_connector/chatroom_mod/emojis')
    const { ActivityButton } = require('@whatsapp_connector/chatroom_mod/activity-button')
    const { useAttachmentUploader } = require('@whatsapp_connector/chatroom_mod/use-attachment-uploader')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const { MessageModel } = require('@whatsapp_connector/chatroom_mod/message-model')
    const { UserModel } = require('@whatsapp_connector/chatroom_mod/user-model')
    const { AttachmentList } = require('@whatsapp_connector/chatroom_mod/attachment-list')
    const { FileUploader } = require('@whatsapp_connector/chatroom_mod/file-uploader')
    const { Message } = require('@whatsapp_connector/chatroom_mod/story-dialog')
    const { WarningDialog } = require('@web/core/errors/error_dialogs')
    const DA = require('@whatsapp_connector/chatroom_mod/default-answer-send')
    const Toolbox = __exports.Toolbox = class Toolbox extends Component {
        setup() {
            super.setup()
            this.env
            this.props
            this.state = useState(this.getInitState())
            this.attachmentUploader = useAttachmentUploader({ onFileUploaded: this.onAddAttachment.bind(this), buildFormData: this.buildFormDataAttachment.bind(this), })
            this.langs = {}
            this.inputRef = useRef('inputRef')
            this.emojisBtnRef = useRef('emojisBtnRef')
            this.sendBtnRef = useRef('sendBtnRef')
            this.attachBtnRef = useRef('attachBtnRef')
            this.releaseBtnRef = useRef('releaseBtnRef')
            this.inputLangRef = useRef('inputLangRef')
            this.toolboxRef = useRef('toolboxRef')
            this.allInputs = [this.inputRef, this.inputLangRef, this.emojisBtnRef]
            this.wizardAction = null
            useBus(this.env.chatBus, 'setInputText', this.setInputText.bind(this))
            useBus(this.env.chatBus, 'quoteMessage', this.setQuoteMessage.bind(this))
            useAutofocus('inputRef')
            onWillStart(this.willStart.bind(this))
            useEffect(this.enableDisplabeAttachBtn.bind(this), () => [this.state.attachments])
            useEffect(() => {
                const convId = this.props.selectedConversation?.id
                if (convId && this.inputRef.el) {
                    this.restoreDraftForConversation(convId)
                }
            }, () => [this.props.selectedConversation?.id])
            onWillUpdateProps(async (props) => {
                const prevId = this.props?.selectedConversation?.id
                const nextId = props?.selectedConversation?.id
                if (prevId && prevId !== nextId) {
                    this.saveDraftForConversation(prevId)
                }
                await this.updateLangs(props)
                if (this.props?.selectedConversation !== props?.selectedConversation) { this.env.chatBus.trigger('quoteMessage', null) }
            })
        }
        draftStorageKey(convId) { return `acrux_chatroom_draft_${convId}` }
        saveDraftForConversation(convId) {
            if (!convId || !this.inputRef.el) { return }
            sessionStorage.setItem(this.draftStorageKey(convId), this.inputRef.el.value)
            if (this.inputLangRef.el) {
                sessionStorage.setItem(`${this.draftStorageKey(convId)}_lang`, this.inputLangRef.el.value)
            }
        }
        restoreDraftForConversation(convId) {
            if (!convId || !this.inputRef.el) { return }
            const main = sessionStorage.getItem(this.draftStorageKey(convId)) || ''
            const lang = sessionStorage.getItem(`${this.draftStorageKey(convId)}_lang`) || ''
            this.env.chatBus.trigger('setInputText', [main, lang])
        }
        clearDraftForConversation(convId) {
            if (!convId) { return }
            sessionStorage.removeItem(this.draftStorageKey(convId))
            sessionStorage.removeItem(`${this.draftStorageKey(convId)}_lang`)
        }
        scheduleDraftSave() {
            const convId = this.props.selectedConversation?.id
            if (!convId || !this.inputRef.el) { return }
            browser.clearTimeout(this._draftSaveTimer)
            this._draftSaveTimer = browser.setTimeout(() => {
                this._draftSaveTimer = null
                this.saveDraftForConversation(convId)
            }, 320)
        }
        get snippetChips() {
            const answers = this.props.defaultAnswers || []
            return [...answers].sort((a, b) => (a.sequence || 0) - (b.sequence || 0)).slice(0, 8)
        }
        getSnippetChipTitle(answer) {
            return DA.getSnippetChipTitle(answer)
        }
        async insertSnippet(answer) {
            if (!this.inputRef.el) {
                return
            }
            if (!answer) {
                return
            }
            if (!this.props.selectedConversation?.isCurrent()) {
                this.env.services.dialog.add(WarningDialog, { message: _t('You must select a conversation.') })
                return
            }
            if (DA.snippetUsesCreateMessage(answer)) {
                if (DA.snippetNeedsAttachment(answer) && (!answer.resModel || !answer.resId)) {
                    this.env.services.dialog.add(WarningDialog, { message: _t('This default reply has no file attached. Configure it under Default Answers.') })
                    return
                }
                const opts = DA.buildSendOptions(answer, {})
                try {
                    await this.props.selectedConversation.createMessage(opts)
                } catch (e) {
                    this.env.services.dialog.add(WarningDialog, { message: String(e.message || e) })
                }
                return
            }
            let codeResult = undefined
            if (answer.ttype === 'code') {
                try {
                    codeResult = await this.env.services.orm.call('acrux.chat.default.answer', 'eval_answer',
                        [[answer.id], this.props.selectedConversation.id], { context: this.env.context })
                } catch (e) {
                    this.env.services.dialog.add(WarningDialog, { message: String(e.message || e) })
                    return
                }
                if (codeResult === null || codeResult === undefined) {
                    this.env.services.dialog.add(WarningDialog, { message: _t('This snippet did not return any text (set `result` in the Python code).') })
                    return
                }
                if (String(codeResult).trim() === '') {
                    this.env.services.dialog.add(WarningDialog, { message: _t('The Python snippet returned an empty message.') })
                    return
                }
                const opts = DA.buildSendOptions(answer, { codeResult })
                const txt = opts.text !== null && opts.text !== undefined ? String(opts.text) : ''
                if (!txt.trim()) {
                    return
                }
                const cur = this.inputRef.el.value
                const spacer = cur && !cur.endsWith('\n') ? '\n' : ''
                const langVal = this.inputLangRef.el ? this.inputLangRef.el.value : undefined
                this.env.chatBus.trigger('setInputText', [`${cur}${spacer}${txt}`, langVal])
                this.inputRef.el.focus()
                this.scheduleDraftSave()
                return
            }
            if (!answer.text && !answer.name) {
                return
            }
            const txt = DA.resolveFallbackText(answer)
            const chunk = String(txt).trim()
            if (!chunk) {
                return
            }
            const cur = this.inputRef.el.value
            const spacer = cur && !cur.endsWith('\n') ? '\n' : ''
            const langVal = this.inputLangRef.el ? this.inputLangRef.el.value : undefined
            this.env.chatBus.trigger('setInputText', [`${cur}${spacer}${chunk}`, langVal])
            this.inputRef.el.focus()
            this.scheduleDraftSave()
        }
        getInitState() { return { attachments: [], showTraductor: browser.localStorage.getItem('chatroomShowTraductor') === 'true', lang: undefined, message: null, isSending: false, } }
        async willStart() {
            const { orm } = this.env.services
            const data = await orm.call(this.env.chatModel, 'check_object_reference', ['', 'acrux_chat_message_wizard_action'], { context: this.context })
            this.wizardAction = data[1]
            await this.updateLangs(this.props)
        }
        async updateLangs(props) {
            if (props.selectedConversation?.allowedLangIds.length > 0) {
                const langIds = props.selectedConversation.allowedLangIds.filter(lang => !this.langs[lang])
                if (langIds.length > 0) {
                    const allowedLangIds = await this.env.services.orm.call('res.lang', 'name_search', [], { args: [['id', 'in', langIds]], context: { ...this.env.context, active_test: false }, })
                    for (const lang of allowedLangIds) { this.langs[lang[0]] = lang[1] }
                }
                this.state.lang = props.selectedConversation.allowedLangIds[0]
            } else { this.state.lang = undefined }
        }
        get conversationMine() { return this.props.selectedConversation?.isCurrent() ? '' : 'd-none' }
        get conversationNotMine() { return this.props.selectedConversation?.isCurrent() ? 'd-none' : '' }
        get allowSign() {
            const { selectedConversation: conv } = this.props
            return (conv?.isCurrent() && conv.allowSigning ? '' : 'd-none')
        }
        get allowTranslate() { return this.canTranslate ? '' : 'd-none' }
        get hasManyLangs() {
            const { selectedConversation: conv } = this.props
            return this.canTranslate && conv.allowedLangIds.length > 1 ? '' : 'd-none'
        }
        get canTranslate() {
            const { selectedConversation: conv } = this.props
            return !!conv?.allowedLangIds?.length && this.env.canTranslate()
        }
        get langProps() {
            const { allowedLangIds } = this.props?.selectedConversation || { allowedLangIds: [] }
            const out = { choices: allowedLangIds.map(value => { return { value, label: this.langs[value] } }), required: true, searchable: true, onSelect: value => { this.state.lang = value }, value: this.state.lang, }
            return out
        }
        async blockClient() { if (this.props.selectedConversation) { try { await this.props.selectedConversation.block() } catch (_e) { } } }
        async releaseClient() { if (this.props.selectedConversation?.isCurrent()) { await this.props.selectedConversation.release() } }
        async sendMessage(event) {
            const convId = this.props.selectedConversation?.id
            const outMessages = []
            let options = { from_me: true }, firstAttach
            let text = this.inputRef.el.value.trim()
            const attachments = [...this.state.attachments]
            const attachmentsSent = []
            let traduction = ''
            if (this.state.lang && this.env.canTranslate() && this.inputLangRef.el) { traduction = this.inputLangRef.el.value.trim() }
            if (event) {
                event.preventDefault()
                event.stopPropagation()
            }
            if ('' !== traduction) { options.traduction = traduction }
            if ('' != text) {
                options.ttype = 'text'
                options.text = text
            }
            if (attachments.length) {
                firstAttach = attachments.shift()
                options = this.setAttachmentValues2Message(options, firstAttach)
            }
            if (!options.ttype) {
                return outMessages
            }
            this.inputRef.el.disabled = true
            this.sendBtnRef.el.disabled = true
            if (this.inputLangRef.el) { this.inputLangRef.el.disabled = true }
            this.state.isSending = true
            try {
                options = this.sendMessageHook(options)
                outMessages.push(await this.props.selectedConversation.createMessage(options))
                await this.postCreateMessage(outMessages[outMessages.length - 1])
                if (options.res_model === 'ir.attachment') { attachmentsSent.push(options.res_model_obj) }
                text = traduction = ''
                for await (const attachment of attachments) {
                    options = this.setAttachmentValues2Message({ from_me: true }, attachment)
                    options = this.sendMessageHook(options)
                    outMessages.push(await this.props.selectedConversation.createMessage(options))
                    await this.postCreateMessage(outMessages[outMessages.length - 1])
                    attachmentsSent.push(attachment)
                }
                if (convId) {
                    this.clearDraftForConversation(convId)
                }
            } catch (e) {
                console.error(e)
                let errText = _t('Could not send the message.')
                const raw = e?.data?.message
                if (raw) {
                    errText = Array.isArray(raw) ? raw.join(' ') : raw
                } else if (e?.message) {
                    errText = e.message
                }
                this.env.services.notification.add(errText, { type: 'danger' })
            } finally {
                this.state.isSending = false
                this.inputRef.el.disabled = false
                this.sendBtnRef.el.disabled = false
                if (this.inputLangRef.el) { this.inputLangRef.el.disabled = false }
                this.state.attachments = [firstAttach, ...attachments].filter(attach => attach && !attachmentsSent.includes(attach))
                this.enableDisplabeAttachBtn()
                this.env.chatBus.trigger('setInputText', [text, traduction])
            }
            return outMessages
        }
        async postCreateMessage() { if (this.state.message) { this.env.chatBus.trigger('quoteMessage', null) } }
        setAttachmentValues2Message(options, attachment) {
            if (attachment.mimetype.includes('image')) { options.ttype = 'image' } else if (attachment.mimetype.includes('audio')) { options.ttype = 'audio' } else if (attachment.mimetype.includes('video')) { options.ttype = 'video' } else { options.ttype = 'file' }
            options.res_model = 'ir.attachment'
            options.res_id = attachment.id
            options.res_model_obj = attachment
            return options
        }
        onAddAttachment(attachment) { this.state.attachments = [...this.state.attachments, attachment] }
        async unlinkAttachment(attachment) {
            await this.attachmentUploader.unlink(attachment)
            this.state.attachments = this.state.attachments.filter(e => e.id !== attachment.id)
        }
        buildFormDataAttachment(formData) {
            formData.append('conversation_id', this.props.selectedConversation.id)
            formData.append('connector_type', this.props.selectedConversation.connectorType)
        }
        sendMessageHook(options) {
            if (this.state.message) { options.quote_id = this.state.message.exportToJson() }
            return options
        }
        onComposerKeydown(event) {
            if (event.key === 'Escape') {
                this.env.chatBus.trigger('quoteMessage', null)
                return
            }
            if (event.key !== 'Enter' || event.shiftKey) {
                return
            }
            const raw = (this.inputRef.el?.value || '').trim()
            if (raw.startsWith('/') && this.trySlashCommand(raw)) {
                event.preventDefault()
                event.stopPropagation()
                return
            }
            event.preventDefault()
            event.stopPropagation()
            if (!this.state.isSending) {
                this.sendMessage(event)
            }
        }
        trySlashCommand(raw) {
            const body = raw.startsWith('/') ? raw.slice(1).trim() : raw.trim()
            const cmd = body.split(/\s+/).filter(Boolean)[0]
            if (!cmd) {
                return false
            }
            const key = cmd.toLowerCase()
            const clearComposer = () => {
                const langVal = this.inputLangRef.el ? this.inputLangRef.el.value : ''
                this.env.chatBus.trigger('setInputText', [ '', langVal ])
            }
            const openSideTab = (tabKey) => {
                this.env.chatBus.trigger('selectTab', tabKey)
                this.env.chatBus.trigger('mobileNavigate', 'lastSide')
                clearComposer()
                return true
            }
            switch (key) {
                case 'help':
                case '?':
                    this.env.services.notification.add(
                        _t('Shortcuts: /partner /info /defaults /template /products /ai /panel /kanban'),
                        { type: 'info' },
                    )
                    clearComposer()
                    return true
                case 'p':
                case 'partner':
                    return openSideTab('tab_partner')
                case 'i':
                case 'info':
                    return openSideTab('tab_conv_info')
                case 'd':
                case 'defaults':
                case 'snippets':
                    return openSideTab('tab_default_answer')
                case 't':
                case 'template':
                    clearComposer()
                    if (!this.props.selectedConversation?.id) {
                        this.env.services.notification.add(_t('Select a conversation first.'), { type: 'warning' })
                        return true
                    }
                    void this.sendWizard()
                    return true
                case 'products':
                case 'cubes':
                    return openSideTab('tab_product_grid')
                case 'ai':
                    return openSideTab('tab_ai_inteface')
                case 'panel':
                case 'activities':
                    return openSideTab('tab_conv_panel')
                case 'kanban':
                case 'funnel':
                    return openSideTab('tab_conv_kanban')
                default:
                    return false
            }
        }
        onTranslateFieldKeydown(event) {
            if (event.key !== 'Enter' || event.shiftKey) {
                return
            }
            event.preventDefault()
            event.stopPropagation()
            this.onTranslate().then(() => this.inputRef.el?.focus())
        }
        resizeTextarea(textarea, maxPx) {
            if (textarea.value.trim()) {
                textarea.style.height = 'auto'
                const newHeight = textarea.scrollHeight - (textarea.offsetHeight - textarea.clientHeight)
                textarea.style.height = Math.min(newHeight, maxPx) + 'px'
                textarea.style.overflow = (newHeight > maxPx) ? 'auto' : 'hidden'
            } else {
                textarea.style.removeProperty('height')
                textarea.style.removeProperty('overflow')
            }
        }
        onComposerInput(event) {
            this.resizeTextarea(event.target, 132)
            this.scheduleDraftSave()
        }
        onInput(event) {
            this.resizeTextarea(event.target, 72)
        }
        async onPaste(event) {
            let clipboardData = event.clipboardData || window.clipboardData
            if (clipboardData) {
                const files = []
                for (const item of clipboardData.items) {
                    if (item.kind === 'file') {
                        event.stopPropagation()
                        event.preventDefault()
                        files.push(item.getAsFile())
                    }
                }
                return Promise.all(files.map(file => this.attachmentUploader.uploadFile(file))).catch(() => { })
            }
        }
        toggleEmojis() {
            if (this.popoverCloseFn) {
                this.popoverCloseFn()
                this.popoverCloseFn = null
            } else {
                this.popoverCloseFn = this.env.services.popover.add(this.emojisBtnRef.el, Emojis, {
                    onClick: this.addEmojis.bind(this), close: () => {
                        if (this.popoverCloseFn) {
                            this.popoverCloseFn()
                            this.popoverCloseFn = null
                        }
                    }
                }, { position: 'top' })
            }
        }
        addEmojis(event) {
            const emoji = event.target.dataset.source
            const startPos = this.inputRef.el.selectionStart; const endPos = this.inputRef.el.selectionEnd; const firstText = this.inputRef.el.value.substring(0, startPos)
            const lastText = this.inputRef.el.value.substring(endPos, this.inputRef.el.value.length)
            this.env.chatBus.trigger('setInputText', `${firstText}${emoji}${lastText}`)
            this.inputRef.el.focus()
            this.inputRef.el.selectionStart = startPos + emoji.length
            this.inputRef.el.selectionEnd = startPos + emoji.length
        }
        async updateSigning(newValue) {
            await this.updateUserPreference({ chatroom_signing_active: newValue })
            this.props.user.signingActive = newValue
        }
        async updateUserPreference(preference) { await this.env.services.orm.write('res.users', [this.env.services.user.userId], preference, { context: this.env.context }) }
        needDisableInput(attachment) {
            let out
            if (this.props.selectedConversation?.isOwnerFacebook()) { if (this.props.selectedConversation.isWabaExtern()) { out = attachment.mimetype.includes('audio') } else { out = true } } else { out = !(attachment.mimetype.includes('image') || attachment.mimetype.includes('video')) }
            return out
        }
        enableDisplabeAttachBtn() {
            if (this.state.attachments.length) {
                const attachment = this.state.attachments[0]
                if (this.needDisableInput(attachment)) {
                    this.env.chatBus.trigger('setInputText', '')
                    this.allInputs.filter(e => e.el).forEach(e => e.el.disabled = true)
                    this.sendBtnRef.el.focus()
                } else { this.allInputs.filter(e => e.el).forEach(e => e.el.disabled = false) }
                this.sendBtnRef.el.focus()
            } else {
                this.allInputs.filter(e => e.el).forEach(e => e.el.disabled = false)
                this.inputRef.el.focus()
            }
        }
        setInputText({ detail }) {
            const [text, traduction] = Array.isArray(detail) ? detail : [detail]
            if (!(this.inputRef.el.disabled || this.inputRef.el.readonly)) {
                this.inputRef.el.value = text
                this.onComposerInput({ target: this.inputRef.el })
                if (this.inputLangRef.el) {
                    this.inputLangRef.el.value = traduction || ''
                    this.onInput({ target: this.inputLangRef.el })
                }
                this.scheduleDraftSave()
            }
        }
        async setQuoteMessage({ detail: message }) {
            if (message) {
                const data = message.exportToJson()
                if (data.quote_id) { delete (data.quote_id) }
                if (data.metadata_type) { delete (data.metadata_type) }
                if (data.button_ids) { delete (data.button_ids) }
                const quote = new MessageModel(this.props.selectedConversation, data)
                await quote.buildExtraObj()
                this.state.message = quote
                this.inputRef.el.focus()
            } else { this.state.message = null }
        }
        async onTranslate() {
            const text = this.inputLangRef.el.value.trim()
            const traduction = await this.doTranslate(text)
            if (text && traduction) { this.env.chatBus.trigger('setInputText', [traduction, text]) }
        }
        async doTranslate(text) {
            let traduction = null
            if (text && this.state.lang && this.canTranslate) {
                const lang_id = this.state.lang
                const ai_config_id = this.env.canTranslate()
                const conversation_id = this.props.selectedConversation.id
                const { orm } = this.env.services
                traduction = await orm.call('acrux.chat.message', 'translate_text', [ai_config_id, text, lang_id, conversation_id], { context: this.env.context })
            }
            return traduction
        }
        async sendWizard() { await this.env.services.action.doAction(this.wizardAction, { additionalContext: { default_conversation_id: this.props.selectedConversation.id, full_name: true } }) }
        openTab(ev) {
            const target = ev.currentTarget || ev.target
            if (target) {
                const tabKey = target.getAttribute('tab-key')
                this.env.chatBus.trigger('selectTab', tabKey)
                this.env.chatBus.trigger('mobileNavigate', 'lastSide')
            }
        }
        async delegateConversation() {
            const { orm } = this.env.services
            await orm.call(this.env.chatModel, 'delegate_conversation', [[this.props.selectedConversation.id]], { context: this.context })
        }
        onToggleTraductor() {
            this.state.showTraductor = !this.state.showTraductor
            browser.localStorage.setItem('chatroomShowTraductor', `${this.state.showTraductor}`)
        }
    }
    Object.assign(Toolbox, { template: 'chatroom.Toolbox', props: { user: UserModel.prototype, selectedConversation: ConversationModel.prototype, defaultAnswers: { optional: true }, }, components: { CheckBox, Emojis, AttachmentList, FileUploader, ActivityButton, Transition, SelectMenu, Message, } })
    return __exports;
});;
