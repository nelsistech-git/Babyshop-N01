# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    bond_consignment_line_ids = fields.One2many('bond.inventory.consignment.line', 'purchase_line_id')
    bond_declared_qty = fields.Float('Declared on Consignments', digits='Product Unit of Measure',
                                     compute='_compute_bond_declared')
    bond_uncovered_qty = fields.Float('Not Yet Declared', digits='Product Unit of Measure',
                                      compute='_compute_bond_declared')

    @api.depends('product_qty', 'product_uom', 'bond_consignment_line_ids.declared_qty',
                 'bond_consignment_line_ids.consignment_id.state')
    def _compute_bond_declared(self):
        for line in self:
            declared = 0.0
            if isinstance(line.id, int) and line.product_id:
                for cl in line.sudo().bond_consignment_line_ids.filtered(
                        lambda c: c.consignment_id.state != 'cancelled'):
                    declared += cl.product_uom_id._compute_quantity(cl.declared_qty, line.product_uom)
            line.bond_declared_qty = declared
            line.bond_uncovered_qty = max(line.product_qty - declared, 0.0)

    def _create_or_update_picking(self):
        bonded = self.filtered(lambda l: l.order_id.bond_purchase_type == 'import_bonded')
        for line in bonded:
            if line.product_id and float_compare(line.product_qty, line.qty_received,
                                                 precision_rounding=line.product_uom.rounding) < 0:
                raise UserError(_('You cannot decrease the ordered quantity of %s below the received quantity.',
                                  line.product_id.display_name))
        return super(PurchaseOrderLine, self - bonded)._create_or_update_picking()
