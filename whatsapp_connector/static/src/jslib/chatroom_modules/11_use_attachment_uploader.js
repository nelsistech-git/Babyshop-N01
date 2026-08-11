odoo.define('@whatsapp_connector/chatroom_mod/use-attachment-uploader', ['@odoo/owl', '@web/core/l10n/translation', '@web/core/utils/concurrency', '@web/core/utils/hooks', '@mail/utils/common/misc', '@whatsapp_connector/chatroom_mod/attachment'], function (require) {
    'use strict'; let __exports = {}; const { useState } = require('@odoo/owl')
    const { _t } = require('@web/core/l10n/translation')
    const { Deferred } = require('@web/core/utils/concurrency')
    const { useBus, useService } = require('@web/core/utils/hooks')
    const { assignDefined } = require('@mail/utils/common/misc')
    const { Attachment } = require('@whatsapp_connector/chatroom_mod/attachment')
    function dataUrlToBlob(data, type) {
        const binData = window.atob(data)
        const uiArr = new Uint8Array(binData.length)
        uiArr.forEach((_, index) => (uiArr[index] = binData.charCodeAt(index)))
        return new Blob([uiArr], { type })
    }
    let nextId = -1
    function getNextId() {
        const tmpId = nextId--
        return `chatroom${tmpId}`
    }
    __exports.useAttachmentUploader = useAttachmentUploader; function useAttachmentUploader({ onFileUploaded, buildFormData }) {
        const { bus, upload } = useService('file_upload')
        const notificationService = useService('notification')
        const rpc = useService('rpc')
        const ui = useService('ui')
        const abortByAttachmentId = new Map()
        const deferredByAttachmentId = new Map()
        const uploadingAttachmentIds = new Set()
        const state = useState({
            uploadData({ data, name, type }) {
                const file = new File([dataUrlToBlob(data, type)], name, { type })
                return this.uploadFile(file)
            }, async uploadFile(file) {
                const tmpId = getNextId()
                uploadingAttachmentIds.add(tmpId)
                await upload('/web/binary/upload_attachment_chat', [file], {
                    buildFormData(formData) {
                        buildFormData?.(formData)
                        formData.append('is_pending', false)
                        formData.append('temporary_id', tmpId)
                    },
                }).catch((e) => { if (e.name !== 'AbortError') { throw e } }); const uploadDoneDeferred = new Deferred()
                deferredByAttachmentId.set(tmpId, uploadDoneDeferred)
                return uploadDoneDeferred
            }, async unlink(attachment) {
                const abort = abortByAttachmentId.get(attachment.id)
                const def = deferredByAttachmentId.get(attachment.id)
                if (abort) {
                    abort()
                    def.resolve()
                }
                abortByAttachmentId.delete(attachment.id)
                deferredByAttachmentId.delete(attachment.id)
                await rpc('/mail/attachment/delete', assignDefined({ attachment_id: attachment.id }, { access_token: attachment.accessToken }))
            }, clear() {
                abortByAttachmentId.clear()
                deferredByAttachmentId.clear()
                uploadingAttachmentIds.clear()
            },
        })
        useBus(bus, 'FILE_UPLOAD_ADDED', ({ detail: { upload } }) => {
            const tmpId = upload.data.get('temporary_id')
            if (uploadingAttachmentIds.has(tmpId)) { ui.block() }
        })
        useBus(bus, 'FILE_UPLOAD_LOADED', ({ detail: { upload } }) => {
            const tmpId = upload.data.get('temporary_id')
            if (uploadingAttachmentIds.has(tmpId)) {
                ui.unblock()
                const def = deferredByAttachmentId.get(tmpId)
                uploadingAttachmentIds.delete(tmpId)
                abortByAttachmentId.delete(tmpId)
                if (upload.xhr.status === 413) {
                    notificationService.add(_t('File too large'), { type: 'danger' })
                    return def.reject()
                }
                if (upload.xhr.status !== 200) {
                    notificationService.add(_t('Server error'), { type: 'danger' })
                    return def.reject()
                }
                const response = JSON.parse(upload.xhr.response)
                if (response.error) {
                    notificationService.add(response.error, { type: 'danger' })
                    return def.reject()
                }
                const attachmentData = { ...response, uploading: false, extension: upload.title.split('.').pop(), }
                const attachment = new Attachment()
                assignDefined(attachment, attachmentData, ['id', 'checksum', 'filename', 'mimetype', 'name', 'type', 'url', 'uploading', 'extension', 'accessToken', 'tmpUrl', 'message', 'isAcrux',])
                if (def) {
                    def.resolve(attachment)
                    deferredByAttachmentId.delete(tmpId)
                }
                onFileUploaded?.(attachment)
            }
        })
        useBus(bus, 'FILE_UPLOAD_ERROR', ({ detail: { upload } }) => {
            const tmpId = upload.data.get('temporary_id')
            if (uploadingAttachmentIds.has(tmpId)) {
                ui.unblock()
                abortByAttachmentId.delete(tmpId)
                deferredByAttachmentId.delete(tmpId)
                uploadingAttachmentIds.delete(upload.data.get('temporary_id'))
            }
        })
        return state
    }
    return __exports;
});;
