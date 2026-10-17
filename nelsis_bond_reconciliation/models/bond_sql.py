# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
"""Shared SQL used by the bond ledger, bond register and reconciliation.

The ledger is built ONLY from validated (state = 'done') standard Odoo stock move
lines. No independent balance is stored anywhere in this module.

Every done move line produces up to two ledger rows, one per *internal* location
touched by the movement:
    * 'in'  row  -> destination is an internal location
    * 'out' row  -> source is an internal location
A transfer between two internal locations therefore produces one 'in' and one
'out' row of identical quantity: summed across all internal locations the net
effect on company stock is exactly zero.

Quantities are converted to the product's own unit of measure.
"""

MOVE_TYPES = [
    ('receipt', 'Receipt'),
    ('return_in', 'Return In'),
    ('issue', 'Issue'),
    ('return_out', 'Return Out'),
    ('transfer', 'Transfer'),
    ('adjustment', 'Adjustment'),
]

BOND_CLASSES = [
    ('bonded', 'Bonded'),
    ('non_bonded', 'Non-Bonded'),
    ('none', 'Not Classified'),
]

VERIFICATION_STATES = [
    ('draft', 'Not Submitted'),
    ('pending', 'Pending Verification'),
    ('verified', 'Verified'),
    ('rejected', 'Rejected'),
]


def _side_select(side):
    """Inner select for one side of the movement ('in' or 'out')."""
    if side == 'in':
        loc, cp, offset = 'sml.location_dest_id', 'sml.location_id', 1
    else:
        loc, cp, offset = 'sml.location_id', 'sml.location_dest_id', 0
    return """
        SELECT
            sml.id * 2 + %(offset)s AS row_id,
            sml.id AS move_line_id,
            sml.date AS date,
            sml.company_id AS company_id,
            sml.product_id AS product_id,
            pt.bond_hs_code AS hs_code,
            sml.lot_id AS lot_id,
            pt.uom_id AS product_uom_id,
            sml.picking_id AS picking_id,
            sml.move_id AS move_id,
            COALESCE(sp.name, sm.reference, sm.name) AS reference,
            loc.id AS location_id,
            cp.id AS counterpart_location_id,
            wh.id AS warehouse_id,
            COALESCE(loc.bond_scope_effective, 'none') AS bond_classification,
            '%(side)s' AS side,
            cp.usage AS cp_usage,
            (sm.origin_returned_move_id IS NOT NULL) AS is_return,
            (sml.quantity / NULLIF(lu.factor, 0) * pu.factor) AS qty,
            COALESCE(NULLIF(sp.bond_lc_ref, ''), NULLIF(lot.bond_lc_ref, '')) AS lc_ref,
            COALESCE(NULLIF(sp.bond_boe_ref, ''), NULLIF(lot.bond_boe_ref, '')) AS boe_ref,
            COALESCE(NULLIF(sp.bond_license_ref, ''), NULLIF(lot.bond_license_ref, '')) AS license_ref,
            NULLIF(sp.bond_entitlement_ref, '') AS entitlement_ref,
            COALESCE(sp.bond_verification_state, 'draft') AS pick_verification,
            COALESCE(sml.bond_adj_approved, FALSE) AS adj_approved,
            sml.write_uid AS processed_by_id,
            COALESCE(sp.bond_verified_by, sml.bond_adj_approved_by) AS approval_user_id,
            COALESCE(sp.bond_verified_on, sml.bond_adj_approved_on) AS approval_date,
            (att.cnt IS NOT NULL) AS has_documents
        FROM stock_move_line sml
        JOIN stock_move sm ON sm.id = sml.move_id
        JOIN product_product pp ON pp.id = sml.product_id
        JOIN product_template pt ON pt.id = pp.product_tmpl_id
        JOIN uom_uom pu ON pu.id = pt.uom_id
        JOIN uom_uom lu ON lu.id = sml.product_uom_id
        LEFT JOIN stock_picking sp ON sp.id = sml.picking_id
        LEFT JOIN stock_lot lot ON lot.id = sml.lot_id
        JOIN stock_location loc ON loc.id = %(loc)s
        JOIN stock_location cp ON cp.id = %(cp)s
        LEFT JOIN LATERAL (
            SELECT w.id
              FROM stock_warehouse w
              JOIN stock_location vl ON vl.id = w.view_location_id
             WHERE left(loc.parent_path, length(vl.parent_path)) = vl.parent_path
             LIMIT 1
        ) wh ON TRUE
        LEFT JOIN (
            SELECT res_id, COUNT(*) AS cnt
              FROM ir_attachment
             WHERE res_model = 'stock.picking'
             GROUP BY res_id
        ) att ON att.res_id = sp.id
        WHERE sm.state = 'done'
          AND sml.quantity > 0
          AND loc.usage = 'internal'
    """ % {'offset': offset, 'side': side, 'loc': loc, 'cp': cp}


MOVE_TYPE_CASE = """
    CASE
        WHEN r.is_return AND r.cp_usage NOT IN ('internal', 'transit')
            THEN CASE WHEN r.side = 'in' THEN 'return_in' ELSE 'return_out' END
        WHEN r.cp_usage = 'inventory' THEN 'adjustment'
        WHEN r.cp_usage IN ('internal', 'transit') THEN 'transfer'
        WHEN r.side = 'in'
            THEN CASE WHEN r.cp_usage IN ('customer', 'production')
                      THEN 'return_in' ELSE 'receipt' END
        ELSE CASE WHEN r.cp_usage = 'supplier' THEN 'return_out' ELSE 'issue' END
    END
"""


def ledger_base_sql():
    """Rows (one per internal location side) with classified ``move_type``.

    Columns: row_id, move_line_id, date, company_id, product_id, hs_code, lot_id,
    product_uom_id, picking_id, move_id, reference, location_id,
    counterpart_location_id, warehouse_id, bond_classification, side, qty,
    move_type, lc_ref, boe_ref, license_ref, entitlement_ref, adj_approved,
    processed_by_id, approval_user_id, approval_date, has_documents,
    verification_state.
    """
    return """
        SELECT b.*,
               CASE WHEN b.move_type = 'adjustment'
                    THEN CASE WHEN b.adj_approved THEN 'verified' ELSE 'draft' END
                    ELSE b.pick_verification
               END AS verification_state
          FROM (
            SELECT r.*, %(move_type_case)s AS move_type
              FROM (
                %(in_side)s
                UNION ALL
                %(out_side)s
              ) r
          ) b
    """ % {
        'move_type_case': MOVE_TYPE_CASE,
        'in_side': _side_select('in'),
        'out_side': _side_select('out'),
    }
