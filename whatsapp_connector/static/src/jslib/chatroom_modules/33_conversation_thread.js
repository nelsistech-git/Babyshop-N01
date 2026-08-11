odoo.define('@whatsapp_connector/chatroom_mod/conversation-thread', ['@web/core/l10n/translation', '@odoo/owl', '@web/core/utils/hooks', '@web/core/browser/browser', '@whatsapp_connector/chatroom_mod/story-dialog', '@whatsapp_connector/chatroom_mod/conversation-model'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation')
    const { Component, useRef, onWillUpdateProps, onPatched, onMounted } = require('@odoo/owl')
    const { useBus } = require('@web/core/utils/hooks')
    const { browser } = require('@web/core/browser/browser')
    const { Message } = require('@whatsapp_connector/chatroom_mod/story-dialog')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const ConversationThread = __exports.ConversationThread = class ConversationThread extends Component {
        setup() {
            super.setup()
            this.env; this.props; this.threadRef = useRef('threadRef')
            useBus(this.env.chatBus, 'productDragInit', this.productDragInit.bind(this))
            useBus(this.env.chatBus, 'productDragging', this.productDragging.bind(this))
            useBus(this.env.chatBus, 'productDragEnd', this.productDragEnd.bind(this))
            useBus(this.env.chatBus, 'productDrop', this.productDrop.bind(this))
            useBus(this.env.chatBus, 'scrollToMessage', this.setMessageToScroll.bind(this))
            useBus(this.env.chatBus, 'inmediateScrollToMessage', this.scrollToMessage.bind(this))
            this.firstScroll = true
            this.loadMoreMessage = false
            this.scrollToPrevMessage = null
            this.messageToScroll = null
            onWillUpdateProps((nextProps) => {
                if (nextProps.uiTick !== this.props.uiTick) {
                    console.log('[acrux-chatroom] ConversationThread uiTick (relative time refresh)', { prev: this.props.uiTick, next: nextProps.uiTick, convId: this.props.selectedConversation?.id ?? null, messageCount: this.props.selectedConversation?.messages?.length ?? 0, })
                }
                this.willUpdateProps()
            })
            onMounted(this.checkScroll.bind(this))
            onPatched(this.checkScroll.bind(this))
        }
        get emptyThreadHint() { return _t('No messages yet. Send one below.') }
        async willUpdateProps() {
            this.loadMoreMessage = false
            this.firstScroll = true
            this.scrollToPrevMessage = null
        }
        checkScroll() {
            if (this.props.selectedConversation) {
                if (this.messageToScroll) {
                    this.scrollToMessage({ message: this.messageToScroll })
                    this.messageToScroll = null
                } else if (this.scrollToPrevMessage) {
                    this.scrollToPrevMessage()
                    this.scrollToPrevMessage = null
                } else {
                    if (this.needScroll() || this.firstScroll) {
                        this.scrollConversation()
                        this.firstScroll = false
                    }
                }
                this.loadMoreMessage = true
            }
        }
        isInside(x, y) {
            let out
            const rect = this.threadRef.el.getBoundingClientRect()
            if (rect.top <= y && y <= rect.bottom) { out = rect.left <= x && x <= rect.right } else { out = false }
            return out
        }
        needScroll() {
            const scollPosition = this.calculateScrollPosition()
            return scollPosition >= 0.7
        }
        calculateScrollPosition() {
            let scrollPosition = 0
            if (this.threadRef.el) {
                const scrollTop = this.threadRef.el.scrollTop
                const scrollHeight = this.threadRef.el.scrollHeight
                const clientHeight = this.threadRef.el.clientHeight
                scrollPosition = (scrollTop + clientHeight) / scrollHeight
            }
            return scrollPosition
        }
        scrollConversation() {
            if (!this.threadRef.el) {
                return
            }
            const el = this.threadRef.el
            browser.setTimeout(() => {
                el.scrollTop = el.scrollHeight
            }, 0)
        }
        scrollToMessage({ detail: { message, effect, className } }) {
            if (this.threadRef.el) {
                const element = document.querySelector(`.acrux_Message[data-id="${message.id}"]`)
                if (element) {
                    element.scrollIntoView({ block: 'nearest', inline: 'start' })
                    if (effect === 'blink' && className) {
                        setTimeout(() => element.classList.add('active_quote'), 400)
                        setTimeout(() => element.classList.remove('active_quote'), 800)
                        setTimeout(() => element.classList.add('active_quote'), 1200)
                        setTimeout(() => element.classList.remove('active_quote'), 1600)
                    }
                }
            }
        }
        async syncMoreMessage() {
            if (this.props.selectedConversation && this.loadMoreMessage && this.threadRef.el && this.threadRef.el.scrollTop === 0) {
                const message = this.threadRef.el.querySelector('.acrux_Message')
                const size = this.props.selectedConversation.messages.length
                await this.props.selectedConversation.syncMoreMessage()
                if (message && this.props.selectedConversation.messages.length > size) { this.scrollToPrevMessage = () => message.scrollIntoView() }
            }
        }
        productDragInit() { this.threadRef.el.classList.add('drop-active') }
        productDragging({ detail: { x, y } }) { if (this.isInside(x, y)) { this.threadRef.el.classList.add('drop-hover') } else { this.threadRef.el.classList.remove('drop-hover') } }
        productDragEnd() {
            this.threadRef.el.classList.remove('drop-active')
            this.threadRef.el.classList.remove('drop-hover')
        }
        async productDrop({ detail: { x, y, product } }) { if (this.isInside(x, y) && this.props.selectedConversation?.isCurrent()) { await this.props.selectedConversation.sendProduct(product.id) } }
        setMessageToScroll({ detail: { message } }) { this.messageToScroll = message }
    }
    Object.assign(ConversationThread, { template: 'chatroom.ConversationThread', props: { selectedConversation: ConversationModel.prototype, uiTick: { type: Number, optional: true }, }, defaultProps: { uiTick: 0 }, components: { Message } })
    return __exports;
});
