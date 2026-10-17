# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import fields, models, tools


class BondStockReport(models.Model):
    """Read-only SQL view over stock.quant. It never stores a balance of its own."""
    _name = 'bond.inventory.stock.report'
    _description = 'Bond Stock Report'
    _auto = False
    _rec_name = 'product_id'
    _order = 'location_id, product_id, lot_id'

    company_id = fields.Many2one('res.company', readonly=True)
    location_id = fields.Many2one('stock.location', readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot / Batch', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', readonly=True)
    quantity = fields.Float(readonly=True, digits='Product Unit of Measure')
    reserved_quantity = fields.Float(readonly=True, digits='Product Unit of Measure')
    available_quantity = fields.Float(readonly=True, digits='Product Unit of Measure')
    bond_status = fields.Selection([('non_bonded', 'Non-Bonded'), ('bonded', 'Bonded')], readonly=True)
    lc_label = fields.Char(string='LC', readonly=True)
    boe_number = fields.Char(string='Bill of Entry No.', readonly=True)
    consignment_id = fields.Many2one('bond.inventory.consignment', readonly=True)
    receipt_id = fields.Many2one('bond.inventory.receipt', string='Origin Receipt', readonly=True)
    hs_code = fields.Char(string='HS Code', readonly=True)
    expiry_date = fields.Date(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT q.id AS id,
                       q.company_id AS company_id,
                       q.location_id AS location_id,
                       q.product_id AS product_id,
                       q.lot_id AS lot_id,
                       pt.uom_id AS uom_id,
                       q.quantity AS quantity,
                       q.reserved_quantity AS reserved_quantity,
                       (q.quantity - q.reserved_quantity) AS available_quantity,
                       l.bond_status AS bond_status,
                       lot.bond_lc_label AS lc_label,
                       lot.bond_boe_number AS boe_number,
                       lot.bond_consignment_id AS consignment_id,
                       lot.bond_receipt_id AS receipt_id,
                       lot.bond_hs_code AS hs_code,
                       lot.bond_expiry_date AS expiry_date
                  FROM stock_quant q
                  JOIN stock_location l ON l.id = q.location_id AND l.usage = 'internal'
                  JOIN product_product pp ON pp.id = q.product_id
                  JOIN product_template pt ON pt.id = pp.product_tmpl_id
             LEFT JOIN stock_lot lot ON lot.id = q.lot_id
            )
        """ % self._table)
