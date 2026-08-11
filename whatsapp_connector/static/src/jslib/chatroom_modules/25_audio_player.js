odoo.define('@whatsapp_connector/chatroom_mod/audio-player', ['@odoo/owl'], function (require) {
    'use strict'; let __exports = {}; const { Component, useState, useRef } = require('@odoo/owl')
    const AudioPlayer = __exports.AudioPlayer = class AudioPlayer extends Component {
        setup() {
            super.setup()
            this.state = useState({ time: '', show: false, error: null, paused: true })
            this.audioRef = useRef('audioRef')
            this.playbackRef = useRef('playbackRef')
            this.progressRef = useRef('progressRef')
            this.ignoreTimeUpdateEvent = false
        }
        onLoadData(event) {
            const audio = event.target
            this.state.time = this.calculateTime(this.props.duration || audio.duration)
            this.state.show = true
        }
        onError() {
            this.state.error = true
            this.state.show = true
        }
        onTimeUpdate(event) {
            const audio = event.target
            let percentage = audio.currentTime * 100.00 / (this.props.duration || audio.duration)
            percentage = Math.round(percentage)
            this.playbackRef.el.style.width = `${percentage}%`
            if (!this.ignoreTimeUpdateEvent) { this.state.time = this.calculateTime(audio.currentTime) }
        }
        onEnded(event) {
            this.ignoreTimeUpdateEvent = true
            const audio = event.target
            audio.currentTime = 0
            this.state.paused = true
            this.state.time = this.calculateTime(this.props.duration || audio.duration)
        }
        onPlayPause(event) {
            event.preventDefault(); this.ignoreTimeUpdateEvent = false
            if (this.state.paused) { this.audioRef.el.play() } else { this.audioRef.el.pause() }
            this.state.paused = !this.state.paused
        }
        changeProgress(event) {
            this.ignoreTimeUpdateEvent = false
            let relative_position, percentage
            const position = this.progressRef.el.getBoundingClientRect()
            relative_position = event.pageX - position.left
            percentage = relative_position / position.width
            if (Number.isFinite(this.props.duration || this.audioRef.el.duration)) { this.audioRef.el.currentTime = (this.props.duration || this.audioRef.el.duration) * percentage }
        }
        calculateTime(num) {
            let out = ''
            if (!isNaN(num) && Number.isFinite(num)) {
                let zero = (x) => x < 10 ? '0' + x : x; let minutes = Math.floor(num / 60.0); let seconds = Math.round(num) % 60; let hours = Math.floor(minutes / 60.0); minutes = Math.round(minutes) % 60; if (hours) { out = zero(hours) + ":"; }
                out += zero(minutes) + ":" + zero(seconds);
            }
            return out;
        }
        onDownload() {
            if (this.props.audio.src) {
                const link = document.createElement('a')
                if (this.props.audio.src.startsWith('blob:')) {
                    link.href = this.props.audio.src
                    link.download = 'audio.oga'
                } else {
                    if (this.props.audio.src.startsWith('/web/content/')) {
                        const split = this.props.audio.src.split('/')
                        const attachId = split[split.length - 1]
                        link.href = `/web/content/ir.attachment/${attachId}/datas?download=true`
                    } else { link.href = this.props.audio.src }
                    link.download = ''
                }
                link.click()
            }
        }
    }
    Object.assign(AudioPlayer, { template: 'chatroom.AudioPlayer', props: { audio: Object, duration: { type: Number, optional: true, } }, })
    return __exports;
});;
