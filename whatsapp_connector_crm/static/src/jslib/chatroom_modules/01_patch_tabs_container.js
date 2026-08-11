odoo.define('@whatsapp_connector_crm/chatroom_ext/patch-tabs-container',['@web/core/utils/patch','@web/core/l10n/translation','@whatsapp_connector/chatroom_mod/tabs-container','@whatsapp_connector_crm/chatroom_ext/crm-lead-form'],function(require){'use strict';let __exports={};const{patch}=require('@web/core/utils/patch')
const{_t}=require('@web/core/l10n/translation')
const{TabsContainer,chatroomFormResId}=require('@whatsapp_connector/chatroom_mod/tabs-container')
const{CrmLeadForm}=require('@whatsapp_connector_crm/chatroom_ext/crm-lead-form')
const chatroomCrmLeadTab={get tabCrmLeadFormProps(){return{viewTitle:_t('CRM'),viewResId:chatroomFormResId(this.props?.selectedConversation?.lead?.id),selectedConversation:this.props?.selectedConversation,searchButton:true,}},get titles(){const out=super.titles
out.tab_crm_lead=_t('CRM')
return out}}
patch(TabsContainer.prototype,chatroomCrmLeadTab)
patch(TabsContainer.components,{CrmLeadForm,})
return __exports;});;
