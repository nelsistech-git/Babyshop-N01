odoo.define('@whatsapp_connector_sale/chatroom_ext/patch-tabs-container',['@web/core/utils/patch','@web/core/l10n/translation','@whatsapp_connector/chatroom_mod/tabs-container','@whatsapp_connector_sale/chatroom_ext/sale-form','@whatsapp_connector_sale/chatroom_ext/sale-indicator'],function(require){'use strict';let __exports={};const{patch}=require('@web/core/utils/patch')
const{_t}=require('@web/core/l10n/translation')
const{TabsContainer,chatroomFormResId}=require('@whatsapp_connector/chatroom_mod/tabs-container')
const{SaleForm}=require('@whatsapp_connector_sale/chatroom_ext/sale-form')
const{SaleIndicator}=require('@whatsapp_connector_sale/chatroom_ext/sale-indicator')
const chatroomSaleTab={setup(){super.setup()
this.emptyPartnerMsg=_t('This conversation does not have a partner.')},get tabSaleFormProps(){return{viewTitle:_t('Order'),viewResId:chatroomFormResId(this.props?.selectedConversation?.sale?.id),selectedConversation:this.props?.selectedConversation,searchButton:true,viewId:this.props.saleFormView,}},get titles(){const out=super.titles
out.tab_order=_t('Order')
return out}}
patch(TabsContainer.prototype,chatroomSaleTab)
patch(TabsContainer.components,{SaleForm,SaleIndicator,})
patch(TabsContainer.props,{saleFormView:{type:Number,optional:true},})
return __exports;});;
