odoo.define('@whatsapp_connector/chatroom_mod/attachment-list', ['@mail/core/common/attachment_list'], function (require) {
    'use strict'; let __exports = {}; const { AttachmentList: AttachmentListBase } = require('@mail/core/common/attachment_list')
    const AttachmentList = __exports.AttachmentList = class AttachmentList extends AttachmentListBase {
        onClickUnlink(attachment) {
            let out
            if (attachment && attachment.isAcrux) { out = this.props.unlinkAttachment(attachment) } else { out = super.onClickUnlink(attachment) }
            return out
        }
    }
    __exports[Symbol.for("default")] = AttachmentList
    return __exports;
});;
