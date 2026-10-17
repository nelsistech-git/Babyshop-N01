# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

from .entitlement import AMOUNT_DIGITS


class BondWarehouseEntitlementUtilization(models.Model):
    """Links an entitlement to a validated (done) standard stock move.

    This is NOT an inventory ledger: quantities stay in stock.move/stock.quant.
    The consumed amount is frozen from the move at validation time.
    """
    _name = 'bond.warehouse.entitlement.utilization'
    _description = 'Bond Entitlement Utilization'
    _inherit = ['bond.warehouse.lifecycle.mixin']
    _order = 'id desc'

    _bond_status_transitions = {'reverse': ({'validated'}, 'reversed')}
    _bond_deletable_states = ('draft',)

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    entitlement_id = fields.Many2one('bond.warehouse.entitlement', required=True, ondelete='restrict')
    company_id = fields.Many2one(related='entitlement_id.company_id', store=True, readonly=True)
    license_id = fields.Many2one(related='entitlement_id.license_id', store=True, readonly=True)
    stock_move_id = fields.Many2one('stock.move', string='Validated Stock Move', required=True,
                                    ondelete='restrict', domain="[('state', '=', 'done')]")
    picking_id = fields.Many2one(related='stock_move_id.picking_id', store=True, readonly=True)
    product_id = fields.Many2one(related='stock_move_id.product_id', store=True, readonly=True)
    move_date = fields.Datetime(related='stock_move_id.date', store=True, readonly=True)
    preview_amount = fields.Float(compute='_compute_preview_amount', digits=AMOUNT_DIGITS)
    consumed_amount = fields.Float(readonly=True, copy=False, digits=AMOUNT_DIGITS)
    basis = fields.Selection(related='entitlement_id.basis', store=True, readonly=True)
    exception_used = fields.Boolean(readonly=True, copy=False)
    validated_by_id = fields.Many2one('res.users', readonly=True, copy=False)
    validated_date = fields.Datetime(readonly=True, copy=False)
    note = fields.Text()
    state = fields.Selection([('draft', 'Draft'), ('validated', 'Validated'), ('reversed', 'Reversed')],
                             default='draft', required=True, copy=False)

    def init(self):
        # one non-reversed utilization per stock move across all entitlements
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS bond_utilization_move_active_uniq
            ON bond_warehouse_entitlement_utilization (stock_move_id)
            WHERE state != 'reversed'
        """)

    # -------------------------------------------------------------- compute
    def _amount_from_move(self):
        self.ensure_one()
        ent, move = self.entitlement_id, self.stock_move_id
        if not (ent and move):
            return 0.0
        if ent.basis == 'quantity':
            if not ent.uom_id or ent.uom_id.category_id != move.product_uom.category_id:
                return 0.0
            return move.product_uom._compute_quantity(move.quantity, ent.uom_id)
        qty_product_uom = move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id)
        value = qty_product_uom * abs(move.price_unit)
        if ent.currency_id and move.company_id.currency_id != ent.currency_id:
            value = move.company_id.currency_id._convert(
                value, ent.currency_id, move.company_id,
                fields.Date.context_today(self, move.date) if move.date else fields.Date.today())
        return value

    @api.depends('entitlement_id.basis', 'entitlement_id.uom_id', 'entitlement_id.currency_id',
                 'stock_move_id.quantity', 'stock_move_id.product_uom', 'stock_move_id.price_unit',
                 'state', 'consumed_amount')
    def _compute_preview_amount(self):
        for rec in self:
            rec.preview_amount = rec._amount_from_move() if rec.state == 'draft' else rec.consumed_amount

    # ------------------------------------------------------------------ ORM
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'bond.warehouse.entitlement.utilization') or 'New'
            ent = self.env['bond.warehouse.entitlement'].browse(vals.get('entitlement_id'))
            if ent and ent.state != 'active':
                raise UserError(_('Utilization can only be raised against an active entitlement.'))
            for protected in ('consumed_amount', 'state', 'validated_by_id', 'validated_date', 'exception_used'):
                vals.pop(protected, None)
            if vals.get('stock_move_id') and self.search_count([
                    ('stock_move_id', '=', vals['stock_move_id']), ('state', '!=', 'reversed')]):
                raise ValidationError(_('This stock move is already linked to an entitlement utilization.'))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get('bond_status_change'):
            protected = {'consumed_amount', 'state', 'validated_by_id', 'validated_date', 'exception_used'}
            if protected & set(vals):
                raise UserError(_('Utilization results can only be set through validation.'))
            if any(rec.state != 'draft' for rec in self) and {'entitlement_id', 'stock_move_id'} & set(vals):
                raise UserError(_('Validated utilization cannot be modified. Reverse it instead.'))
        return super().write(vals)

    @api.constrains('stock_move_id', 'state')
    def _check_duplicate_move(self):
        for rec in self:
            if rec.state != 'reversed' and self.search_count([
                    ('stock_move_id', '=', rec.stock_move_id.id), ('state', '!=', 'reversed'),
                    ('id', '!=', rec.id)]):
                raise ValidationError(_('This stock move is already linked to an entitlement utilization.'))

    # -------------------------------------------------------------- actions
    def action_validate(self):
        for rec in self:
            rec._validate_single()
        return True

    def _validate_single(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft utilization can be validated.'))
        ent, move = self.entitlement_id, self.stock_move_id
        # serialise concurrent validations on the same entitlement
        self.env.cr.execute('SELECT id FROM bond_warehouse_entitlement WHERE id = %s FOR UPDATE', (ent.id,))
        ent.invalidate_recordset()
        self.env['bond.warehouse.entitlement.utilization'].flush_model()

        if ent.state != 'active':
            raise UserError(_('The entitlement is not active.'))
        if move.state != 'done':
            raise UserError(_('The stock move must be validated (done) before it can be utilized.'))
        if move.company_id != ent.company_id:
            raise UserError(_('The stock move belongs to a different company.'))
        if self.search_count([('stock_move_id', '=', move.id), ('state', '!=', 'reversed'),
                              ('id', '!=', self.id)]):
            raise UserError(_('This stock move is already utilized against an entitlement.'))
        move_day = fields.Date.context_today(self, move.date)
        if not (ent.effective_from <= move_day <= ent.effective_to):
            raise UserError(_('The stock move date %(d)s is outside the entitlement effective dates.',
                              d=move_day))
        if not (ent.period_from <= move_day <= ent.period_to):
            raise UserError(_('The stock move date %(d)s is outside the entitlement period.', d=move_day))
        lic = ent.license_id
        if not lic._is_valid_on(move_day):
            raise UserError(_('The license %(l)s was not valid on %(d)s.', l=lic.display_name, d=move_day))
        if ent.product_id and move.product_id != ent.product_id:
            raise UserError(_('The stock move product does not match the entitlement product.'))
        if ent.basis == 'quantity' and ent.uom_id.category_id != move.product_uom.category_id:
            raise UserError(_('The move unit of measure is not convertible to the entitlement unit.'))
        if lic.location_ids:
            locations = move.location_id | move.location_dest_id
            if not self.env['stock.location'].search_count([
                    ('id', 'in', locations.ids), ('id', 'child_of', lic.location_ids.ids)]):
                raise UserError(_('Neither the source nor the destination location is an authorized '
                                  'bonded location of the license.'))
        if ent.basis == 'value' and not move.sudo().price_unit:
            raise UserError(_('The stock move has no unit price; a value-based entitlement cannot be applied.'))
        amount = self._amount_from_move()
        if float_compare(amount, 0.0, precision_digits=4) <= 0:
            raise UserError(_('The consumed amount must be greater than zero.'))

        used = sum(self.search([('entitlement_id', '=', ent.id), ('state', '=', 'validated')])
                   .mapped('consumed_amount'))
        exceeds = float_compare(used + amount, ent.approved_total, precision_digits=4) > 0
        if exceeds and not ent.exception_authorized:
            raise UserError(_(
                'Utilization of %(amt)s exceeds the available balance of %(avail)s for %(ent)s. '
                'An authorised exception with legal basis is required.',
                amt=amount, avail=ent.approved_total - used, ent=ent.display_name))
        self.with_context(bond_status_change=True).write({
            'state': 'validated', 'consumed_amount': amount, 'exception_used': exceeds,
            'validated_by_id': self.env.user.id, 'validated_date': fields.Datetime.now()})
        self._log_history('validate', _('Amount %s', amount), 'draft', 'validated')
        ent._log_history('utilization', _('%(n)s: %(a)s%(x)s', n=self.name, a=amount,
                                          x=_(' (EXCEPTION)') if exceeds else ''))

    def action_reverse(self):
        return self._bond_open_wizard('reverse', _('Reverse Utilization'))

    def _bond_before_transition(self, action_code, target):
        if action_code == 'reverse':
            self.entitlement_id._log_history('utilization_reversed', self.name)
        return target
