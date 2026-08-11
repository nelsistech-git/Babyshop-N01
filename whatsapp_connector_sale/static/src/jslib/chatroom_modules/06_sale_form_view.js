odoo.define('@whatsapp_connector_sale/chatroom_ext/sale-form-view',['@web/core/registry','@web/views/form/form_view','@whatsapp_connector_sale/chatroom_ext/sale-form-renderer'],function(require){'use strict';let __exports={};const{registry}=require('@web/core/registry')
const{formView}=require('@web/views/form/form_view')
const{SaleFormRenderer}=require('@whatsapp_connector_sale/chatroom_ext/sale-form-renderer')
const SaleFormView=__exports.SaleFormView={...formView,Renderer:SaleFormRenderer,}
registry.category('views').add('acrux_whatsapp_sale_order',SaleFormView)
return __exports;});;
