/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Loads the Facebook JS SDK with the App ID configured in Settings, pops
 * the Facebook Login dialog, and on success asks the backend
 * (/omni/connect/facebook/pages) to list every Page the user manages.
 * Each Page gets a "Connect" button that calls
 * /omni/connect/facebook/connect_page, which stores the token AND
 * subscribes the webhook server-side - the user never sees a token.
 */
export class FacebookConnectDashboard extends Component {
    static template = "crm_omnichannel_connect_center.FacebookConnect";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.state = useState({
            appId: null,
            sdkReady: false,
            loading: false,
            pages: null,
            error: null,
        });

        onWillStart(async () => {
            const params = await this.orm.call("ir.config_parameter", "search_read", [
                [["key", "=", "crm_omnichannel_connect_center.meta_app_id"]],
                ["value"],
            ]);
            this.state.appId = params.length ? params[0].value : null;
            if (this.state.appId) {
                this._loadFacebookSdk(this.state.appId);
            }
        });
    }

    _loadFacebookSdk(appId) {
        if (window.FB) {
            this.state.sdkReady = true;
            return;
        }
        window.fbAsyncInit = () => {
            window.FB.init({ appId, cookie: true, xfbml: false, version: "v19.0" });
            this.state.sdkReady = true;
        };
        const script = document.createElement("script");
        script.src = "https://connect.facebook.net/en_US/sdk.js";
        script.async = true;
        script.defer = true;
        document.body.appendChild(script);
    }

    onLoginClick() {
        if (!window.FB) {
            this.state.error = "Facebook SDK did not load yet - wait a second and try again.";
            return;
        }
        this.state.loading = true;
        this.state.error = null;
        window.FB.login(
            (response) => this._onFbLoginResponse(response),
            {
                scope: [
                    "pages_show_list",
                    "pages_messaging",
                    "pages_manage_metadata",
                    "instagram_basic",
                    "instagram_manage_messages",
                ].join(","),
            }
        );
    }

    async _onFbLoginResponse(response) {
        if (response.status !== "connected" || !response.authResponse) {
            this.state.loading = false;
            this.state.error = "Facebook login was cancelled or did not grant the required permissions.";
            return;
        }
        try {
            const result = await this.rpc("/omni/connect/facebook/pages", {
                access_token: response.authResponse.accessToken,
            });
            this.state.loading = false;
            if (!result.ok) {
                this.state.error = result.error;
                return;
            }
            this.state.pages = result.pages.map((p) => ({ ...p, connecting: false, connected: false }));
        } catch (e) {
            this.state.loading = false;
            this.state.error = "Could not reach the server.";
        }
    }

    async onConnectPage(page) {
        page.connecting = true;
        try {
            const result = await this.rpc("/omni/connect/facebook/connect_page", {
                page_id: page.id,
                page_name: page.name,
                page_access_token: page.access_token,
                instagram_id: page.instagram_id,
            });
            page.connecting = false;
            if (result.ok) {
                page.connected = true;
                this.notification.add(result.message, { type: "success" });
            } else {
                this.notification.add(result.error, { type: "danger", sticky: true });
            }
        } catch (e) {
            page.connecting = false;
            this.notification.add("Could not reach the server.", { type: "danger" });
        }
    }
}

registry.category("actions").add("fb_connect_dashboard", FacebookConnectDashboard);
