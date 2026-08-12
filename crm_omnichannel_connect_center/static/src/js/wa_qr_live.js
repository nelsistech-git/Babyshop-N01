/** @odoo-module **/

import { Component, onWillStart, onWillDestroy, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";

/** Odoo image fields come through as raw base64 - build a usable <img src>. */
function qrImageSrc(base64) {
    return base64 ? `data:image/png;base64,${base64}` : null;
}

const POLL_INTERVAL_MS = 2500;

/**
 * Renders the wizard's own children (the QR <img> field + a status line)
 * and, in the background, calls whatsapp.connect.wizard.action_refresh_status
 * every ~2.5s so the QR image / connected state update WITHOUT the user
 * having to close and reopen the form. Stops polling once connected, or
 * when the widget is destroyed (dialog closed).
 */
export class WaQrLiveWidget extends Component {
    static template = "crm_omnichannel_connect_center.WaQrLive";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ statusText: "Waiting for QR scan..." });
        this._timer = null;

        onWillStart(() => this._poll());
        onWillDestroy(() => this._stopPolling());
    }

    get qrSrc() {
        return qrImageSrc(this.props.record.data.qr_image);
    }

    get connectionState() {
        return this.props.record.data.connection_state;
    }

    get connectedNumber() {
        return this.props.record.data.connected_number;
    }

    async _poll() {
        const resId = this.props.record.resId;
        if (!resId) {
            return;
        }
        try {
            const result = await this.orm.call(
                "whatsapp.connect.wizard",
                "action_refresh_status",
                [resId]
            );
            if (result.state === "connected") {
                this.state.statusText = result.connected_number
                    ? `Connected: ${result.connected_number}`
                    : "Connected";
                this._stopPolling();
                // Pull the fresh qr_image/connection_state fields into the form.
                await this.props.record.load();
                this.render();
                return;
            }
            if (result.state === "qr_pending") {
                this.state.statusText = "Scan this QR code with WhatsApp > Linked Devices";
            } else {
                this.state.statusText = "Disconnected - click Re-generate QR";
            }
            await this.props.record.load();
            this.render();
        } catch {
            this.state.statusText = "Could not reach the server to refresh status - retrying...";
        }
        this._timer = setTimeout(() => this._poll(), POLL_INTERVAL_MS);
    }

    _stopPolling() {
        if (this._timer) {
            clearTimeout(this._timer);
            this._timer = null;
        }
    }
}

registry.category("view_widgets").add("wa_qr_live", {
    component: WaQrLiveWidget,
});
