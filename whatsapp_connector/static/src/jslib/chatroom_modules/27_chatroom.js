odoo.define('@whatsapp_connector/chatroom_mod/chatroom', ['@web/core/l10n/translation', '@web/core/utils/draggable', '@web/core/errors/error_dialogs', '@web/core/ui/ui_service', '@web/core/utils/urls', '@web/core/browser/browser', '@odoo/owl', '@web/core/utils/hooks', '@whatsapp_connector/chatroom_mod/chatroom-header', '@whatsapp_connector/chatroom_mod/conversation-list', '@whatsapp_connector/chatroom_mod/conversation', '@whatsapp_connector/chatroom_mod/conversation-header', '@whatsapp_connector/chatroom_mod/conversation-thread', '@whatsapp_connector/chatroom_mod/tabs-container', '@whatsapp_connector/chatroom_mod/toolbox', '@whatsapp_connector/chatroom_mod/conversation-name', '@whatsapp_connector/chatroom_mod/conversation-model', '@whatsapp_connector/chatroom_mod/default-answer-model', '@whatsapp_connector/chatroom_mod/user-model'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation')
    const { useDraggable } = require('@web/core/utils/draggable')
    const { WarningDialog } = require('@web/core/errors/error_dialogs')
    const { SIZES } = require('@web/core/ui/ui_service')
    const { url } = require('@web/core/utils/urls')
    const { browser } = require('@web/core/browser/browser')
    const { Component, EventBus, useSubEnv, useState, onWillStart, useRef, onMounted, onWillUnmount } = require('@odoo/owl')
    const { useBus } = require('@web/core/utils/hooks')
    const { ChatroomHeader } = require('@whatsapp_connector/chatroom_mod/chatroom-header')
    const { ConversationList } = require('@whatsapp_connector/chatroom_mod/conversation-list')
    const { Conversation } = require('@whatsapp_connector/chatroom_mod/conversation')
    const { ConversationHeader } = require('@whatsapp_connector/chatroom_mod/conversation-header')
    const { ConversationThread } = require('@whatsapp_connector/chatroom_mod/conversation-thread')
    const { TabsContainer } = require('@whatsapp_connector/chatroom_mod/tabs-container')
    const { Toolbox } = require('@whatsapp_connector/chatroom_mod/toolbox')
    const { ConversationName } = require('@whatsapp_connector/chatroom_mod/conversation-name')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const { DefaultAnswerModel } = require('@whatsapp_connector/chatroom_mod/default-answer-model')
    const { UserModel } = require('@whatsapp_connector/chatroom_mod/user-model')
    const Chatroom = __exports.Chatroom = class Chatroom extends Component {
        setup() {
            super.setup()
            this.env; this.state = useState(this.getInitState())
            this.currencyId = null
            this.defaultAnswers = []
            this.canPlay = typeof (Audio) !== 'undefined'
            this.audio = null
            this.myController = null
            this.chatroomRef = useRef('chatroomRef')
            this.firstSideRef = useRef('firstSideRef')
            this.middleSideRef = useRef('middleSideRef')
            this.showUserInMessage = false
            this.canTranscribe = false
            this.canTranslate = false
            this.currentLang = false
            this.iAmAdmin = false
            this.chatroomTabSize = this.state.chatroomTabSize
            useSubEnv(this.getSubEnv())
            this.productDragAndDrop()
            useBus(this.env.chatBus, 'selectConversation', this.selectConversation.bind(this))
            useBus(this.env.chatBus, 'deleteConversation', this.deleteConversation.bind(this))
            useBus(this.env.chatBus, 'mobileNavigate', this.mobileNavigate.bind(this))
            useBus(this.env.chatBus, 'selectTab', this.updateTab.bind(this))
            useBus(this.env.chatBus, 'chatUiRefresh', () => this.bumpUiTick('chatUiRefresh'))
            useBus(this.env.services.bus_service, 'notification', this.onNotification.bind(this))
            useBus(this.env.services.ui.bus, 'resize', this.resize.bind(this))
            useBus(document, 'visibilitychange', this.visibilityChange)
            onWillStart(this.willStart.bind(this))
            const updateMyController = () => {
                this.myController = this.env.services.action.currentController
                this.state.renderForms = true
                this.env.bus.removeEventListener('ACTION_MANAGER:UI-UPDATED', updateMyController)
            }
            this.env.bus.addEventListener('ACTION_MANAGER:UI-UPDATED', updateMyController)
            this._uiTickInterval = null
            onMounted(() => {
                browser.setTimeout(() => this.bumpUiTick('delayed_boot_2s'), 2000)
                this._uiTickInterval = browser.setInterval(() => this.bumpUiTick('interval_30s'), 30 * 1000)
            })
            onWillUnmount(() => {
                if (this._uiTickInterval) {
                    browser.clearInterval(this._uiTickInterval)
                }
            })
        }
        bumpUiTick(reason = 'unknown') {
            const prev = this.state.uiTick
            this.state.uiTick++
            console.log('[acrux-chatroom] uiTick bump', { reason, prev, next: this.state.uiTick, selectedConvId: this.state.selectedConversation?.id ?? null, convListLen: this.state.conversations?.length ?? 0, })
        }
        getInitState() {
            const chatroomTabSize = parseInt(browser.localStorage.getItem('chatroomTabSize') || '0')
            let focusMode = 0
            const fmStored = browser.localStorage.getItem('chatroomFocusMode')
            if (fmStored !== null && fmStored !== '') {
                const n = parseInt(fmStored, 10)
                if (!Number.isNaN(n) && n >= 0 && n <= 2) {
                    focusMode = n
                }
            } else if (browser.localStorage.getItem('chatroomFocusChatOnly') === '1') {
                focusMode = 1
            }
            return { user: new UserModel(this), selectedConversation: null, conversations: [], currentMobileSide: '', renderForms: false, chatroomTabSize, tabSelected: this.props.tabSelected || 'tab_default_answer', focusMode, uiTick: 0, }
        }
        getSubEnv() { return { context: this.props.action.context, chatBus: new EventBus(), chatModel: 'acrux.chat.conversation', getCurrency: () => this.currencyId, chatroomJsId: this.props.action.jsId, getShowUser: () => this.showUserInMessage, canTranscribe: () => this.canTranscribe, canTranslate: () => this.canTranslate, getCurrentLang: () => this.currentLang, isVerticalView: () => this.state.user?.tabOrientation === 'vertical', isAdmin: () => this.isAdmin, } }
        async willStart() {
            this.currencyId = await this.getCurrency()
            this.defaultAnswers = await this.getDefaultAnswers()
            this.conversationUsedFields = await this.getConversationUsedFields()
            this.conversationInfoForm = await this.getConversationInfoView()
            this.conversationKanban = await this.getConversationKanbanView()
            this.aiIntefaceForm = await this.getAiIntefaceView()
            this.state.user.updateFromJson(await this.getUserPreference())
            this.showUserInMessage = await this.env.services.user.hasGroup('whatsapp_connector.group_chat_show_user_in_message')
            this.isAdmin = await this.env.services.user.hasGroup('whatsapp_connector.group_chatroom_admin')
            this.canTranscribe = await this.getTranscriptionModel()
            this.canTranslate = await this.getTranslationModel()
            await this.setServerConversation()
            if (this.canPlay) {
                this.audio = new Audio()
                if (this.audio.canPlayType('audio/ogg; codecs=vorbis')) { this.audio.src = url('/mail/static/src/audio/ting.ogg') } else { this.audio.src = url('/mail/static/src/audio/ting.mp3') }
            }
            if (this.props.selectedConversationId) {
                const conv = this.state.conversations.find(conv => conv.id === this.props.selectedConversationId)
                if (conv) { this.selectConversation({ detail: { conv } }) } else { this.selectConversation({ detail: { conv: null } }) }
            } else { this.selectConversation({ detail: { conv: null } }) }
        }
        async setServerConversation() {
            const { orm } = this.env.services
            const data = await orm.call(this.env.chatModel, 'search_active_conversation', [], { context: this.env.context })
            await this.upsertConversation(data)
            return this.state.conversations
        }
        async getCurrency() {
            const { orm } = this.env.services
            const currency = await orm.read('res.company', [this.env.services.company.currentCompany.id], ['currency_id'], { context: this.env.context })
            return currency[0].currency_id[0]
        }
        async getDefaultAnswers() {
            const { orm } = this.env.services
            const data = await orm.call('acrux.chat.default.answer', 'get_for_chatroom', [], { context: this.env.context })
            return data.map(answer => new DefaultAnswerModel(this, answer))
        }
        async getConversationInfoView() {
            const { orm } = this.env.services
            const data = await orm.call(this.env.chatModel, 'check_object_reference', ['', 'view_whatsapp_connector_conversation_chatroom_form'], { context: this.context })
            return data[1]
        }
        async getConversationKanbanView() {
            const { orm } = this.env.services
            const data = await orm.call(this.env.chatModel, 'check_object_reference', ['', 'view_whatsapp_connector_conversation_kanban'], { context: this.context })
            return data[1]
        }
        async getAiIntefaceView() {
            const { orm } = this.env.services
            const data = await orm.call(this.env.chatModel, 'check_object_reference', ['', 'view_whatsapp_connector_ai_interface_form'], { context: this.context })
            return data[1]
        }
        async getTranscriptionModel() {
            const { orm } = this.env.services
            const data = await orm.searchRead('acrux.chat.ai.config', [['operation_key', '=', 'audio_transcriptions']], ['name'], { context: this.context, limit: 1 })
            return data.length ? data[0].id : 0
        }
        async getTranslationModel() {
            let out = 0
            const { orm } = this.env.services
            const transalateRef = await orm.call(this.env.chatModel, 'check_object_reference', ['', 'data_ai_translate'], { context: this.context })
            if (transalateRef?.length && transalateRef[1]) {
                const translateModel = await orm.read('acrux.chat.ai.config', [transalateRef[1]], ['name', 'active'], { context: this.context })
                if (translateModel?.length) { if (translateModel[0].active) { out = translateModel[0].id } }
            }
            return out
        }
        async getConversationUsedFields() {
            const { orm } = this.env.services
            const data = await orm.call(this.env.chatModel, 'get_fields_to_read', [], { context: this.env.context })
            return data
        }
        get userPreferenceFild() { return ['id', 'chatroom_signing_active', 'acrux_chat_active'] }
        async getUserPreference() {
            const data = await this.env.services.orm.read('res.users', [this.env.services.user.userId], this.userPreferenceFild, { context: this.env.context })
            const params = await this.env.services.orm.call(this.env.chatModel, 'get_config_parameters', [], { context: this.env.context })
            Object.assign(data[0], params)
            return data[0]
        }
        async upsertConversation(convList) {
            const conversations = [...this.state.conversations]
            const out = []
            let replaceSelectedConversation = false
            if (convList) {
                if (!Array.isArray(convList)) { convList = [convList] }
                for (const convData of convList) {
                    let conv = conversations.find(conv => conv.id === convData.id)
                    if (conv) {
                        if (this.state.selectedConversation?.id === convData.id) { replaceSelectedConversation = true }
                        conv.updateFromJson(convData)
                        await conv.buildExtraObj()
                    } else {
                        conv = new ConversationModel(this, convData)
                        await conv.buildExtraObj()
                        conversations.push(conv)
                    }
                    out.push(conv)
                }
            }
            this.state.conversations = conversations.filter(conv => this.canHaveThisConversation(conv))
            if (replaceSelectedConversation) { this.replaceSelectedConversation() }
            console.log('[acrux-chatroom] upsertConversation -> conversationsReorder', { updatedIds: out.map(c => c.id), filteredCount: this.state.conversations.length, })
            this.env.chatBus.trigger('conversationsReorder')
            return out.filter(item => this.state.conversations.includes(item))
        }
        replaceSelectedConversation() {
            const index = this.state.conversations.findIndex(conv => conv.id === this.state.selectedConversation?.id)
            let conv = null
            if (index >= 0) {
                conv = new ConversationModel(this, {})
                conv.copyFromObj(this.state.selectedConversation)
                this.state.conversations = [...this.state.conversations.slice(0, index), conv, ...this.state.conversations.slice(index + 1)]
            }
            this.env.chatBus.trigger('selectConversation', { conv })
        }
        canHaveThisConversation(conversation) {
            let out = true
            if (this.isAdmin) { out = conversation.status !== 'done' } else { out = conversation.status === 'new' || conversation.isCurrent() }
            return out
        }
        async selectConversation({ detail: { conv } }) {
            this.state.selectedConversation = conv
            if (this.myController) { this.myController.props.selectedConversationId = conv ? conv.id : undefined }
            if (conv) {
                await conv.selected()
                this.env.chatBus.trigger('mobileNavigate', 'middleSide')
            }
            this.bumpUiTick('selectConversation')
        }
        async onNotification({ detail: notifications }) {
            if (notifications) {
                const types = [...new Set(notifications.map(n => n.type).filter(Boolean))]
                console.log('[acrux-chatroom] bus notification batch', { count: notifications.length, types, })
                const proms = notifications.map(d => this.notifactionProcessor(d))
                await Promise.all(proms)
                this.bumpUiTick('notifications_processed')
            }
        }
        async notifactionProcessor(data) {
            const proms = []
            if (data.type === 'new_messages' && this.state.user.status) { proms.push(...data.payload.map(m => this.onNewMessage(m))) }
            if (data.type === 'init_conversation' && this.state.user.status) { proms.push(...data.payload.map(m => this.onInitConversation(m))) }
            if (data.type === 'change_status') { proms.push(...data.payload.map(m => this.onChangeStatus(m))) }
            if (data.type === 'update_conversation' && this.state.user.status) { proms.push(...data.payload.map(m => this.onUpdateConversation(m))) }
            if (data.type === 'error_messages' && this.state.user.status) { proms.push(...data.payload.map(m => this.onErrorMessages(m))) }
            await Promise.all(proms)
        }
        async onNewMessage(convData) {
            const { desk_notify, messages } = convData
            const someMessageNew = messages.some(msg => !msg.from_me)
            let conv = null
            const res = await this.upsertConversation(convData)
            if (res.length > 0) {
                conv = res[0]
                if (document.hidden) {
                    if ('all' && desk_notify || ('mines' === desk_notify && conv.agent.id === this.env.services.user.userId)) {
                        if (someMessageNew) {
                            const msg = _t('New messages from ') + conv.name
                            this.env.services.notification.add(msg, { type: 'info' })
                            await this.playNotification()
                        }
                    }
                } else { if (someMessageNew && this.state.selectedConversation?.id === conv.id && conv.isCurrent()) { await conv.messageSeen() } }
            }
            return conv
        }
        async onUpdateConversation(convData) {
            await this.upsertConversation(convData)
            return this.state.conversations.find(x => x.id === convData.id)
        }
        async onInitConversation(convData) {
            await this.upsertConversation(convData)
            const conv = this.state.conversations.find(x => x.id === convData.id)
            if (conv) { this.env.chatBus.trigger('selectConversation', { conv }) }
            return conv
        }
        async onChangeStatus(data) {
            if (data.agent_id[0] === this.env.services.user.userId) {
                if (this.state.user.status !== data.status) {
                    this.state.user.status = data.status
                    this.changeStatusView(data)
                }
                if (this.state.user.signingActive !== data.signing_active) { this.state.user.signingActive = data.signing_active }
            }
        }
        async onErrorMessages(convData) {
            const conv = this.state.conversations.find(x => x.id === convData.id)
            if (conv) {
                conv.updateFromJson(convData)
                await conv.buildExtraObj()
                console.log('[acrux-chatroom] onErrorMessages -> conversationsReorder', { convId: conv.id, })
                this.env.chatBus.trigger('conversationsReorder')
                const messageIds = convData.messages.map(msg => msg.id)
                const message = conv.messages.find(msg => messageIds.includes(msg.id))
                this.env.services.dialog.add(WarningDialog, { message: _t('Error in conversation with ') + conv.name }, {
                    onClose: async () => {
                        if (this.state.selectedConversation === conv) { if (message) { this.env.chatBus.trigger('inmediateScrollToMessage', { message }) } } else {
                            if (message) { this.env.chatBus.trigger('scrollToMessage', { message }) }
                            this.env.chatBus.trigger('selectConversation', { conv })
                        }
                    }
                })
            }
        }
        async deleteConversation({ detail: { id } }) {
            const conv = this.state.conversations.find(x => x.id === id)
            this.state.conversations = this.state.conversations.filter(x => x.id !== id)
            if (conv) {
                if (conv === this.state.selectedConversation) {
                    this.env.chatBus.trigger('selectConversation', { conv: null })
                    this.env.chatBus.trigger('mobileNavigate', 'firstSide')
                }
            }
            return Promise.resolve(conv)
        }
        productDragAndDrop() {
            useDraggable({
                enable: true, ref: this.chatroomRef, elements: '.acrux_Product', cursor: 'grabbing', onDragStart: () => this.env.chatBus.trigger('productDragInit'), onDragEnd: () => this.env.chatBus.trigger('productDragEnd'), onDrag: ({ x, y }) => this.env.chatBus.trigger('productDragging', { x, y }), onDrop: ({ x, y, element }) => {
                    const product = { id: element.dataset.id, name: element.dataset.name }
                    this.env.chatBus.trigger('productDrop', { x, y, product })
                },
            })
        }
        visibilityChange() {
            if (!document.hidden && this.state.selectedConversation && this.state.selectedConversation.isCurrent()) {
                this.state.selectedConversation.messageSeen()
            }
            if (!document.hidden) {
                this.bumpUiTick('visibility_visible')
            } else {
                console.log('[acrux-chatroom] visibility hidden (no uiTick)')
            }
        }
        mobileNavigate({ detail: target }) { if (this.env.services.ui.size <= SIZES.MD) { this.state.currentMobileSide = target } }
        get firtSideMobile() {
            let out = ''
            if (this.env.services.ui.size <= SIZES.MD) {
                const { currentMobileSide } = this.state
                if (currentMobileSide === 'firstSide') { } else if (currentMobileSide === 'middleSide') { if (this.env.services.ui.size < SIZES.MD) { out = 'd-none' } } else if (currentMobileSide === 'lastSide') { out = 'd-none' }
            }
            return out
        }
        get middleSideMobile() {
            let out = ''
            if (this.env.services.ui.size <= SIZES.MD) {
                const { currentMobileSide } = this.state
                if (currentMobileSide === 'firstSide') { if (this.env.services.ui.size < SIZES.MD) { out = 'd-none' } } else if (currentMobileSide === 'middleSide') { } else if (currentMobileSide === 'lastSide') { out = 'd-none' }
            }
            return out
        }
        get lastSideMobile() {
            let out = ''
            if (this.env.services.ui.size <= SIZES.MD) {
                const { currentMobileSide } = this.state
                if (currentMobileSide === 'firstSide') { out = 'd-none' } else if (currentMobileSide === 'middleSide') { out = 'd-none' } else if (currentMobileSide === 'lastSide') { out = 'col-12' }
            }
            return out
        }
        resize() {
            this.state.currentMobileSide = ''
            this.chatroomTabSize = this.state.chatroomTabSize
        }
        async playNotification() { if (this.canPlay) { try { await this.audio.play() } catch { } } }
        updateTab({ detail: tabId }) {
            if (this.myController) { this.myController.props.tabSelected = tabId }
            this.state.tabSelected = tabId
        }
        get leftColumnClasses() {
            let out = 'o_sidebar o_sidebar_left col-12 col-md-4 col-lg-3 col-xl-3 col-xxl-3'
            if (this.state.focusMode === 2 && this.env.services.ui.size >= SIZES.LG) {
                out += ' d-none'
            }
            if (this.state.currentMobileSide && this.firtSideMobile) {
                out += ` ${this.firtSideMobile}`
            }
            return out
        }
        get middleColumnClasses() {
            const ui = this.env.services.ui.size
            const base = 'o_sidebar o_sidebar_content col-12 col-md-8'
            const lg = ui >= SIZES.LG
            const fm = this.state.focusMode
            if (!lg) {
                const t = this.chatroomTabSize
                return `${base} col-lg-${4 + t} col-xl-${4 + t} col-xxl-${5 + t}`
            }
            if (fm === 2) {
                return `${base} col-lg-12 col-xl-12 col-xxl-12`
            }
            if (fm === 1) {
                return `${base} col-lg-9 col-xl-9 col-xxl-9`
            }
            const t = this.chatroomTabSize
            return `${base} col-lg-${4 + t} col-xl-${4 + t} col-xxl-${5 + t}`
        }
        get rightColumnClasses() {
            const ui = this.env.services.ui.size
            const base = 'o_sidebar o_sidebar_right'
            if (ui >= SIZES.LG && this.state.focusMode >= 1) {
                return `${base} d-none`
            }
            const t = this.chatroomTabSize
            return `${base} col-lg-${5 - t} col-xl-${5 - t} col-xxl-${4 - t}`
        }
        cycleFocusChat() {
            this.state.focusMode = (this.state.focusMode + 1) % 3
            browser.localStorage.setItem('chatroomFocusMode', String(this.state.focusMode))
        }
        get focusToggleTitle() {
            switch (this.state.focusMode) {
                case 0:
                    return _t('Hide side panel (wider chat)')
                case 1:
                    return _t('Hide conversation list (full width)')
                default:
                    return _t('Restore normal layout')
            }
        }
        get focusToggleIcon() {
            switch (this.state.focusMode) {
                case 0:
                    return 'fa-expand'
                case 1:
                    return 'fa-columns'
                default:
                    return 'fa-compress'
            }
        }
        changeTabSize(event) {
            const target = event.currentTarget || event.target
            const reducing = target.className.includes('left')
            const size = this.state.chatroomTabSize + (reducing ? -2 : 2)
            this.chatroomTabSize = size
        }
        set chatroomTabSize(size) {
            size = Math.max(-2, size)
            size = Math.min(2, size)
            browser.localStorage.setItem('chatroomTabSize', size)
            this.state.chatroomTabSize = size
        }
        get chatroomTabSize() { return this.state.chatroomTabSize }
    }
    Object.assign(Chatroom, { props: { action: Object, actionId: { type: Number, optional: true }, className: String, globalState: { type: Object, optional: true }, selectedConversationId: { type: Number, optional: true }, tabSelected: { type: String, optional: true } }, components: { ChatroomHeader, Conversation, ConversationHeader, ConversationThread, TabsContainer, Toolbox, ConversationName, ConversationList, }, template: 'chatroom.Chatroom', })
    return __exports;
});;
