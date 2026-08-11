/** Shared payload + routing for chatroom default replies (⚡ panel + snippet chips). */
odoo.define('@whatsapp_connector/chatroom_mod/default-answer-send', ['@web/core/l10n/translation'], function (require) {
    'use strict'
    let __exports = {}
    const { _t } = require('@web/core/l10n/translation')

    const MESSAGE_ONLY_SNIPPET_TYPES = new Set(['location', 'info', 'image', 'audio', 'video', 'file', 'sticker'])

    function stripBtnIds(buttons) {
        return (buttons || []).map((btn) => {
            const b = { ...btn }
            delete b.id
            return b
        })
    }

    function resolveFallbackText(answer) {
        if (answer.text != null && String(answer.text) !== '') {
            return answer.text
        }
        return answer.name
    }

    /**
     * @param {*} answer DefaultAnswerModel (owl model from get_for_chatroom)
     * @param {object} opts
     * @param {string|undefined|null} opts.codeResult resolved text when ttype === 'code' (already evaluated)
     */
    function buildSendOptions(answer, opts = {}) {
        const rawType = answer.ttype
        let ttype = rawType
        let text
        if (rawType === 'code') {
            ttype = 'text'
            text = (opts.codeResult === undefined || opts.codeResult === null) ? undefined : String(opts.codeResult)
        } else {
            text = resolveFallbackText(answer)
        }
        return {
            from_me: true,
            text,
            ttype,
            res_model: answer.resModel,
            res_id: answer.resId,
            button_ids: stripBtnIds(answer.buttons),
            chat_list_id: answer.chatListRecord,
        }
    }

    function snippetUsesCreateMessage(answer) {
        return MESSAGE_ONLY_SNIPPET_TYPES.has(answer?.ttype)
    }

    function snippetNeedsAttachment(answer) {
        return Boolean(answer?.ttype && ['image', 'audio', 'video', 'file', 'sticker'].includes(answer.ttype))
    }

    function getSnippetChipTitle(answer) {
        if (!answer) {
            return ''
        }
        const n = answer.name || ''
        if (answer.ttype === 'code') {
            return `${n} — ${_t('Dynamic (Python)')}`
        }
        if (snippetUsesCreateMessage(answer)) {
            const kind = ({ location: _t('Location'), info: _t('Notice'), image: _t('Image'), audio: _t('Audio'), video: _t('Video'), file: _t('File'), sticker: _t('Sticker') })[answer.ttype] || answer.ttype
            return `${n} (${kind}: ${_t('Send now')})`
        }
        if (answer.text) {
            const t = String(answer.text).replace(/\s+/g, ' ').trim()
            if (t.length > 220) {
                return `${t.slice(0, 217)}…`
            }
            return t
        }
        return n
    }

    __exports.stripBtnIds = stripBtnIds
    __exports.buildSendOptions = buildSendOptions
    __exports.snippetUsesCreateMessage = snippetUsesCreateMessage
    __exports.snippetNeedsAttachment = snippetNeedsAttachment
    __exports.resolveFallbackText = resolveFallbackText
    __exports.getSnippetChipTitle = getSnippetChipTitle
    __exports.MESSAGE_ONLY_SNIPPET_TYPES = MESSAGE_ONLY_SNIPPET_TYPES

    __exports[Symbol.for('default')] = __exports
    return __exports
})
