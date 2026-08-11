odoo.define('@whatsapp_connector/chatroom_mod/tabs-container', ['@web/core/l10n/translation', '@web/core/notebook/notebook', '@odoo/owl', '@whatsapp_connector/chatroom_mod/notebook-chat', '@whatsapp_connector/chatroom_mod/default-answer', '@whatsapp_connector/chatroom_mod/conversation-form', '@whatsapp_connector/chatroom_mod/conversation-kanban', '@whatsapp_connector/chatroom_mod/conversation-panel-form', '@whatsapp_connector/chatroom_mod/ai-inteface-form', '@whatsapp_connector/chatroom_mod/partner-form', '@whatsapp_connector/chatroom_mod/conversation-model', '@whatsapp_connector/chatroom_mod/default-answer-model', '@whatsapp_connector/chatroom_mod/product-container', '@whatsapp_connector/chatroom_mod/user-model'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation')
    const { Notebook } = require('@web/core/notebook/notebook')
    const { Component } = require('@odoo/owl')
    const { NotebookChat } = require('@whatsapp_connector/chatroom_mod/notebook-chat')
    const { DefaultAnswer } = require('@whatsapp_connector/chatroom_mod/default-answer')
    const { ConversationForm } = require('@whatsapp_connector/chatroom_mod/conversation-form')
    const { ConversationKanban } = require('@whatsapp_connector/chatroom_mod/conversation-kanban')
    const { ConversationPanelForm } = require('@whatsapp_connector/chatroom_mod/conversation-panel-form')
    const { AiIntefaceForm } = require('@whatsapp_connector/chatroom_mod/ai-inteface-form')
    const { PartnerForm } = require('@whatsapp_connector/chatroom_mod/partner-form')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const { DefaultAnswerModel } = require('@whatsapp_connector/chatroom_mod/default-answer-model')
    const { ProductContainer } = require('@whatsapp_connector/chatroom_mod/product-container')
    const { UserModel } = require('@whatsapp_connector/chatroom_mod/user-model')
    /** Odoo uses false for empty Many2one; Owl Number props reject false — omit / pass undefined instead. */
    function chatroomFormResId(raw) {
        if (raw === undefined || raw === null || raw === false) {
            return undefined
        }
        const n = typeof raw === 'number' ? raw : parseInt(raw, 10)
        return Number.isFinite(n) && n > 0 ? n : undefined
    }
    __exports.chatroomFormResId = chatroomFormResId
    const TabsContainer = __exports.TabsContainer = class TabsContainer extends Component {
        setup() {
            super.setup()
            this.env; this.props
        }
        get tabPartnerFormProps() {
            return {
                viewTitle: _t('Partner'),
                viewResId: chatroomFormResId(this.props.selectedConversation?.partner?.id),
                searchButton: true,
                searchButtonString: _t('Search Existing'),
                selectedConversation: this.props.selectedConversation,
            }
        }
        get tabConversationFormProps() {
            return {
                viewId: this.props.conversationInfoForm,
                viewTitle: _t('Info'),
                viewResId: chatroomFormResId(this.props.selectedConversation?.id),
                selectedConversation: this.props.selectedConversation,
            }
        }
        get tabConversationKanbanProps() { return { viewId: this.props.conversationKanban, viewTitle: _t('Status'), formViewId: this.props.conversationInfoForm, selectedConversation: this.props.selectedConversation, } }
        get tabConversationPanelFormProps() { return { viewId: this.props.conversationPanelForm, viewTitle: _t('Panel'), } }
        get tabAiIntefaceFormProps() { return { viewId: this.props.aiIntefaceForm, viewTitle: _t('AI'), selectedConversation: this.props.selectedConversation, } }
        get titles() { return { tab_default_answer: _t('Default Answers'), tab_partner: _t('Partner'), tab_init_conversation: _t('Conversations'), tab_product_grid: _t('Products'), tab_conv_info: _t('Info'), tab_conv_kanban: _t('Chat Funnels'), tab_conv_panel: _t('Activities'), tab_ai_inteface: _t('Artificial Intelligence'), } }
        get comp() { return this.constructor.components }
    }
    Object.assign(TabsContainer, { template: 'chatroom.TabsContainer', props: { selectedConversation: ConversationModel.prototype, defaultAnswers: { type: Array, element: DefaultAnswerModel.prototype, }, conversationUsedFields: { type: Array, element: String, }, conversationInfoForm: { type: Number, optional: true }, conversationKanban: { type: Number, optional: true }, conversationPanelForm: { type: Number, optional: true }, aiIntefaceForm: { type: Number, optional: true }, className: { type: String, optional: true, }, tabSelected: { type: String, optional: true }, user: UserModel.prototype, }, defaultProps: { className: '' }, components: { Notebook, NotebookChat, DefaultAnswer, PartnerForm, ConversationForm, ConversationKanban, ConversationPanelForm, AiIntefaceForm, ProductContainer, }, })
    return __exports;
});;
