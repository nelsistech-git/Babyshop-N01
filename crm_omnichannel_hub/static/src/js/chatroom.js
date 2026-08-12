/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const POLL_INTERVAL_MS = 8000;
const EMOJI_LIST = [
    "😀", "😂", "😊", "😍", "👍", "🙏", "🎉", "❤️", "😢", "😮",
    "👏", "🔥", "✅", "❌", "⏰", "📦", "💰", "🤝", "😅", "🙌",
];

export class OmniChatRoom extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.user = useService("user");
        this.messagesEndRef = useRef("messagesEnd");
        this.fileInputRef = useRef("fileInput");

        this.state = useState({
            sessions: [],
            channels: [],
            selectedSession: null,
            messages: [],
            partnerContext: null,
            filter: "open",
            channelFilter: "all",
            searchTerm: "",
            composerText: "",
            composerMode: "reply", // 'reply' | 'note'
            quickReplies: [],
            showQuickReplies: false,
            showEmojiPicker: false,
            showInfoPanel: true,
            infoTab: "info", // info | crm | sales | inventory | history
            loadingSessions: true,
            loadingMessages: false,
            loadingContext: false,
            sending: false,
            attaching: false,
        });

        this.emojiList = EMOJI_LIST;

        onWillStart(async () => {
            await Promise.all([this.loadSessions(), this.loadQuickReplies(), this.loadChannels()]);
        });

        onMounted(() => {
            this.pollTimer = setInterval(() => this.poll(), POLL_INTERVAL_MS);
        });

        onWillUnmount(() => {
            clearInterval(this.pollTimer);
        });
    }

    // =====================================================================
    // DATA LOADING
    // =====================================================================
    get sessionDomain() {
        const domain = [];
        if (this.state.filter === "open") {
            domain.push(["state", "in", ["new", "open", "pending"]]);
        } else if (this.state.filter === "unread") {
            domain.push(["is_unread", "=", true]);
        } else if (this.state.filter === "mine") {
            domain.push(["agent_id", "=", this.user.userId]);
        } else if (this.state.filter === "starred") {
            domain.push(["is_starred", "=", true]);
        } else if (this.state.filter === "closed") {
            domain.push(["state", "=", "closed"]);
        }
        if (this.state.channelFilter !== "all") {
            domain.push(["channel_id", "=", this.state.channelFilter]);
        }
        if (this.state.searchTerm) {
            domain.push(["display_name", "ilike", this.state.searchTerm]);
        }
        return domain;
    }

    async loadSessions() {
        this.state.loadingSessions = true;
        try {
            const sessions = await this.orm.searchRead(
                "crm.chat.session",
                this.sessionDomain,
                [
                    "display_name", "channel_id", "channel_code", "state", "priority", "sla_status",
                    "is_unread", "unread_count", "last_message_preview", "last_message_date",
                    "agent_id", "partner_id", "lead_id", "tag_ids", "is_starred",
                ],
                { order: "last_message_date desc", limit: 200 }
            );
            this.state.sessions = sessions;
            if (this.state.selectedSession) {
                const stillThere = sessions.find((s) => s.id === this.state.selectedSession.id);
                if (stillThere) {
                    this.state.selectedSession = stillThere;
                }
            }
        } finally {
            this.state.loadingSessions = false;
        }
    }

    async loadChannels() {
        const channels = await this.orm.searchRead(
            "crm.channel", [], ["name", "code"], { order: "sequence" }
        );
        let counts = [];
        try {
            counts = await this.orm.readGroup(
                "crm.chat.session",
                [["state", "in", ["new", "open", "pending"]]],
                ["channel_id"],
                ["channel_id"]
            );
        } catch (err) {
            counts = [];
        }
        const countMap = {};
        for (const c of counts) {
            if (c.channel_id) {
                countMap[c.channel_id[0]] = c.channel_id_count;
            }
        }
        this.state.channels = channels.map((c) => ({ ...c, count: countMap[c.id] || 0 }));
    }

    async loadQuickReplies() {
        const replies = await this.orm.searchRead(
            "crm.quick.reply", [], ["name", "title", "message"], { limit: 50 }
        );
        this.state.quickReplies = replies;
    }

    async loadMessages(sessionId) {
        this.state.loadingMessages = true;
        try {
            const messages = await this.orm.searchRead(
                "crm.chat.message",
                [["session_id", "=", sessionId]],
                ["direction", "message_type", "body", "message_date", "agent_id", "is_delivered", "is_seen"],
                { order: "message_date asc", limit: 500 }
            );
            this.state.messages = messages;
            this.scrollToBottom();
        } finally {
            this.state.loadingMessages = false;
        }
    }

    async loadPartnerContext(partnerIdTuple) {
        if (!partnerIdTuple) {
            this.state.partnerContext = null;
            return;
        }
        this.state.loadingContext = true;
        try {
            const context = await this.orm.call(
                "crm.omni.chat.context", "get_partner_context", [partnerIdTuple[0]]
            );
            this.state.partnerContext = context;
        } finally {
            this.state.loadingContext = false;
        }
    }

    async poll() {
        await this.loadSessions();
        await this.loadChannels();
        if (this.state.selectedSession) {
            await this.loadMessages(this.state.selectedSession.id);
        }
    }

    // =====================================================================
    // SELECTION / FILTERS
    // =====================================================================
    async selectSession(session) {
        this.state.selectedSession = session;
        this.state.showQuickReplies = false;
        this.state.showEmojiPicker = false;
        this.state.composerMode = "reply";
        this.state.infoTab = "info";
        await Promise.all([
            this.loadMessages(session.id),
            this.loadPartnerContext(session.partner_id),
        ]);
        if (session.is_unread) {
            await this.orm.call("crm.chat.session", "action_mark_read", [[session.id]]);
            session.is_unread = false;
            session.unread_count = 0;
        }
    }

    setFilter(filter) {
        this.state.filter = filter;
        this.loadSessions();
    }

    setChannelFilter(channelId) {
        this.state.channelFilter = channelId;
        this.loadSessions();
    }

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;
        this.loadSessions();
    }

    toggleInfoPanel() {
        this.state.showInfoPanel = !this.state.showInfoPanel;
    }

    setInfoTab(tab) {
        this.state.infoTab = tab;
    }

    // =====================================================================
    // COMPOSER
    // =====================================================================
    setComposerMode(mode) {
        this.state.composerMode = mode;
        this.state.showQuickReplies = false;
    }

    toggleQuickReplies() {
        this.state.showQuickReplies = !this.state.showQuickReplies;
        this.state.showEmojiPicker = false;
    }

    toggleEmojiPicker() {
        this.state.showEmojiPicker = !this.state.showEmojiPicker;
        this.state.showQuickReplies = false;
    }

    insertEmoji(emoji) {
        this.state.composerText += emoji;
        this.state.showEmojiPicker = false;
    }

    applyQuickReply(reply) {
        this.state.composerText = reply.message;
        this.state.showQuickReplies = false;
    }

    async sendMessage() {
        const body = this.state.composerText.trim();
        if (!body || !this.state.selectedSession || this.state.sending) {
            return;
        }
        this.state.sending = true;
        try {
            await this.orm.create("crm.chat.message", [{
                session_id: this.state.selectedSession.id,
                direction: this.state.composerMode === "note" ? "note" : "out",
                message_type: "text",
                body: body,
            }]);
            this.state.composerText = "";
            await this.loadMessages(this.state.selectedSession.id);
            await this.loadSessions();
        } catch (err) {
            this.notification.add("Failed to send message.", { type: "danger" });
        } finally {
            this.state.sending = false;
        }
    }

    onComposerKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    triggerFilePicker() {
        if (this.fileInputRef.el) {
            this.fileInputRef.el.click();
        }
    }

    async onFileSelected(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file || !this.state.selectedSession) return;
        this.state.attaching = true;
        try {
            const base64 = await this._readFileAsBase64(file);
            const attachmentId = await this.orm.create("ir.attachment", [{
                name: file.name,
                datas: base64,
                res_model: "crm.chat.message",
                res_id: 0,
            }]);
            const isImage = file.type && file.type.startsWith("image/");
            const messageId = await this.orm.create("crm.chat.message", [{
                session_id: this.state.selectedSession.id,
                direction: this.state.composerMode === "note" ? "note" : "out",
                message_type: isImage ? "image" : "document",
                body: file.name,
                attachment_ids: [[6, 0, attachmentId]],
            }]);
            await this.orm.write("ir.attachment", attachmentId, { res_id: messageId[0] });
            await this.loadMessages(this.state.selectedSession.id);
            await this.loadSessions();
        } catch (err) {
            this.notification.add("Failed to attach file.", { type: "danger" });
        } finally {
            this.state.attaching = false;
            ev.target.value = "";
        }
    }

    _readFileAsBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(",")[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    // =====================================================================
    // HEADER ACTIONS
    // =====================================================================
    async toggleStar() {
        if (!this.state.selectedSession) return;
        await this.orm.call("crm.chat.session", "action_toggle_star", [[this.state.selectedSession.id]]);
        this.state.selectedSession.is_starred = !this.state.selectedSession.is_starred;
    }

    openMailto() {
        const email = this.state.partnerContext && this.state.partnerContext.contact
            && this.state.partnerContext.contact.email;
        if (email) {
            window.open("mailto:" + email, "_blank");
        } else {
            this.notification.add("No email on file for this contact.", { type: "warning" });
        }
    }

    async closeConversation() {
        if (!this.state.selectedSession) return;
        await this.orm.call("crm.chat.session", "action_close", [[this.state.selectedSession.id]]);
        this.state.selectedSession.state = "closed";
        await this.loadSessions();
    }

    async reopenConversation() {
        if (!this.state.selectedSession) return;
        await this.orm.call("crm.chat.session", "action_reopen", [[this.state.selectedSession.id]]);
        this.state.selectedSession.state = "open";
        await this.loadSessions();
    }

    async markSpam() {
        if (!this.state.selectedSession) return;
        await this.orm.call("crm.chat.session", "action_mark_spam", [[this.state.selectedSession.id]]);
        this.state.selectedSession.state = "spam";
        await this.loadSessions();
    }

    async convertToLead() {
        if (!this.state.selectedSession) return;
        await this.orm.call("crm.chat.session", "action_convert_to_lead", [[this.state.selectedSession.id]]);
        await this.loadSessions();
        const refreshed = this.state.sessions.find((s) => s.id === this.state.selectedSession.id);
        if (refreshed) {
            this.state.selectedSession = refreshed;
        }
    }

    async openLead() {
        if (!this.state.selectedSession || !this.state.selectedSession.lead_id) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            view_mode: "form",
            views: [[false, "form"]],
            res_id: this.state.selectedSession.lead_id[0],
        });
    }

    async openPartner() {
        const contact = this.state.partnerContext && this.state.partnerContext.contact;
        if (!contact) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            view_mode: "form",
            views: [[false, "form"]],
            res_id: contact.id,
        });
    }

    async openRecord(model, id) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            view_mode: "form",
            views: [[false, "form"]],
            res_id: id,
        });
    }

    openListView() {
        this.action.doAction("crm_omnichannel_hub.action_crm_chat_session");
    }

    scrollToBottom() {
        requestAnimationFrame(() => {
            if (this.messagesEndRef.el) {
                this.messagesEndRef.el.scrollIntoView({ block: "end" });
            }
        });
    }

    // =====================================================================
    // DISPLAY HELPERS
    // =====================================================================
    formatTime(datetimeStr) {
        if (!datetimeStr) return "";
        const d = new Date(datetimeStr.replace(" ", "T") + "Z");
        return d.toLocaleString(undefined, { hour: "2-digit", minute: "2-digit" });
    }

    formatDate(datetimeStr) {
        if (!datetimeStr) return "";
        const d = new Date(datetimeStr.replace(" ", "T") + "Z");
        return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    }

    formatNumber(value) {
        if (value === undefined || value === null) return "0";
        return Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
    }

    initials(name) {
        if (!name) return "?";
        return name.trim().split(/\s+/).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
    }

    channelIcon(channelCode) {
        return {
            whatsapp: "fa-whatsapp",
            facebook: "fa-facebook",
            instagram: "fa-instagram",
            telegram: "fa-telegram",
            email: "fa-envelope",
            call: "fa-phone",
        }[channelCode] || "fa-comment";
    }

    channelIconClass(channelCode) {
        return {
            whatsapp: "o_omni_channel_icon_whatsapp",
            facebook: "o_omni_channel_icon_facebook",
            instagram: "o_omni_channel_icon_instagram",
            telegram: "o_omni_channel_icon_telegram",
            email: "o_omni_channel_icon_email",
            call: "o_omni_channel_icon_call",
        }[channelCode] || "o_omni_channel_icon_other";
    }

    messageTickIcon(msg) {
        if (msg.direction !== "out") return null;
        if (msg.is_seen) return "fa-check-double o_omni_tick_seen";
        if (msg.is_delivered) return "fa-check-double o_omni_tick_delivered";
        return "fa-check o_omni_tick_sent";
    }

    /**
     * Annotates state.messages with day-divider pseudo-entries so the
     * template can render WhatsApp-style "Today" / "Yesterday" separators.
     */
    get messagesWithDividers() {
        const result = [];
        let lastDay = null;
        for (const msg of this.state.messages) {
            const day = (msg.message_date || "").slice(0, 10);
            if (day !== lastDay) {
                result.push({ isDivider: true, id: "divider-" + day, label: this.formatDayDivider(msg.message_date) });
                lastDay = day;
            }
            result.push(msg);
        }
        return result;
    }

    formatDayDivider(datetimeStr) {
        if (!datetimeStr) return "";
        const d = new Date(datetimeStr.replace(" ", "T") + "Z");
        const today = new Date();
        const yesterday = new Date();
        yesterday.setDate(today.getDate() - 1);
        const sameDay = (a, b) => a.toDateString() === b.toDateString();
        if (sameDay(d, today)) return "Today";
        if (sameDay(d, yesterday)) return "Yesterday";
        return d.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
    }
}

OmniChatRoom.template = "crm_omnichannel_hub.OmniChatRoom";

registry.category("actions").add("crm_omni_chatroom", OmniChatRoom);
