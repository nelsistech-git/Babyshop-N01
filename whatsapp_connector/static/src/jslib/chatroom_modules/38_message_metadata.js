odoo.define('@whatsapp_connector/chatroom_mod/message-metadata', ['@odoo/owl', '@whatsapp_connector/chatroom_mod/audio-player'], function (require) {
    'use strict'; let __exports = {}; const { Component, onWillUpdateProps, onWillStart } = require('@odoo/owl')
    const { AudioPlayer } = require('@whatsapp_connector/chatroom_mod/audio-player')
    const MessageMetadata = __exports.MessageMetadata = class MessageMetadata extends Component {
        setup() {
            super.setup()
            this.env; this.props; this.data = {}
            onWillStart(this.willStart.bind(this))
            onWillUpdateProps(this.willUpdateProps.bind(this))
        }
        async willStart() { this.computeProps(this.props) }
        async willUpdateProps(nextProps) { this.computeProps(nextProps) }
        computeProps(props) {
            const data = JSON.parse(props.metadataJson)
            data.title = data.title || ''
            data.body = data.body || ''
            this.data = data
        }
        openExternalLink() { if (this.data.url) { window.open(this.data.url, '_blank') } }
        get audioObj() { return { src: this.data?.media?.url } }
        get urlPreview() { return this.data?.media?.url }
        get extraClass() { return '' }
    }
    Object.assign(MessageMetadata, { template: 'chatroom.MessageMetadata', props: { type: String, metadataJson: String, }, components: { AudioPlayer } })
    return __exports;
});;
