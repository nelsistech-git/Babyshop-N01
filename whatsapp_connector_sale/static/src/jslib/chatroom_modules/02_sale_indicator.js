odoo.define('@whatsapp_connector_sale/chatroom_ext/sale-indicator',['@web/views/fields/formatters','@web/core/assets','@odoo/owl'],function(require){'use strict';let __exports={};const{formatMonetary}=require('@web/views/fields/formatters')
const{loadBundle}=require('@web/core/assets')
const{Component,onWillStart,useEffect,useRef,onWillUpdateProps,markup}=require('@odoo/owl')
const SaleIndicator=__exports.SaleIndicator=class SaleIndicator extends Component{setup(){super.setup()
this.env
this.canvasRef=useRef('canvas')
this.monthLastSaleData=null
this.htmlLastSale=null
this.chart=null
onWillStart(this.willStart.bind(this))
onWillUpdateProps(this.onWillUpdateProps.bind(this))
useEffect(()=>{this.renderChart()
return()=>{if(this.chart){this.chart.destroy()}}})}
async willStart(){await this.getPartnerIndicator(this.props)
await loadBundle('web.chartjs_lib')}
async onWillUpdateProps(nextProps){await this.getPartnerIndicator(nextProps)}
async getPartnerIndicator(props){const result=await this.env.services.orm.call('res.partner','get_chat_indicators',[[props.partnerId]],{context:this.env.context},)
if(result['6month_last_sale_data']){this.monthLastSaleData=result['6month_last_sale_data'];}
if(result['html_last_sale']){this.htmlLastSale=markup(result['html_last_sale'])}}
renderChart(){if(this.monthLastSaleData){const config=this._getBarChartConfig()
this.chart=new Chart(this.canvasRef.el,config)}}
_getBarChartConfig(){var data=[]
var backgroundColor=['#FFD8E1','#FFE9D3','#FFF3D6','#D3F5F5','#CDEBFF','#E6D9FF']
var borderColor=['#FF3D67','#FF9124','#FFD36C','#60DCDC','#4CB7FF','#A577FF']
var labels=[]
let data_param=this.monthLastSaleData
data_param[0].values.forEach(pt=>{data.push(pt.value)
labels.push(pt.label)})
return{type:'bar',data:{labels:labels,datasets:[{data:data,fill:'start',label:data_param[0].key,backgroundColor:backgroundColor,borderColor:borderColor,}]},options:{scales:{y:{display:false},},maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{enabled:true,intersect:false,position:'nearest',caretSize:0,callbacks:{label:(tooltipItem)=>{let label=tooltipItem.dataset.label||''
if(label){label+=': '}
label+=formatMonetary(tooltipItem.raw,{currencyId:this.env.getCurrency()})
return label}}},},elements:{line:{tension:0.000001}},},}}}
Object.assign(SaleIndicator,{template:'chatroom.SaleIndicator',props:{partnerId:Number}})
return __exports;});;
