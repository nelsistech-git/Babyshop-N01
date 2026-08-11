/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");

function changePassword(env) {
    return {
        type: "item",
        id: "change_password",
        description: _t("Change Password"),
        callback: async () => {
            env.services.action.doAction({
                res_model: "technician.change.password.wizard",
                name: 'Change Password',
                views: [
                    [false, "form"],
                ],
                domain: [],
                type: "ir.actions.act_window",
                target: 'new',
                view_id: false,
                view_type: 'form',
                view_mode: 'form',
            });
        },
        sequence: 20,
    };
}

const customService = {
    start() {
        // Remove specific default items if needed
        userMenuRegistry.remove('documentation');
        userMenuRegistry.remove('support');
        userMenuRegistry.remove('separator');
        userMenuRegistry.remove('odoo_account');
        userMenuRegistry.remove('profile');

        // Add custom "Change Password" item
        userMenuRegistry.add('change_password', changePassword);
    },
};

serviceRegistry.add("change_pass", customService);
