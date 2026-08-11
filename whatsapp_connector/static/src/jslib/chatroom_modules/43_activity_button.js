odoo.define('@whatsapp_connector/chatroom_mod/activity-button', ['@mail/core/web/activity_button'], function (require) {
    'use strict'; let __exports = {}; const { ActivityButton: ActivityButtonBase } = require('@mail/core/web/activity_button')
    const ActivityButton = __exports.ActivityButton = class ActivityButton extends ActivityButtonBase {
        setup() {
            super.setup()
            this.env;
        }
        get buttonClass() {
            let classes = super.buttonClass.split(' ')
            classes = classes.filter(c => c !== this.props.record.data.activity_type_icon)
            classes = classes.filter(c => !['text-dark', 'btn-link'].includes(c))
            classes.push('fa-clock-o')
            return classes.join(' ')
        }
    }
    return __exports;
});;
