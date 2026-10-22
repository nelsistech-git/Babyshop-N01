# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Maintenance Supplier / External Service Provider Management (Maintenance
& Asset Mgmt SRS sec. 26-27) and AMC / Maintenance Contract Management
(CMMS SRS sec. 31-32). The Service Provider / Calibration Company /
Machine Vendor master is NOT re-modeled — this reuses the existing
``garment.supplier`` (garment_supplier, ``supplier_type='service'``).
This model only tracks the AMC/contract terms and links back to the
shared supplier and equipment records. See IMPLEMENTATION_NOTES.md.
"""
from odoo import api, fields, models, _


class GarmentMaintenanceContract(models.Model):
    _name = 'garment.maintenance.contract'
    _description = 'Garment Maintenance AMC / Service Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'end_date'

    name = fields.Char(string='Contract No.', copy=False, readonly=True, default=lambda s: _('New'))
    vendor_id = fields.Many2one('garment.supplier', string='Vendor', required=True, tracking=True)
    equipment_type = fields.Selection([
        ('machine', 'Production Machine'),
        ('asset', 'Other Asset'),
    ], string='Equipment Type', default='machine', required=True)
    machine_id = fields.Many2one('garment.production.machine', string='Machine')
    asset_id = fields.Many2one('garment.asset', string='Asset')

    service_frequency = fields.Selection([
        ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('half_yearly', 'Half-Yearly'), ('yearly', 'Yearly'),
    ], string='Service Frequency', required=True, default='quarterly')
    coverage = fields.Text(string='Coverage')
    start_date = fields.Date(string='Contract Start Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='Contract End Date', required=True, tracking=True)
    cost = fields.Monetary(string='Contract Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    workorder_ids = fields.One2many('garment.maintenance.workorder', 'contract_id', string='Service Work Orders')
    workorder_count = fields.Integer(compute='_compute_workorder_count')

    status = fields.Selection([
        ('active', 'Active'), ('terminated', 'Terminated'),
    ], string='Status', default='active', tracking=True)
    is_expired = fields.Boolean(string='Expired', compute='_compute_expiry_flags', store=True)
    is_expiring_soon = fields.Boolean(string='Expiring Soon', compute='_compute_expiry_flags', store=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('workorder_ids')
    def _compute_workorder_count(self):
        for rec in self:
            rec.workorder_count = len(rec.workorder_ids)

    @api.depends('end_date')
    def _compute_expiry_flags(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_expired = bool(rec.end_date and rec.end_date < today)
            rec.is_expiring_soon = bool(rec.end_date and today <= rec.end_date and (rec.end_date - today).days <= 30)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.maintenance.contract') or _('New')
        return super().create(vals_list)

    def action_terminate(self):
        self.write({'status': 'terminated'})
