# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Worker Incentive Management + Production Linked Incentive (HRM SRS
sections 38-39; Module 36 SRS section 39) — garment.hr.incentive. Uses the
SRS's own formula: Incentive = Extra Production x Rate. Kept
self-contained (no Many2one into garment_ie_management / garment_production)
since garment_hr is not structurally dependent on those modules — the
production reference is a plain text field, matching the "don't add
cosmetic depends" rule in the house style guide.
"""
from odoo import api, fields, models


class GarmentHrIncentive(models.Model):
    _name = 'garment.hr.incentive'
    _description = 'Garment Worker Production Incentive'
    _inherit = ['mail.thread']
    _order = 'period_end desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    production_reference = fields.Char(string='Production Line / Order Reference')
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)

    target_output = fields.Float(string='Target Output (PCS)', required=True)
    actual_output = fields.Float(string='Actual Output (PCS)', required=True)
    extra_output = fields.Float(string='Extra Production (PCS)', compute='_compute_incentive', store=True)
    rate_per_unit = fields.Monetary(string='Rate per Extra PCS', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    incentive_amount = fields.Monetary(string='Incentive Amount', compute='_compute_incentive', store=True,
                                        currency_field='currency_id')

    payroll_id = fields.Many2one('garment.hr.payroll', string='Included In Payslip',
                                  copy=False, ondelete='set null')
    status = fields.Selection([
        ('draft', 'Draft'), ('approved', 'Approved'), ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('target_output', 'actual_output', 'rate_per_unit')
    def _compute_incentive(self):
        for rec in self:
            extra = max(0.0, (rec.actual_output or 0.0) - (rec.target_output or 0.0))
            rec.extra_output = extra
            rec.incentive_amount = extra * (rec.rate_per_unit or 0.0)

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_mark_paid(self):
        self.write({'status': 'paid'})
