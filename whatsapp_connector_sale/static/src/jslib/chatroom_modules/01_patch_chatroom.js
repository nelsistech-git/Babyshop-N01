odoo.define('@whatsapp_connector_sale/chatroom_ext/patch-chatroom',['@web/core/utils/patch','@whatsapp_connector/chatroom_mod/chatroom'],function(require){'use strict';let __exports={};const{patch}=require('@web/core/utils/patch')
const{Chatroom}=require('@whatsapp_connector/chatroom_mod/chatroom')
const chatroomSale={setup(){super.setup()
this.saleAllowed=false},getSubEnv(){const out=super.getSubEnv()
out.saleAllowed=()=>this.saleAllowed
return out},async willStart(){await super.willStart()
this.saleAllowed=await this.env.services.user.hasGroup('sales_team.group_sale_salesman')
this.saleFormView=await this.getSaleFormView()},async getSaleFormView(){const{orm}=this.env.services
const data=await orm.call(this.env.chatModel,'check_object_reference',['_sale','acrux_whatsapp_sale_order_form_view'],{context:this.context})
return data[1]}}
patch(Chatroom.prototype,chatroomSale)
return __exports;});;
