# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Bond Management System — Bond License (SRS section 28) —
garment.bond.license. The bonded-warehouse licence issued by Bangladesh
Customs Bond Commissionerate that the Bond Register lines are consumed
against."""
from odoo import api, fields, models, _


class GarmentBondLicense(models.Model):
    _name = 'garment.bond.license'
    _description = 'Garment Bond License'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'

    license_number = fields.Char(string='Bond License Number', required=True, copy=False, tracking=True)
    license_type = fields.Selection([
        ('general_bond', 'General Bonded Warehouse'), ('special_bond', 'Special Bonded Warehouse'),
        ('back_to_back', 'Back-to-Back Bond'),
    ], string='License Type', default='general_bond', required=True)
    issuing_authority = fields.Char(string='Issuing Authority', default='Bond Commissionerate, Bangladesh Customs')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    bond_value = fields.Monetary(string='Bond Value', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    status = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('renewal_due', 'Renewal Due'),
        ('expired', 'Expired'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    register_ids = fields.One2many('garment.bond.register', 'bond_license_id', string='Bond Register Lines')
    register_count = fields.Integer(compute='_compute_register_totals')
    total_imported_qty = fields.Float(string='Total Imported Qty', compute='_compute_register_totals')
    total_balance_qty = fields.Float(string='Total Balance Qty', compute='_compute_register_totals')

    days_to_expiry = fields.Integer(string='Days to Expiry', compute='_compute_days_to_expiry')
    file = fields.Binary(string='License Copy', attachment=True)
    filename = fields.Char(string='Filename')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('bond_license_number_uniq', 'unique(license_number, company_id)',
         'Bond License Number must be unique per company!'),
    ]

    @api.depends('register_ids.import_qty', 'register_ids.balance_qty')
    def _compute_register_totals(self):
        for rec in self:
            rec.register_count = len(rec.register_ids)
            rec.total_imported_qty = sum(rec.register_ids.mapped('import_qty'))
            rec.total_balance_qty = sum(rec.register_ids.mapped('balance_qty'))

    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_to_expiry = (rec.expiry_date - today).days if rec.expiry_date else 0

    def action_view_register(self):
        self.ensure_one()
        return {'name': _('Bond Register'), 'type': 'ir.actions.act_window', 'res_model': 'garment.bond.register',
                'view_mode': 'tree,form', 'domain': [('bond_license_id', '=', self.id)],
                'context': {'default_bond_license_id': self.id}}
