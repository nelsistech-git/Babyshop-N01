odoo.define('@whatsapp_connector_sale/chatroom_ext/sale-form-renderer',['@web/views/form/form_renderer','@web/core/utils/hooks'],function(require){'use strict';let __exports={};const{FormRenderer}=require('@web/views/form/form_renderer')
const{useBus}=require('@web/core/utils/hooks')
const SaleFormRenderer=__exports.SaleFormRenderer=class SaleFormRenderer extends FormRenderer{setup(){super.setup()
useBus(this.env.chatBus,'chatroomAddToOrder',async product=>{const context={...this.env.services.user.context,default_product_id:parseInt(product.id)}
const newLine=await this.props.record.data.order_line.addNew({context,mode:'edit',position:'bottom',})
await newLine.switchMode('readonly')})}}
return __exports;});;
