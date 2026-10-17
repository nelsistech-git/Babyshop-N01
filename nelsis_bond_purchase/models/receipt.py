# -*- coding: utf-8 -*-
from odoo import Command, _, fields, models
from odoo.exceptions import UserError

from odoo.addons.nelsis_lc_management.models.constants import LIVE_STATES


class BondReceipt(models.Model):
    _inherit = 'bond.inventory.receipt'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order',
                                        related='consignment_id.purchase_order_id', store=True, index=True)

    def action_view_purchase_order(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'res_model': 'purchase.order', 'view_mode': 'form',
                'res_id': self.purchase_order_id.id}

    def _bond_lc(self):
        self.ensure_one()
        lc = self.sudo().lc_ref
        if lc and lc._name == 'nelsis.lc':
            return lc
        return self.sudo().purchase_order_id.lc_id

    def _bond_po_line_map(self):
        """{'product:uom': purchase_line_id} for the accepted lines; one purchase line per product / unit."""
        self.ensure_one()
        groups = {}
        for line in self._accepted_lines():
            groups.setdefault((line.product_id.id, line.product_uom_id.id), self.env['bond.inventory.receipt.line'])
            groups[(line.product_id.id, line.product_uom_id.id)] |= line
        mapping = {}
        for (prod, uom), lines in groups.items():
            pols = lines.mapped('purchase_line_id')
            if not pols:
                continue
            if len(pols) > 1 or len(lines.filtered('purchase_line_id')) != len(lines):
                raise UserError(_('Receipt lines of %s must all belong to the same purchase line, or none.',
                                  lines[0].product_id.display_name))
            mapping['%s:%s' % (prod, uom)] = pols.id
        return mapping

    def _bond_picking_refs(self):
        self.ensure_one()
        lc = self._bond_lc()
        ent = self.sudo().purchase_order_id.bond_entitlement_id
        license_ref = ent.license_id.license_number if ent and 'license_id' in ent._fields else False
        license_ref = license_ref or lc.bond_license_ref or self.sudo().location_dest_id.bond_license_ref
        return {'bond_boe_ref': self.boe_number or False,
                'bond_lc_ref': lc.lc_number if lc else (self.lc_number or False),
                'bond_license_ref': license_ref or False,
                'bond_entitlement_ref': ent.reference if ent and 'reference' in ent._fields else False}

    def _post_stock(self):
        self.ensure_one()
        mapping = self._bond_po_line_map()
        receipt = self.with_context(bond_po_line_map=mapping, bond_po_origin=self.name) if mapping else self
        res = super(BondReceipt, receipt)._post_stock()
        self._bond_link_after_post()
        return res

    def _bond_link_after_post(self):
        self.ensure_one()
        picking = self.picking_id.sudo()
        if not picking:
            return
        po = self.sudo().purchase_order_id
        lc = self._bond_lc()
        if lc and lc.state in LIVE_STATES:
            vals = {'lc_id': lc.id}
            ship = self.sudo().consignment_id.lc_shipment_id
            if ship and ship.lc_id == lc:
                vals['lc_shipment_id'] = ship.id
            picking.write(vals)
        elif lc:
            self.message_post(body=_('LC %s is not open: the transfer was not linked to it.', lc.display_name))
        if po:
            if po.commercial_file_id:
                po.commercial_file_id.write({'picking_ids': [Command.link(picking.id)]})
            po.message_post(body=_('Bond receipt %(r)s validated (transfer %(p)s).', r=self.name, p=picking.name))

    def _bond_sync_done_receipt(self):
        """Attach a validated receipt that pre-dates the order link to the purchase lines. Returns changes."""
        self.ensure_one()
        changes = 0
        done_moves = {}
        for line in self._accepted_lines().filtered(lambda l: l.purchase_line_id and l.move_id):
            done_moves.setdefault(line.move_id, set()).add(line.purchase_line_id.id)
        for move, pol_ids in done_moves.items():
            if len(pol_ids) == 1 and not move.purchase_line_id:
                move.sudo().purchase_line_id = list(pol_ids)[0]
                changes += 1
        picking = self.picking_id.sudo()
        po = self.sudo().purchase_order_id
        if picking and po:
            lc = self._bond_lc()
            if lc and lc.state in LIVE_STATES and not picking.lc_id:
                picking.write({'lc_id': lc.id})
                changes += 1
            if po.commercial_file_id and picking not in po.commercial_file_id.picking_ids:
                po.commercial_file_id.write({'picking_ids': [Command.link(picking.id)]})
                changes += 1
            refs = {k: v for k, v in self._bond_picking_refs().items() if v and not picking[k]}
            if refs:
                picking.write(refs)
                changes += 1
        return changes


class BondReceiptLine(models.Model):
    _inherit = 'bond.inventory.receipt.line'

    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase Line',
                                       related='consignment_line_id.purchase_line_id', store=True, index=True)
