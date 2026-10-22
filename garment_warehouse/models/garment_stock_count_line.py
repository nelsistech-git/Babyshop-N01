# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentStockCountLine(models.Model):
    _name = 'garment.stock.count.line'
    _description = 'Garment Stock Count Line'
    _order = 'sequence'

    count_id = fields.Many2one('garment.stock.count', string='Count', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    material_id = fields.Many2one('garment.material', string='Material', required=True)
    location_id = fields.Many2one('garment.location', string='Location',
                                   domain="[('warehouse_id', '=', parent.warehouse_id)]")
    abc_classification = fields.Selection(related='material_id.abc_classification', string='ABC Class', store=True,
                                           readonly=True)
    system_qty = fields.Float(string='System Quantity', help='Filled by "Start Count" from the stock ledger.')
    counted_qty = fields.Float(string='Physical Quantity')
    variance_qty = fields.Float(string='Variance', compute='_compute_variance', store=True)
    currency_id = fields.Many2one(related='material_id.currency_id')
    variance_value = fields.Monetary(string='Variance Value', compute='_compute_variance', store=True,
                                      currency_field='currency_id')
    notes = fields.Char(string='Remarks')

    @api.depends('system_qty', 'counted_qty')
    def _compute_variance(self):
        for rec in self:
            rec.variance_qty = (rec.counted_qty or 0.0) - (rec.system_qty or 0.0)
            rec.variance_value = rec.variance_qty * (rec.material_id.standard_cost or 0.0)

    def _get_system_qty(self):
        self.ensure_one()
        if self.location_id:
            moves = self.env['garment.stock.move'].search([
                ('material_id', '=', self.material_id.id),
                ('location_id', '=', self.location_id.id),
                ('state', '=', 'done'),
            ])
            in_types = ('receipt', 'return', 'adjustment_in', 'transfer_in')
            out_types = ('issue', 'transfer_out', 'adjustment_out')
            qty = sum(m.quantity for m in moves if m.move_type in in_types)
            qty -= sum(m.quantity for m in moves if m.move_type in out_types)
            return qty
        return self.material_id.on_hand_qty
