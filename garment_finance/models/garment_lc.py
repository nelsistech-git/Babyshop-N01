# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
LC (Letter of Credit) Master + Workflow + Amendment Management (SRS
sections 22-25) — garment.lc. The single most garment-export-specific
piece of this module: manages the complete export LC lifecycle from
buyer order confirmation to payment realization.
"""
from odoo import api, fields, models, _


class GarmentLc(models.Model):
    _name = 'garment.lc'
    _description = 'Garment Letter of Credit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc'

    lc_number = fields.Char(string='LC Number', required=True, copy=False)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    order_confirmation_id = fields.Many2one('garment.merch.order.confirmation', string='Export Order')
    bank_id = fields.Many2one('garment.bank.account', string='Advising/Negotiating Bank')
    lc_amount = fields.Monetary(string='LC Amount', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    shipment_deadline = fields.Date(string='Shipment Deadline', tracking=True)
    payment_terms = fields.Char(string='Payment Terms')

    workflow_stage = fields.Selection([
        ('buyer_order', 'Buyer Order'), ('lc_received', 'LC Received'), ('lc_verification', 'LC Verification'),
        ('bank_approval', 'Bank Approval'), ('material_procurement', 'Material Procurement'),
        ('production', 'Production'), ('shipment', 'Shipment'), ('export_documents', 'Export Documents'),
        ('payment_received', 'Payment Received'),
    ], string='Workflow Stage', default='buyer_order', tracking=True, group_expand='_expand_states')

    status = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('utilized', 'Utilized'),
        ('expired', 'Expired'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    amendment_count = fields.Integer(string='Amendment Count', default=0)
    document_ids = fields.One2many('garment.lc.document', 'lc_id', string='Documents')
    document_count = fields.Integer(compute='_compute_document_count')

    ai_realization_risk_note = fields.Text(string='AI Realization Risk', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('lc_number_uniq', 'unique(lc_number, company_id)', 'LC Number must be unique per company!'),
    ]

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['workflow_stage'].selection]

    def action_next_stage(self):
        flow = ['buyer_order', 'lc_received', 'lc_verification', 'bank_approval', 'material_procurement',
                'production', 'shipment', 'export_documents', 'payment_received']
        for rec in self:
            idx = flow.index(rec.workflow_stage)
            if idx < len(flow) - 1:
                rec.workflow_stage = flow[idx + 1]
            if rec.workflow_stage == 'payment_received':
                rec.status = 'utilized'

    def action_record_amendment(self):
        """LC Amendment Management (SRS section 25)."""
        self.write({'amendment_count': self.amendment_count + 1})
        for rec in self:
            rec.message_post(body=_('LC amendment #%s recorded.') % rec.amendment_count)

    def action_run_ai_analysis(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            note = ai_engine.predict_lc_realization_risk(rec)
            rec.write({'ai_realization_risk_note': note, 'ai_last_run': fields.Datetime.now()})
        return True
