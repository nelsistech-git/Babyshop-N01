# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, fields, models, tools

from .bond_sql import BOND_CLASSES, ledger_base_sql


class BondWarehouseRegister(models.Model):
    """Bond register: validated Odoo movements grouped per license / LC / BoE /
    product / lot / location. A read-only SQL view - it is NOT a second ledger."""
    _name = 'bond.warehouse.register'
    _description = 'Bond Register'
    _auto = False
    _order = 'license_ref, lc_ref, boe_ref, product_id, lot_id'
    _rec_name = 'product_id'

    company_id = fields.Many2one('res.company', readonly=True)
    license_ref = fields.Char(string='License', readonly=True)
    lc_ref = fields.Char(string='LC Reference', readonly=True)
    boe_ref = fields.Char(string='Bill of Entry', readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)
    hs_code = fields.Char(string='HS Code', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Batch', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='UoM', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    bond_classification = fields.Selection(BOND_CLASSES, string='Bond Classification', readonly=True)
    received_qty = fields.Float(string='Received', readonly=True, digits='Product Unit of Measure')
    return_in_qty = fields.Float(string='Returned In', readonly=True, digits='Product Unit of Measure')
    issued_qty = fields.Float(string='Issued', readonly=True, digits='Product Unit of Measure')
    return_out_qty = fields.Float(string='Returned Out', readonly=True, digits='Product Unit of Measure')
    transfer_in_qty = fields.Float(string='Transfers In', readonly=True, digits='Product Unit of Measure')
    transfer_out_qty = fields.Float(string='Transfers Out', readonly=True, digits='Product Unit of Measure')
    adjusted_qty = fields.Float(string='Approved Adjustments', readonly=True,
                                digits='Product Unit of Measure')
    unapproved_adjusted_qty = fields.Float(string='Unapproved Adjustments', readonly=True,
                                           digits='Product Unit of Measure')
    balance_qty = fields.Float(string='Balance', readonly=True, digits='Product Unit of Measure',
                               help="All validated movements. Equals the standard Odoo stock "
                                    "quantity at this location for this product/lot.")
    traceable_balance_qty = fields.Float(
        string='Traceable Balance', readonly=True, digits='Product Unit of Measure',
        help="Part of the balance whose LC and Bill of Entry references are both known.")
    untraceable_balance_qty = fields.Float(
        string='Untraceable Balance', readonly=True, digits='Product Unit of Measure',
        help="Part of the balance with a missing LC or Bill of Entry reference.")
    first_receipt_date = fields.Datetime(readonly=True)
    last_move_date = fields.Datetime(string='Last Movement', readonly=True)
    receipt_refs = fields.Char(string='Receipt References', readonly=True)
    movement_count = fields.Integer(string='Movements', readonly=True)
    picking_count = fields.Integer(string='Transfers', readonly=True)
    document_missing_count = fields.Integer(string='Transfers Without Documents', readonly=True)
    verification_state = fields.Selection(
        [('verified', 'Verified'), ('pending', 'Unverified'), ('rejected', 'Has Rejected')],
        string='Verification', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY l.company_id, l.license_ref, l.lc_ref,
                                       l.boe_ref, l.product_id, l.lot_id, l.location_id) AS id,
                    l.company_id, l.license_ref, l.lc_ref, l.boe_ref, l.product_id,
                    l.hs_code, l.lot_id, l.product_uom_id, l.warehouse_id, l.location_id,
                    l.bond_classification,
                    SUM(CASE WHEN l.move_type = 'receipt' THEN l.qty ELSE 0 END) AS received_qty,
                    SUM(CASE WHEN l.move_type = 'return_in' THEN l.qty ELSE 0 END) AS return_in_qty,
                    SUM(CASE WHEN l.move_type = 'issue' THEN l.qty ELSE 0 END) AS issued_qty,
                    SUM(CASE WHEN l.move_type = 'return_out' THEN l.qty ELSE 0 END) AS return_out_qty,
                    SUM(CASE WHEN l.move_type = 'transfer' AND l.side = 'in' THEN l.qty ELSE 0 END) AS transfer_in_qty,
                    SUM(CASE WHEN l.move_type = 'transfer' AND l.side = 'out' THEN l.qty ELSE 0 END) AS transfer_out_qty,
                    SUM(CASE WHEN l.move_type = 'adjustment' AND l.adj_approved
                             THEN CASE WHEN l.side = 'in' THEN l.qty ELSE -l.qty END ELSE 0 END) AS adjusted_qty,
                    SUM(CASE WHEN l.move_type = 'adjustment' AND NOT l.adj_approved
                             THEN CASE WHEN l.side = 'in' THEN l.qty ELSE -l.qty END ELSE 0 END) AS unapproved_adjusted_qty,
                    SUM(CASE WHEN l.side = 'in' THEN l.qty ELSE -l.qty END) AS balance_qty,
                    SUM(CASE WHEN l.lc_ref IS NOT NULL AND l.boe_ref IS NOT NULL
                             THEN CASE WHEN l.side = 'in' THEN l.qty ELSE -l.qty END ELSE 0 END) AS traceable_balance_qty,
                    SUM(CASE WHEN l.lc_ref IS NULL OR l.boe_ref IS NULL
                             THEN CASE WHEN l.side = 'in' THEN l.qty ELSE -l.qty END ELSE 0 END) AS untraceable_balance_qty,
                    MIN(CASE WHEN l.move_type = 'receipt' THEN l.date END) AS first_receipt_date,
                    MAX(l.date) AS last_move_date,
                    STRING_AGG(DISTINCT CASE WHEN l.move_type = 'receipt' THEN l.reference END, ', ') AS receipt_refs,
                    COUNT(DISTINCT l.move_line_id) AS movement_count,
                    COUNT(DISTINCT l.picking_id) AS picking_count,
                    COUNT(DISTINCT l.picking_id) FILTER (WHERE l.picking_id IS NOT NULL AND NOT l.has_documents) AS document_missing_count,
                    CASE WHEN BOOL_OR(l.verification_state = 'rejected') THEN 'rejected'
                         WHEN BOOL_AND(l.verification_state = 'verified') THEN 'verified'
                         ELSE 'pending' END AS verification_state
                FROM (%s) l
                GROUP BY l.company_id, l.license_ref, l.lc_ref, l.boe_ref, l.product_id,
                         l.hs_code, l.lot_id, l.product_uom_id, l.warehouse_id,
                         l.location_id, l.bond_classification
            )
        """ % (self._table, ledger_base_sql()))

    # ------------------------------------------------------------------
    def action_view_ledger(self):
        self.ensure_one()
        domain = [
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', self.location_id.id),
            ('lot_id', '=', self.lot_id.id or False),
            ('lc_ref', '=', self.lc_ref or False),
            ('boe_ref', '=', self.boe_ref or False),
            ('license_ref', '=', self.license_ref or False),
        ]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Ledger: %s', self.product_id.display_name),
            'res_model': 'bond.warehouse.ledger',
            'view_mode': 'tree,pivot,graph',
            'domain': domain,
        }
