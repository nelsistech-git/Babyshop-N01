odoo.define('@whatsapp_connector/chatroom_mod/chat-search', ['@odoo/owl'], function (require) {
    'use strict'; let __exports = {}; const { Component, useRef } = require('@odoo/owl')
    const ChatSearch = __exports.ChatSearch = class ChatSearch extends Component {
        setup() {
            super.setup()
            this.env; this.props; this.inputSearch = useRef('inputSearch')
        }
        onKeypress(event) { if (event.which === 13) { this.env.chatBus.trigger(this.props.searchEvent, { search: this.inputSearch.el.value }) } }
        onSearch() { this.env.chatBus.trigger(this.props.searchEvent, { search: this.inputSearch.el.value }) }
        onClean() {
            this.inputSearch.el.value = ''
            this.env.chatBus.trigger(this.props.cleanEvent || this.props.searchEvent, { search: '' })
        }
    }
    Object.assign(ChatSearch, { template: 'chatroom.ChatSearch', props: { placeHolder: { type: String, optional: true }, cleanEvent: { type: String, optional: true }, searchEvent: String, slots: { type: Object, optional: true }, }, defaultProps: { placeHolder: '', } })
    return __exports;
});;
