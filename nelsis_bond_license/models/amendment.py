# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .entitlement import AMOUNT_DIGITS


class BondWarehouseEntitlementAmendment(models.Model):
    _name = 'bond.warehouse.entitlement.amendment'
    _description = 'Bond Entitlement Amendment'
    _inherit = ['bond.warehouse.lifecycle.mixin', 'mail.thread']
    _order = 'id desc'

    _bond_status_transitions = {'reject': ({'draft'}, 'rejected')}

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    entitlement_id = fields.Many2one('bond.warehouse.entitlement', required=True, ondelete='restrict',
                                     tracking=True)
    company_id = fields.Many2one(related='entitlement_id.company_id', store=True, readonly=True)
    amendment_date = fields.Date(default=fields.Date.context_today, required=True)
    approval_reference = fields.Char(string='Authority Approval Reference', required=True)
    reason = fields.Text(required=True)
    change_amount = fields.Float(string='Change in Approved Amount (+/-)', digits=AMOUNT_DIGITS)
    new_effective_to = fields.Date(string='New Effective To')
    previous_total = fields.Float(readonly=True, copy=False, digits=AMOUNT_DIGITS)
    new_total = fields.Float(readonly=True, copy=False, digits=AMOUNT_DIGITS)
    previous_effective_to = fields.Date(readonly=True, copy=False)
    approved_by_id = fields.Many2one('res.users', readonly=True, copy=False)
    approved_date = fields.Date(readonly=True, copy=False)
    attachment_ids = fields.Many2many('ir.attachment', 'bond_amendment_attachment_rel', 'amendment_id',
                                      'attachment_id', string='Supporting Documents')
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                             default='draft', required=True, copy=False, tracking=True)

    @api.constrains('change_amount', 'new_effective_to')
    def _check_content(self):
        for rec in self:
            if not rec.change_amount and not rec.new_effective_to:
                raise ValidationError(_('An amendment must change the amount or the effective end date.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'bond.warehouse.entitlement.amendment') or 'New'
            ent = self.env['bond.warehouse.entitlement'].browse(vals.get('entitlement_id'))
            if ent and ent.state not in ('active', 'expired'):
                raise UserError(_('Amendments can only be raised for active or expired entitlements.'))
        return super().create(vals_list)

    def write(self, vals):
        if any(rec.state != 'draft' for rec in self) and not self.env.context.get('bond_status_change'):
            raise UserError(_('Approved or rejected amendments cannot be modified.'))
        return super().write(vals)

    def action_approve(self):
        self._bond_require_manager()
        today = fields.Date.context_today(self)
        for rec in self:
            ent = rec.entitlement_id
            if rec.state != 'draft':
                raise UserError(_('Only draft amendments can be approved.'))
            if ent.state not in ('active', 'expired'):
                raise UserError(_('The entitlement must be active or expired.'))
            new_total = ent.approved_total + rec.change_amount
            if new_total <= 0:
                raise UserError(_('The amended approved amount must stay above zero.'))
            if new_total < ent.used_amount:
                raise UserError(_('The amended approved amount (%(new)s) cannot be lower than the amount '
                                  'already utilized (%(used)s).', new=new_total, used=ent.used_amount))
            previous_effective_to = ent.effective_to
            if rec.new_effective_to:
                if rec.new_effective_to < ent.effective_from:
                    raise UserError(_('The new effective end date cannot precede the effective start date.'))
                ent.with_context(bond_amendment=True).write({'effective_to': rec.new_effective_to})
                if ent.state == 'expired' and rec.new_effective_to >= today:
                    ent.with_context(bond_status_change=True).write({'state': 'active'})
            rec.with_context(bond_status_change=True).write({
                'state': 'approved', 'previous_total': ent.approved_total, 'new_total': new_total,
                'previous_effective_to': previous_effective_to,
                'approved_by_id': self.env.user.id, 'approved_date': today})
            rec._log_history('approve', rec.approval_reference, 'draft', 'approved')
            ent._log_history('amendment_approved', _(
                '%(name)s: total %(old)s -> %(new)s (%(ref)s)', name=rec.name, old=rec.previous_total,
                new=rec.new_total, ref=rec.approval_reference))
        return True

    def action_reject(self):
        return self._bond_open_wizard('reject', _('Reject Amendment'))
