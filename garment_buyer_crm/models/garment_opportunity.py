# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentOpportunity(models.Model):
    """Buyer Opportunity Management — converts qualified leads into tracked
    business opportunities through the full sales pipeline until Order
    Confirmed or Lost, per the Buyer CRM SRS section 13."""
    _name = 'garment.opportunity'
    _description = 'Garment Buyer Opportunity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, expected_closing_date'

    name = fields.Char(string='Opportunity Name', required=True, tracking=True)
    opportunity_no = fields.Char(string='Opportunity No.', copy=False, readonly=True, default=lambda s: _('New'))

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True, ondelete='cascade')
    buyer_contact_id = fields.Many2one('garment.buyer.contact', string='Buyer Contact',
                                        domain="[('buyer_id', '=', buyer_id)]")
    assigned_merchandiser_id = fields.Many2one('res.users', string='Assigned Merchandiser', tracking=True)
    sales_executive_id = fields.Many2one('res.users', string='Sales Executive')
    marketing_executive_id = fields.Many2one('res.users', string='Marketing Executive')
    department = fields.Char(string='Department')
    lead_source_id = fields.Many2one('garment.lead.source', string='Lead Source')

    stage_id = fields.Many2one('garment.opportunity.stage', string='Opportunity Stage', tracking=True,
                                group_expand='_read_group_stage_ids',
                                default=lambda s: s.env['garment.opportunity.stage'].search([], limit=1).id)
    is_lost = fields.Boolean(string='Lost', default=False, tracking=True)
    lost_reason = fields.Char(string='Lost Reason')

    expected_closing_date = fields.Date(string='Expected Closing Date')
    expected_order_date = fields.Date(string='Expected Order Date')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    probability = fields.Float(string='Probability (%)', default=10.0)
    expected_revenue = fields.Monetary(string='Expected Revenue', currency_field='currency_id')
    estimated_quantity = fields.Integer(string='Estimated Quantity (pcs)')
    estimated_fob_price = fields.Monetary(string='Estimated FOB Price', currency_field='currency_id')
    estimated_order_value = fields.Monetary(string='Estimated Order Value', currency_field='currency_id',
                                             compute='_compute_estimated_order_value', store=True)
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Very High'),
    ], string='Priority', default='1')
    tag_ids = fields.Many2many('garment.crm.tag', string='Tags')
    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')
    branch = fields.Char(string='Branch')

    rfq_ids = fields.One2many('garment.rfq', 'opportunity_id', string='Related RFQs')
    rfq_count = fields.Integer(compute='_compute_rfq_count')
    meeting_ids = fields.One2many('garment.crm.meeting', 'related_opportunity_id', string='Meetings')

    # ------------------------------------------------------------------
    # AI Opportunity Prediction (SRS section 20)
    # ------------------------------------------------------------------
    ai_probability_win = fields.Float(string='AI Probability of Winning (%)', readonly=True)
    ai_expected_margin = fields.Monetary(string='AI Expected Margin', currency_field='currency_id', readonly=True)
    ai_buyer_response_time_days = fields.Integer(string='AI Buyer Response Time (days)', readonly=True)
    ai_expected_po_date = fields.Date(string='AI Expected PO Date', readonly=True)
    ai_suggested_followup_date = fields.Date(string='AI Suggested Follow-up Date', readonly=True)
    ai_suggested_next_action = fields.Char(string='AI Suggested Next Action', readonly=True)
    ai_recommended_sales_executive_id = fields.Many2one('res.users', string='AI Recommended Sales Executive',
                                                          readonly=True)
    ai_similar_historical_orders = fields.Text(string='AI Similar Historical Orders', readonly=True)
    ai_last_insight = fields.Text(string='AI Insight', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('estimated_quantity', 'estimated_fob_price')
    def _compute_estimated_order_value(self):
        for rec in self:
            rec.estimated_order_value = (rec.estimated_quantity or 0) * (rec.estimated_fob_price or 0.0)

    def _compute_rfq_count(self):
        for rec in self:
            rec.rfq_count = len(rec.rfq_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('opportunity_no', _('New')) == _('New'):
                vals['opportunity_no'] = self.env['ir.sequence'].next_by_code('garment.opportunity') or _('New')
        return super().create(vals_list)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return stages.search([], order='sequence')

    def action_mark_won(self):
        won_stage = self.env['garment.opportunity.stage'].search([('is_won_stage', '=', True)], limit=1)
        for rec in self:
            rec.write({'stage_id': won_stage.id, 'is_lost': False, 'probability': 100.0})
            rec.buyer_id.write({'buyer_status': 'confirmed'})

    def action_mark_lost(self):
        lost_stage = self.env['garment.opportunity.stage'].search([('is_lost_stage', '=', True)], limit=1)
        for rec in self:
            rec.write({'stage_id': lost_stage.id or rec.stage_id.id, 'is_lost': True, 'probability': 0.0})
            rec.message_post(body=_('Opportunity marked as Lost.%s') % (
                (' Reason: %s' % rec.lost_reason) if rec.lost_reason else ''))

    def action_view_rfqs(self):
        self.ensure_one()
        return {
            'name': _('RFQs'),
            'type': 'ir.actions.act_window',
            'res_model': 'garment.rfq',
            'view_mode': 'tree,form',
            'domain': [('opportunity_id', '=', self.id)],
            'context': {'default_opportunity_id': self.id, 'default_buyer_id': self.buyer_id.id},
        }

    def action_run_ai_prediction(self):
        """Trigger the AI engine to (re)predict this opportunity's outcome
        (SRS section 20: AI Opportunity Prediction)."""
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            prediction = ai_engine.predict_opportunity(rec)
            prediction['ai_last_run'] = fields.Datetime.now()
            rec.write(prediction)
        return True

    @api.model
    def _cron_notify_high_value_opportunities(self, threshold=None):
        """'Notify managers about high-value opportunities' (SRS section 40)."""
        if threshold is None:
            threshold = float(self.env['ir.config_parameter'].sudo().get_param(
                'garment_buyer_crm.high_value_threshold', 50000))
        opportunities = self.search([
            ('expected_revenue', '>=', threshold),
            ('is_lost', '=', False),
        ])
        managers = self.env.ref('garment_buyer_crm.group_garment_crm_marketing_manager').users
        for opp in opportunities:
            opp.message_post(
                body=_('High-value opportunity "%s" (%s %s) needs management attention.') % (
                    opp.name, opp.expected_revenue, opp.currency_id.name or ''),
                partner_ids=managers.mapped('partner_id').ids,
            )
