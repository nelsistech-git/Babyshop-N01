odoo.define('@whatsapp_connector/chatroom_mod/attachment', ['@mail/core/common/attachment_model'], function (require) {
    'use strict'; let __exports = {}; const { Attachment: AttachmentBase } = require('@mail/core/common/attachment_model')
    const Attachment = __exports.Attachment = class Attachment extends AttachmentBase {
        message = undefined
        get isDeletable() { return !this.message }
        get originThread() { return undefined }
    }
    __exports[Symbol.for("default")] = Attachment
    return __exports;
});;
