odoo.define('@whatsapp_connector_crm/chatroom_ext/patch-conversation-model',['@web/core/utils/patch','@whatsapp_connector/chatroom_mod/conversation-model'],function(require){'use strict';let __exports={};const{patch}=require('@web/core/utils/patch')
const{ConversationModel}=require('@whatsapp_connector/chatroom_mod/conversation-model')
const chatroomCrm={constructor(comp,base){super.constructor(comp,base)
this.lead={id:0,name:''}},updateFromJson(base){super.updateFromJson(base)
if('crm_lead_id'in base){this.lead=this.convertRecordField(base.crm_lead_id)}}}
patch(ConversationModel.prototype,chatroomCrm)
return __exports;});;
