odoo.define('@whatsapp_connector_sale/chatroom_ext/sale-form',['@web/core/utils/patch','@web/core/utils/hooks','@whatsapp_connector/chatroom_mod/chatroom-action-tab','@whatsapp_connector/chatroom_mod/conversation-model'],function(require){'use strict';let __exports={};const{patch}=require('@web/core/utils/patch')
const{useBus}=require('@web/core/utils/hooks')
const{ChatroomActionTab}=require('@whatsapp_connector/chatroom_mod/chatroom-action-tab')
const{ConversationModel}=require('@whatsapp_connector/chatroom_mod/conversation-model')
const SaleForm=__exports.SaleForm=class SaleForm extends ChatroomActionTab{setup(){super.setup()
this.env;this.props
useBus(this.env.chatBus,'productDragInit',()=>{this.elRef.el.classList.add('drop-active')})
useBus(this.env.chatBus,'productDragging',({x,y})=>{if(this.isInside(x,y)){this.elRef.el.classList.add('drop-hover')}else{this.elRef.el.classList.remove('drop-hover')}})
useBus(this.env.chatBus,'productDragEnd',()=>{this.elRef.el.classList.remove('drop-active')
this.elRef.el.classList.remove('drop-hover')})
useBus(this.env.chatBus,'productDrop',async({x,y,product})=>{if(this.isInside(x,y)&&this.props.selectedConversation?.isCurrent()){this.env.chatBus.trigger('chatroomAddToOrder',product)}})}
getExtraContext(props){const context=Object.assign(super.getExtraContext(props),{default_partner_id:props.selectedConversation.partner.id,})
if(props.selectedConversation.team.id){context['default_team_id']=props.selectedConversation.team.id}
return context}
async onSave(record){await super.onSave(record)
if(record.resId!==this.props.selectedConversation.sale.id){await this.env.services.orm.write(this.env.chatModel,[this.props.selectedConversation.id],{sale_order_id:record.resId},{context:this.env.context})
this.props.selectedConversation.updateFromJson({sale_order_id:[record.resId,record.data.name]})
this.env.chatBus.trigger('updateConversation',this.props.selectedConversation)}}
_getOnSearchChatroomDomain(){let domain=super._getOnSearchChatroomDomain()
domain.push(['conversation_id','=',this.props.selectedConversation.id])
if(this.props.selectedConversation.partner.id){domain.unshift('|')
domain.push(['partner_id','=',this.props.selectedConversation.partner.id])}
return domain}}
SaleForm.props=Object.assign({},SaleForm.props)
SaleForm.defaultProps=Object.assign({},SaleForm.defaultProps)
patch(SaleForm.props,{selectedConversation:{type:ConversationModel.prototype},viewModel:{type:String,optional:true},viewType:{type:String,optional:true},viewKey:{type:String,optional:true},})
patch(SaleForm.defaultProps,{viewModel:'sale.order',viewType:'form',viewKey:'sale_form',})
return __exports;});;
