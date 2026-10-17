# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, fields, models, tools
from odoo.exceptions import UserError

from .bond_sql import BOND_CLASSES, MOVE_TYPES, VERIFICATION_STATES, ledger_base_sql


class BondWarehouseLedger(models.Model):
    _name = 'bond.warehouse.ledger'
    _description = 'Bond Stock Ledger (validated stock movements)'
    _auto = False
    _order = 'date desc, id desc'
    _rec_name = 'reference'

    date = fields.Datetime(readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)
    hs_code = fields.Char(string='HS Code', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Batch', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='UoM', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Transfer', readonly=True)
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True)
    move_line_id = fields.Many2one('stock.move.line', string='Move Line', readonly=True)
    reference = fields.Char(readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    counterpart_location_id = fields.Many2one('stock.location', string='Source / Destination', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', readonly=True)
    bond_classification = fields.Selection(BOND_CLASSES, string='Bond Classification', readonly=True)
    side = fields.Selection([('in', 'In'), ('out', 'Out')], readonly=True)
    move_type = fields.Selection(MOVE_TYPES, string='Movement Type', readonly=True)
    qty_in = fields.Float(string='Qty In', readonly=True, digits='Product Unit of Measure')
    qty_out = fields.Float(string='Qty Out', readonly=True, digits='Product Unit of Measure')
    signed_qty = fields.Float(string='Net Qty', readonly=True, digits='Product Unit of Measure')
    company_effect_qty = fields.Float(
        string='Company Stock Effect', readonly=True, digits='Product Unit of Measure',
        help="Net quantity effect on total company stock. Internal transfers are always 0.")
    running_balance = fields.Float(
        string='Running Balance', readonly=True, digits='Product Unit of Measure',
        group_operator='max',
        help="Running balance per product / lot / location over all validated movements.")
    lc_ref = fields.Char(string='LC Reference', readonly=True)
    boe_ref = fields.Char(string='Bill of Entry', readonly=True)
    license_ref = fields.Char(string='License', readonly=True)
    entitlement_ref = fields.Char(string='Entitlement', readonly=True)
    verification_state = fields.Selection(VERIFICATION_STATES, string='Verification', readonly=True)
    adj_approved = fields.Boolean(string='Adjustment Approved', readonly=True)
    processed_by_id = fields.Many2one('res.users', string='Processed By', readonly=True)
    approval_user_id = fields.Many2one('res.users', string='Approved/Verified By', readonly=True)
    approval_date = fields.Datetime(string='Approval Date', readonly=True)
    has_documents = fields.Boolean(string='Has Documents', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    b.row_id AS id,
                    b.date, b.company_id, b.product_id, b.hs_code, b.lot_id,
                    b.product_uom_id, b.picking_id, b.move_id, b.move_line_id,
                    b.reference, b.location_id, b.counterpart_location_id,
                    b.warehouse_id, b.bond_classification, b.side, b.move_type,
                    CASE WHEN b.side = 'in' THEN b.qty ELSE 0 END AS qty_in,
                    CASE WHEN b.side = 'out' THEN b.qty ELSE 0 END AS qty_out,
                    CASE WHEN b.side = 'in' THEN b.qty ELSE -b.qty END AS signed_qty,
                    CASE WHEN b.move_type = 'transfer' THEN 0
                         WHEN b.side = 'in' THEN b.qty ELSE -b.qty END AS company_effect_qty,
                    SUM(CASE WHEN b.side = 'in' THEN b.qty ELSE -b.qty END) OVER (
                        PARTITION BY b.company_id, b.product_id, COALESCE(b.lot_id, 0), b.location_id
                        ORDER BY b.date, b.row_id
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS running_balance,
                    b.lc_ref, b.boe_ref, b.license_ref, b.entitlement_ref,
                    b.verification_state, b.adj_approved, b.processed_by_id,
                    b.approval_user_id, b.approval_date, b.has_documents
                FROM (%s) b
            )
        """ % (self._table, ledger_base_sql()))

    # ------------------------------------------------------------------
    def action_approve_adjustment(self):
        """Approve selected adjustment rows (delegates to stock.move.line)."""
        lines = self.env['stock.move.line'].browse(self.mapped('move_line_id').ids)
        lines.action_bond_approve_adjustment()
        return True

    def action_open_transfer(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("This movement has no transfer (e.g. an inventory adjustment)."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
        }
