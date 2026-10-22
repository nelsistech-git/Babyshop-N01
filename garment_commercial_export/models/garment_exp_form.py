# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""EXP Form Management (SRS section 25) — garment.exp.form. Export
Registration Form workflow: Commercial Officer -> Bank Verification ->
EXP Approval -> Shipment. Distinct from the generic
garment.export.documentation record (which can still hold a scanned copy
via document_type='exp_form_copy') because the EXP Form carries its own
bank-verification workflow rather than a simple draft/issued lifecycle."""
from odoo import api, fields, models, _


class GarmentExpForm(models.Model):
    _name = 'garment.exp.form'
    _description = 'Garment EXP Form (Export Registration Form)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'shipment_date desc'

    exp_number = fields.Char(string='EXP Number', copy=False, readonly=True, default=lambda s: _('New'))
    exporter = fields.Char(string='Exporter', default=lambda s: s.env.company.name)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    export_documentation_id = fields.Many2one('garment.export.documentation', string='Invoice Reference',
                                               domain="[('document_type', '=', 'export_invoice')]")
    shipment_id = fields.Many2one('garment.shipment', string='Shipment', tracking=True)
    lc_id = fields.Many2one('garment.lc', string='LC Reference')

    shipment_date = fields.Date(string='Shipment Date', tracking=True)
    export_value = fields.Monetary(string='Export Value', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    bank_id = fields.Many2one('garment.bank.account', string='Bank')

    workflow_stage = fields.Selection([
        ('commercial_officer', 'Commercial Officer'), ('bank_verification', 'Bank Verification'),
        ('exp_approval', 'EXP Approval'), ('shipment', 'Shipment'),
    ], string='Workflow Stage', default='commercial_officer', tracking=True, group_expand='_expand_states')

    status = fields.Selection([
        ('draft', 'Draft'), ('verified', 'Bank Verified'), ('approved', 'Approved'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('exp_number_uniq', 'unique(exp_number, company_id)', 'EXP Number must be unique per company!'),
    ]

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['workflow_stage'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('exp_number', _('New')) == _('New'):
                vals['exp_number'] = self.env['ir.sequence'].next_by_code('garment.exp.form') or _('New')
        return super().create(vals_list)

    def action_next_stage(self):
        flow = ['commercial_officer', 'bank_verification', 'exp_approval', 'shipment']
        for rec in self:
            idx = flow.index(rec.workflow_stage)
            if idx < len(flow) - 1:
                rec.workflow_stage = flow[idx + 1]
            if rec.workflow_stage == 'bank_verification':
                rec.status = 'verified'
            elif rec.workflow_stage == 'exp_approval':
                rec.status = 'approved'
