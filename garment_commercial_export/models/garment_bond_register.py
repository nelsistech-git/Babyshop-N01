# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Bond Register (SRS section 28) — garment.bond.register. Material-wise
import/consumption/balance ledger under a Bond License, adjusted against
an export reference (Utilization Declaration / shipment) — the SRS's own
DB design table names this model explicitly."""
from odoo import api, fields, models


class GarmentBondRegister(models.Model):
    _name = 'garment.bond.register'
    _description = 'Garment Bond Register'
    _order = 'material_name'

    bond_license_id = fields.Many2one('garment.bond.license', string='Bond License', required=True,
                                       ondelete='cascade')
    material_id = fields.Many2one('garment.material', string='Material')
    material_name = fields.Char(string='Material Name', required=True)
    uom = fields.Char(string='UOM', default='Meter')

    import_qty = fields.Float(string='Imported Quantity', required=True)
    used_qty = fields.Float(string='Used/Consumed Quantity')
    balance_qty = fields.Float(string='Balance Quantity', compute='_compute_balance_qty', store=True)

    import_permission_id = fields.Many2one('garment.import.permission', string='Import Permission (IP)')
    export_documentation_id = fields.Many2one('garment.export.documentation', string='Export Reference')
    shipment_id = fields.Many2one('garment.shipment', string='Shipment')

    company_id = fields.Many2one('res.company', related='bond_license_id.company_id', store=True)

    @api.depends('import_qty', 'used_qty')
    def _compute_balance_qty(self):
        for rec in self:
            rec.balance_qty = rec.import_qty - rec.used_qty
