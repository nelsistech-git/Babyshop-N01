# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    bond_receipt_id = fields.Many2one(
        'bond.inventory.receipt', string='Bond Receipt', readonly=True, copy=False, index=True,
        ondelete='restrict')

    def button_validate(self):
        if not self.env.context.get('bond_receipt_validate'):
            controlled = self.filtered('bond_receipt_id')
            if controlled:
                raise UserError(_(
                    'Transfer %s belongs to a bond receipt and can only be validated from the receipt '
                    'workflow.', controlled[0].name))
        return super().button_validate()

    def action_cancel(self):
        if not self.env.context.get('bond_receipt_cancel'):
            controlled = self.filtered('bond_receipt_id')
            if controlled:
                raise UserError(_(
                    'Transfer %s belongs to a bond receipt and can only be cancelled from the receipt '
                    'workflow.', controlled[0].name))
        return super().action_cancel()


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _action_done(self):
        self._bond_check_location_rules()
        return super()._action_done()

    def _bond_check_location_rules(self):
        """Guard bonded / non-bonded separation for every posted stock movement.

        * Bonded locations accept only bond-eligible products in bonded lots, and only via a bond
          receipt, a transfer from another bonded location, or an explicitly approved context
          (``bond_allow_inbound`` for future approved return / adjustment addons).
        * Bonded stock may not move into a non-bonded internal location (``bond_allow_debond``
          is reserved for a future approved de-bonding workflow).
        """
        for line in self:
            rounding = line.product_uom_id.rounding or 0.01
            if float_compare(line.quantity, 0.0, precision_rounding=rounding) <= 0:
                continue
            src, dest, lot = line.location_id, line.location_dest_id, line.lot_id
            if dest.usage != 'internal':
                continue
            if dest.bond_status == 'bonded':
                line._bond_check_inbound()
            else:
                if lot and lot.bond_status == 'bonded':
                    raise UserError(_(
                        'Bonded lot %(lot)s cannot be moved into the non-bonded location %(loc)s.',
                        lot=lot.name, loc=dest.display_name))
                if (src.usage == 'internal' and src.bond_status == 'bonded'
                        and not self.env.context.get('bond_allow_debond')):
                    raise UserError(_(
                        'Stock cannot leave bonded location %(src)s for the non-bonded location %(dest)s '
                        'without an approved de-bonding process.',
                        src=src.display_name, dest=dest.display_name))

    def _bond_check_inbound(self):
        self.ensure_one()
        product, dest, lot, src = self.product_id, self.location_dest_id, self.lot_id, self.location_id
        if not product.product_tmpl_id.bond_eligible:
            raise UserError(_('Product "%(product)s" is not bond-eligible and cannot enter bonded '
                              'location %(loc)s.', product=product.display_name, loc=dest.display_name))
        if not dest._bond_is_authorized():
            raise UserError(_('Location %s is not bond-authorized (license missing, not yet valid or '
                              'expired).', dest.display_name))
        if lot and lot.bond_status != 'bonded':
            raise UserError(_('Non-bonded lot %(lot)s cannot enter bonded location %(loc)s.',
                              lot=lot.name, loc=dest.display_name))
        receipt = self.picking_id.bond_receipt_id
        if receipt:
            if receipt.bond_status != 'bonded':
                raise UserError(_('Non-bonded receipt %s cannot post into a bonded location.', receipt.name))
            return
        if src.usage == 'internal' and src.bond_status == 'bonded':
            return
        if self.env.context.get('bond_allow_inbound'):
            return
        raise UserError(_(
            'Stock can enter bonded location %s only through a verified bond receipt or a transfer '
            'from another bonded location.', dest.display_name))
