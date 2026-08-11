odoo.define('@whatsapp_connector_crm/chatroom_ext/crm-lead-form',['@web/core/utils/patch','@whatsapp_connector/chatroom_mod/chatroom-action-tab','@whatsapp_connector/chatroom_mod/conversation-model'],function(require){'use strict';let __exports={};const{patch}=require('@web/core/utils/patch')
const{ChatroomActionTab}=require('@whatsapp_connector/chatroom_mod/chatroom-action-tab')
const{ConversationModel}=require('@whatsapp_connector/chatroom_mod/conversation-model')
const CrmLeadForm=__exports.CrmLeadForm=class CrmLeadForm extends ChatroomActionTab{setup(){super.setup()
this.env;this.props}
getExtraContext(props){const context=Object.assign(super.getExtraContext(props),{default_partner_id:props.selectedConversation.partner.id,default_mobile:props.selectedConversation.numberFormat,default_phone:props.selectedConversation.numberFormat,default_name:`${props.selectedConversation.connector.name}: ${props.selectedConversation.name}`,default_contact_name:props.selectedConversation.name,default_user_id:this.env.services.user.userId,})
if(props.selectedConversation.team.id){context['default_team_id']=props.selectedConversation.team.id}
return context}
async onSave(record){await super.onSave(record)
if(record.resId!==this.props.selectedConversation.lead.id){await this.env.services.orm.write(this.env.chatModel,[this.props.selectedConversation.id],{crm_lead_id:record.resId},{context:this.env.context})
this.props.selectedConversation.updateFromJson({crm_lead_id:[record.resId,record.data.display_name]})
this.env.chatBus.trigger('updateConversation',this.props.selectedConversation)}}
_getOnSearchChatroomDomain(){let domain=super._getOnSearchChatroomDomain()
domain.push(['conversation_id','=',this.props.selectedConversation.id])
if(this.props.selectedConversation.partner.id){domain.unshift('|')
domain.push(['partner_id','=',this.props.selectedConversation.partner.id])}
return domain}}
CrmLeadForm.props=Object.assign({},CrmLeadForm.props)
CrmLeadForm.defaultProps=Object.assign({},CrmLeadForm.defaultProps)
patch(CrmLeadForm.props,{selectedConversation:{type:ConversationModel.prototype},viewModel:{type:String,optional:true},viewType:{type:String,optional:true},viewKey:{type:String,optional:true},})
patch(CrmLeadForm.defaultProps,{viewModel:'crm.lead',viewType:'form',viewKey:'crm_form',})
return __exports;});;
