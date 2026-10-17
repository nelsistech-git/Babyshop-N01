# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BondWarehouseLicenseRenewal(models.Model):
    _name = 'bond.warehouse.license.renewal'
    _description = 'Bond License Renewal Application'
    _inherit = ['bond.warehouse.lifecycle.mixin', 'mail.thread']
    _order = 'id desc'

    _bond_status_transitions = {'reject': ({'applied'}, 'rejected')}

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    license_id = fields.Many2one('bond.warehouse.license', required=True, ondelete='restrict',
                                 tracking=True)
    company_id = fields.Many2one(related='license_id.company_id', store=True, readonly=True)
    application_date = fields.Date(default=fields.Date.context_today, required=True)
    application_reference = fields.Char(string='Application Reference')
    requested_expiry_date = fields.Date(string='Requested New Expiry Date', required=True)
    previous_expiry_date = fields.Date(readonly=True, copy=False)
    approval_reference = fields.Char(string='Approval Reference', copy=False)
    decision_date = fields.Date(readonly=True, copy=False)
    attachment_ids = fields.Many2many('ir.attachment', 'bond_renewal_attachment_rel', 'renewal_id',
                                      'attachment_id', string='Supporting Documents')
    note = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'), ('applied', 'Applied'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], default='draft', required=True, copy=False, tracking=True)

    @api.constrains('license_id', 'state')
    def _check_single_open_renewal(self):
        for rec in self:
            if rec.state in ('draft', 'applied') and self.search_count([
                    ('license_id', '=', rec.license_id.id), ('state', 'in', ('draft', 'applied')),
                    ('id', '!=', rec.id)]):
                raise ValidationError(_('This license already has an open renewal application.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bond.warehouse.license.renewal') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get('bond_status_change'):
            for rec in self:
                if rec.state == 'applied' and set(vals) <= {'approval_reference', 'note'}:
                    continue
                if rec.state != 'draft':
                    raise UserError(_('Submitted renewal applications can no longer be edited.'))
        return super().write(vals)

    def action_submit(self):
        for rec in self:
            lic = rec.license_id
            if rec.state != 'draft':
                raise UserError(_('Only draft applications can be submitted.'))
            if lic.state not in ('active', 'expired'):
                raise UserError(_('Only active or expired licenses can be renewed.'))
            if not rec.application_reference:
                raise UserError(_('Enter the application reference before submitting.'))
            if rec.requested_expiry_date <= lic.expiry_date:
                raise UserError(_('The requested expiry date must be later than the current expiry date.'))
            rec.with_context(bond_status_change=True).write({
                'state': 'applied', 'previous_expiry_date': lic.expiry_date})
            rec._log_history('submit', rec.application_reference, 'draft', 'applied')
            lic._log_history('renewal_applied', rec.name)
        return True

    def action_approve(self):
        self._bond_require_manager()
        today = fields.Date.context_today(self)
        for rec in self:
            lic = rec.license_id
            if rec.state != 'applied':
                raise UserError(_('Only applied renewals can be approved.'))
            if not rec.approval_reference:
                raise UserError(_('Enter the approval reference before approving.'))
            if lic.state not in ('active', 'expired'):
                raise UserError(_('The license must be active or expired to apply a renewal.'))
            if rec.requested_expiry_date <= lic.expiry_date:
                raise UserError(_('The requested expiry date must be later than the current expiry date.'))
            old_state, old_expiry = lic.state, lic.expiry_date
            lic.with_context(bond_renewal=True).write({'expiry_date': rec.requested_expiry_date})
            if lic.state == 'expired' and rec.requested_expiry_date >= today:
                lic.with_context(bond_status_change=True).write({'state': 'active'})
            rec.with_context(bond_status_change=True).write({
                'state': 'approved', 'decision_date': today})
            rec._log_history('approve', rec.approval_reference, 'applied', 'approved')
            lic._log_history('renewal_approved', _(
                'Expiry %(old)s -> %(new)s (%(ref)s)', old=old_expiry,
                new=rec.requested_expiry_date, ref=rec.approval_reference), old_state, lic.state)
        return True

    def action_reject(self):
        return self._bond_open_wizard('reject', _('Reject Renewal'))
