# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

AMOUNT_DIGITS = (16, 4)


class BondWarehouseEntitlement(models.Model):
    _name = 'bond.warehouse.entitlement'
    _description = 'Bond Warehouse Entitlement'
    _inherit = ['bond.warehouse.lifecycle.mixin', 'bond.warehouse.expiry.mixin',
                'bond.warehouse.rule.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'effective_to desc, id desc'

    _bond_status_transitions = {
        'close': ({'active', 'expired'}, 'closed'),
        'cancel': ({'draft', 'active'}, 'cancelled'),
    }
    _bond_expiry_field = 'effective_to'
    _bond_active_states = ('active',)
    _LOCKED_FIELDS = ('reference', 'license_id', 'product_id', 'hs_code', 'basis', 'uom_id',
                      'currency_id', 'original_amount', 'period_from', 'period_to',
                      'effective_from', 'effective_to', 'approval_reference')
    _EXCEPTION_FIELDS = ('exception_authorized', 'exception_reference', 'exception_basis')

    name = fields.Char(string='Internal Number', required=True, copy=False, readonly=True, default='New')
    reference = fields.Char(string='Entitlement Reference', required=True, tracking=True)
    license_id = fields.Many2one('bond.warehouse.license', string='License', required=True,
                                 ondelete='restrict', tracking=True)
    company_id = fields.Many2one(related='license_id.company_id', store=True, readonly=True)
    period_from = fields.Date(string='Period From', required=True)
    period_to = fields.Date(string='Period To', required=True)
    effective_from = fields.Date(required=True, tracking=True)
    effective_to = fields.Date(required=True, tracking=True)
    original_effective_to = fields.Date(readonly=True, copy=False)
    product_id = fields.Many2one('product.product', string='Product / Material')
    product_description = fields.Char(string='Material Description')
    hs_code = fields.Char(string='HS Code')
    eligibility_note = fields.Text(string='Bonded Eligibility Note')
    basis = fields.Selection([('quantity', 'Quantity'), ('value', 'Value')], required=True,
                             default='quantity')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    currency_id = fields.Many2one('res.currency', string='Currency')
    original_amount = fields.Float(string='Approved Amount (Original)', digits=AMOUNT_DIGITS,
                                   required=True, tracking=True)
    approval_reference = fields.Char(string='Approval Reference')
    approval_date = fields.Date()
    attachment_ids = fields.Many2many('ir.attachment', 'bond_entitlement_attachment_rel',
                                      'entitlement_id', 'attachment_id', string='Supporting Documents')
    note = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired'),
        ('closed', 'Closed'), ('cancelled', 'Cancelled'),
    ], default='draft', required=True, copy=False, tracking=True)

    # calculated (read-only) balances
    amendment_ids = fields.One2many('bond.warehouse.entitlement.amendment', 'entitlement_id')
    utilization_ids = fields.One2many('bond.warehouse.entitlement.utilization', 'entitlement_id')
    amended_total = fields.Float(compute='_compute_approved_total', store=True, digits=AMOUNT_DIGITS,
                                 inverse='_inverse_locked')
    approved_total = fields.Float(string='Current Approved Amount', compute='_compute_approved_total',
                                  store=True, digits=AMOUNT_DIGITS, inverse='_inverse_locked')
    used_amount = fields.Float(compute='_compute_used', store=True, digits=AMOUNT_DIGITS,
                               inverse='_inverse_locked')
    available_amount = fields.Float(compute='_compute_used', store=True, digits=AMOUNT_DIGITS,
                                    inverse='_inverse_locked')
    utilization_percent = fields.Float(compute='_compute_used', store=True, inverse='_inverse_locked')
    over_utilized = fields.Boolean(compute='_compute_used', store=True, inverse='_inverse_locked')
    unit_label = fields.Char(compute='_compute_unit_label')
    amendment_count = fields.Integer(compute='_compute_counts')
    utilization_count = fields.Integer(compute='_compute_counts')
    days_to_expiry = fields.Integer(compute='_compute_days_to_expiry')

    # exception (legally permitted over-utilization) - manager only
    exception_authorized = fields.Boolean(string='Over-utilization Exception Authorized', copy=False)
    exception_reference = fields.Char(string='Exception Authority Reference', copy=False)
    exception_basis = fields.Text(string='Legal Basis for Exception', copy=False)
    exception_authorized_by_id = fields.Many2one('res.users', readonly=True, copy=False)
    exception_date = fields.Date(readonly=True, copy=False)

    _sql_constraints = [
        ('reference_license_uniq', 'unique(license_id, reference)',
         'This entitlement reference already exists for the license.'),
    ]

    # -------------------------------------------------------------- compute
    @api.depends('name', 'reference')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s [%s]' % (rec.name, rec.reference) if rec.reference else rec.name

    @api.depends('original_amount', 'amendment_ids.state', 'amendment_ids.change_amount')
    def _compute_approved_total(self):
        for rec in self:
            amended = sum(rec.amendment_ids.filtered(lambda a: a.state == 'approved').mapped('change_amount'))
            rec.amended_total = amended
            rec.approved_total = rec.original_amount + amended

    @api.depends('approved_total', 'utilization_ids.consumed_amount', 'utilization_ids.state')
    def _compute_used(self):
        for rec in self:
            used = sum(rec.utilization_ids.filtered(lambda l: l.state == 'validated').mapped('consumed_amount'))
            rec.used_amount = used
            rec.available_amount = rec.approved_total - used
            rec.utilization_percent = (used / rec.approved_total * 100.0) if rec.approved_total else 0.0
            rec.over_utilized = rec.available_amount < 0

    def _inverse_locked(self):
        raise UserError(_('Calculated balances cannot be edited directly.'))

    @api.depends('basis', 'uom_id', 'currency_id')
    def _compute_unit_label(self):
        for rec in self:
            rec.unit_label = rec.uom_id.name if rec.basis == 'quantity' else rec.currency_id.name

    @api.depends('amendment_ids', 'utilization_ids')
    def _compute_counts(self):
        for rec in self:
            rec.amendment_count = len(rec.amendment_ids)
            rec.utilization_count = len(rec.utilization_ids)

    @api.depends('effective_to')
    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_to_expiry = (rec.effective_to - today).days if rec.effective_to else 0

    # ---------------------------------------------------------- constraints
    @api.constrains('period_from', 'period_to', 'effective_from', 'effective_to')
    def _check_dates(self):
        for rec in self:
            if rec.period_from > rec.period_to:
                raise ValidationError(_('Period From cannot be after Period To.'))
            if rec.effective_from > rec.effective_to:
                raise ValidationError(_('Effective From cannot be after Effective To.'))

    @api.constrains('original_amount')
    def _check_original_amount(self):
        for rec in self:
            if rec.original_amount <= 0:
                raise ValidationError(_('The approved amount must be greater than zero.'))

    @api.constrains('exception_authorized', 'exception_reference', 'exception_basis')
    def _check_exception(self):
        for rec in self:
            if rec.exception_authorized and not (rec.exception_reference and rec.exception_basis):
                raise ValidationError(_('An exception requires the authority reference and its legal basis.'))

    # ------------------------------------------------------------------ ORM
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bond.warehouse.entitlement') or 'New'
            if any(f in vals for f in self._EXCEPTION_FIELDS):
                self._bond_require_manager()
        return super().create(vals_list)

    def write(self, vals):
        if any(rec.state != 'draft' for rec in self):
            locked = [f for f in self._LOCKED_FIELDS if f in vals]
            if 'effective_to' in locked and self.env.context.get('bond_amendment'):
                locked.remove('effective_to')
            if locked:
                raise UserError(_('Original entitlement values are locked once activated. '
                                  'Use an approved amendment to change them.'))
        if any(f in vals for f in self._EXCEPTION_FIELDS):
            self._bond_require_manager()
            if 'exception_authorized' in vals:
                if vals['exception_authorized']:
                    vals = dict(vals, exception_authorized_by_id=self.env.user.id,
                                exception_date=fields.Date.context_today(self))
                else:
                    vals = dict(vals, exception_authorized_by_id=False, exception_date=False)
        return super().write(vals)

    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault('reference', _('%s (copy)', self.reference))
        return super().copy(default)

    def _bond_responsible_user(self):
        self.ensure_one()
        return self.license_id.responsible_id or self.create_uid

    # -------------------------------------------------------------- actions
    def action_activate(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft entitlements can be activated.'))
            missing = []
            if not rec.hs_code:
                missing.append(_('HS Code'))
            if not rec.approval_reference:
                missing.append(_('Approval Reference'))
            if rec.basis == 'quantity' and not rec.uom_id:
                missing.append(_('Unit of Measure'))
            if rec.basis == 'value' and not rec.currency_id:
                missing.append(_('Currency'))
            if not (rec.product_id or rec.product_description):
                missing.append(_('Product / Material'))
            if missing:
                raise UserError(_('Missing required values: %s', ', '.join(missing)))
            if rec.license_id.state != 'active':
                raise UserError(_('The linked license must be active.'))
            if rec.effective_to < fields.Date.context_today(rec):
                raise UserError(_('An entitlement whose effective period has ended cannot be activated.'))
            rec._bond_check_rule_verified()
            rec.with_context(bond_status_change=True).write({
                'state': 'active', 'original_effective_to': rec.effective_to})
            rec._log_history('activate', from_state='draft', to_state='active')
        return True

    def action_close(self):
        return self._bond_open_wizard('close', _('Close Entitlement'))

    def action_cancel(self):
        return self._bond_open_wizard('cancel', _('Cancel Entitlement'))

    def _bond_before_transition(self, action_code, target):
        if action_code == 'cancel' and self.utilization_ids.filtered(lambda l: l.state == 'validated'):
            raise UserError(_('An entitlement with validated utilization cannot be cancelled. Close it instead.'))
        return target

    def _action_view(self, model, name):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': name, 'res_model': model,
            'view_mode': 'tree,form', 'domain': [('entitlement_id', '=', self.id)],
            'context': {'default_entitlement_id': self.id},
        }

    def action_view_amendments(self):
        return self._action_view('bond.warehouse.entitlement.amendment', _('Amendments'))

    def action_view_utilizations(self):
        return self._action_view('bond.warehouse.entitlement.utilization', _('Utilizations'))
