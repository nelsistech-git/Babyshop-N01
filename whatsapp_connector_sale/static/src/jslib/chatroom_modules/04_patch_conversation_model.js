odoo.define('@whatsapp_connector_sale/chatroom_ext/patch-conversation-model',['@web/core/utils/patch','@whatsapp_connector/chatroom_mod/conversation-model'],function(require){'use strict';let __exports={};const{patch}=require('@web/core/utils/patch')
const{ConversationModel}=require('@whatsapp_connector/chatroom_mod/conversation-model')
const chatroomSale={constructor(comp,base){super.constructor(comp,base)
this.sale={id:0,name:''}},updateFromJson(base){super.updateFromJson(base)
if('sale_order_id'in base){this.sale=this.convertRecordField(base.sale_order_id)}}}
patch(ConversationModel.prototype,chatroomSale)
return __exports;});;
