# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Utilization Permission / Utilization Declaration (UP/UD) Management
(SRS section 27) — garment.utilization.declaration. Tracks consumption of
imported (bonded) material against production and the export shipment it
was used for — the document Bangladesh Customs requires to adjust the
Bond Register after shipment. The SRS's DB design table names the
technical model ``garment.utilization.permission``; this module uses the
"Utilization Declaration (UD)" terminology in common Bangladesh customs
usage for the same document (see IMPLEMENTATION_NOTES.md)."""
from odoo import api, fields, models, _


class GarmentUtilizationDeclaration(models.Model):
    _name = 'garment.utilization.declaration'
    _description = 'Garment Utilization Declaration (UD/UP)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'declaration_date desc'

    ud_number = fields.Char(string='UD Number', copy=False, readonly=True, default=lambda s: _('New'))
    import_permission_id = fields.Many2one('garment.import.permission', string='Import Permission (IP)',
                                            required=True, tracking=True)
    imported_quantity = fields.Float(string='Imported Quantity', related='import_permission_id.quantity',
                                      store=True)
    consumed_qty = fields.Float(string='Consumed Quantity', required=True, tracking=True)
    remaining_quantity = fields.Float(string='Remaining Quantity (After This UD)', compute='_compute_remaining',
                                       store=True)

    production_reference = fields.Char(string='Production Order Reference')
    export_documentation_id = fields.Many2one('garment.export.documentation', string='Export Reference')
    shipment_id = fields.Many2one('garment.shipment', string='Export Shipment')

    declaration_date = fields.Date(string='Declaration Date', default=fields.Date.context_today)
    status = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted to Customs'), ('accepted', 'Accepted'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('ud_number_uniq', 'unique(ud_number, company_id)', 'UD Number must be unique per company!'),
    ]

    @api.depends('import_permission_id.quantity', 'import_permission_id.ud_ids.consumed_qty')
    def _compute_remaining(self):
        for rec in self:
            ip = rec.import_permission_id
            if not ip:
                rec.remaining_quantity = 0
                continue
            total_consumed = sum(ip.ud_ids.mapped('consumed_qty'))
            rec.remaining_quantity = ip.quantity - total_consumed

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ud_number', _('New')) == _('New'):
                vals['ud_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.utilization.declaration') or _('New')
        return super().create(vals_list)
