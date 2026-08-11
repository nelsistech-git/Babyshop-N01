odoo.define('@whatsapp_connector/chatroom_mod/chatroom-action-tab', ['@web/core/l10n/translation', '@web/core/browser/browser', '@odoo/owl', '@whatsapp_connector/chatroom_mod/conversation-model'], function (require) {
    'use strict'; let __exports = {}; const { _t } = require('@web/core/l10n/translation')
    const { browser } = require('@web/core/browser/browser')
    const { Component, xml, onWillStart, onWillDestroy, onWillUpdateProps, useRef } = require('@odoo/owl')
    const { ConversationModel } = require('@whatsapp_connector/chatroom_mod/conversation-model')
    const ChatroomActionTab = __exports.ChatroomActionTab = class ChatroomActionTab extends Component {
        setup() {
            super.setup()
            this.env; this.props; this.info = {}
            this.elRef = useRef('elRef')
            const onActionManagerUpdate = this.onActionManagerUpdate.bind(this)
            this.env.bus.addEventListener('ACTION_MANAGER:UPDATE', onActionManagerUpdate)
            onWillDestroy(() => this.env.bus.removeEventListener('ACTION_MANAGER:UPDATE', onActionManagerUpdate))
            onWillStart(this.willStart.bind(this))
            onWillUpdateProps(this.onWillUpdateProps.bind(this))
        }
        async willStart() { await this.makeAction(this.props) }
        async onWillUpdateProps(nextProps) { await this.makeAction(nextProps) }
        async makeAction(props) {
            const prom = new Promise(res => this.infoResolve = res)
            this.env.services.action.doAction(this.getActionConfig(props), this.getActionOptions(props))
            await prom
        }
        onActionManagerUpdate({ detail: info }) {
            if (info?.componentProps?.chatroomTab === this.props.viewKey) {
                this.info = info
                this.info.Component = class ChatroomController extends info.Component {
                    onMounted() {
                        const hashOrigin = this.env.services.router?.current?.hash
                        const current_action = browser.sessionStorage.getItem('current_action')
                        super.onMounted()
                        browser.sessionStorage.setItem('current_action', current_action)
                        if (hashOrigin) { this.env.services.router.replaceState(hashOrigin, { replace: true }) }
                    }
                }
                this.infoResolve()
            }
        }
        getActionConfig(props) {
            const context = { ...this.env.context, ...this.getExtraContext(props) }
            this._contextHook(context)
            return { type: 'ir.actions.act_window', view_type: 'form', view_mode: props.viewType, res_model: props.viewModel, views: this.getActionViews(props), target: 'current', context: context, res_id: props.viewResId, flags: this.getActionFlags(props), name: props.viewTitle, }
        }
        getActionViews(props) {
            let out
            if (props.viewType === 'form') { out = [[props.viewId, props.viewType]] } else if (props.viewType === 'list') { out = [[props.viewId, props.viewType], [false, 'search']] } else if (props.viewType === 'kanban') { out = [[props.viewId, props.viewType], [false, 'search']] } else { throw new Error('Not implemented.') }
            return out
        }
        _contextHook(context) {
            if ((['res.partner', 'crm.lead'].includes(this.props.viewModel) && this.props.selectedConversation?.isOwnerFacebook() && !this.props.selectedConversation?.isWabaExtern()) || this.props.selectedConversation?.isPrivate || this.props.selectedConversation?.isGroup) {
                if ('default_mobile' in context) { delete context.default_mobile }
                if ('default_phone' in context) { delete context.default_phone }
            }
        }
        getExtraContext(props) { return { default_conversation_id: props?.selectedConversation?.id } }
        getActionFlags(props) {
            let out
            if (props.viewType === 'form') { out = { withControlPanel: false, footerToButtons: false, hasSearchView: false, hasSidebar: false, mode: 'edit', searchMenuTypes: false, } } else if (props.viewType === 'list') { out = { withControlPanel: true, footerToButtons: false, hasSearchView: true, hasSidebar: false, searchMenuTypes: ['filter', 'groupBy'], withSearchPanel: true, withSearchBar: true, } } else if (props.viewType === 'kanban') { out = { withControlPanel: true, footerToButtons: false, hasSearchView: true, hasSidebar: false, searchMenuTypes: ['filter', 'groupBy'], withSearchPanel: true, withSearchBar: true, } } else { throw new Error('Not implemented.') }
            return out
        }
        getActionOptions(props) {
            let stackPosition = 'replaceCurrentAction'
            if (this.env.chatroomJsId === this.env.services.action.currentController.action.jsId) { stackPosition = false }
            return { clearBreadcrumbs: false, stackPosition: stackPosition, props: this.getActionProps(props), }
        }
        getActionProps(props) {
            const out = { chatroomTab: props.viewKey }
            if (props.viewType === 'form') { Object.assign(out, { onSave: this.onSave.bind(this), searchButton: props.searchButton, searchButtonString: props.searchButtonString || _t('Search'), searchAction: this._onSearchChatroom.bind(this) }) } else if (props.viewType === 'list') { } else if (props.viewType === 'kanban') { } else { throw new Error('Not implemented.') }
            return out
        }
        _getSearchAction() {
            const context = { ...this.env.context, chatroom_wizard_search: true }
            return { type: 'ir.actions.act_window', view_type: 'form', view_mode: 'list', res_model: this.props.viewModel, domain: this._getOnSearchChatroomDomain(), views: [[false, 'list']], target: 'new', context: context, }
        }
        _onSearchChatroom() {
            const action = this._getSearchAction()
            const options = { props: { showButtons: false, chatroomTab: this.props.viewKey, chatroomSelect: this._onSelectedRecord.bind(this) } }
            return this.env.services.action.doAction(action, options)
        }
        _getOnSearchChatroomDomain() { return [] }
        async _onSelectedRecord(record) {
            await this.env.services.action.doAction({ type: 'ir.actions.act_window_close' })
            await this.onSave(record)
        }
        async onSave(record) { if (this.props.viewType === 'form') { if (record.data.partner_id) { if (record.data.partner_id[0] !== this.props.selectedConversation.partner.id) { await this.savePartner(record.data.partner_id) } } } }
        async savePartner(partner) {
            await this.env.services.orm.write(this.env.chatModel, [this.props.selectedConversation.id], { res_partner_id: partner[0] }, { context: this.env.context })
            const [{ image_url }] = await this.env.services.orm.read(this.env.chatModel, [this.props.selectedConversation.id], ['image_url'], { context: this.env.context })
            this.props.selectedConversation.updateFromJson({ res_partner_id: partner, image_url })
            this.env.chatBus.trigger('updateConversation', this.props.selectedConversation)
        }
        isInside(x, y) {
            let out
            const rect = this.elRef.el.getBoundingClientRect()
            if (rect.top <= y && y <= rect.bottom) { out = rect.left <= x && x <= rect.right } else { out = false }
            return out
        }
    }
    Object.assign(ChatroomActionTab, { props: { viewId: { type: Number, optional: true }, viewModel: String, viewType: String, viewTitle: String, viewKey: String, viewResId: { type: Number, optional: true }, selectedConversation: { type: ConversationModel.prototype, optional: true }, searchButton: { type: Boolean, optional: true }, searchButtonString: { type: String, optional: true }, }, defaultProps: {} })
    ChatroomActionTab.template = xml`
    <t t-name="chatroom.ActionTab">
      <div class="o_ActionTab" t-attf-class="{{env.isVerticalView() ? 'vertical': 'horizontal'}}" t-ref="elRef">
        <t t-if="info.Component" t-component="info.Component" className="'o_action'" t-props="info.componentProps" t-key="info.id"/>
      </div>
    </t>`; return __exports;
});;
