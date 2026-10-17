# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .bond_compliance_common import (
    G_APPROVER, G_OFFICER, WORKFLOW_CTX, check_segregation, clear_activities,
    require_any_group, schedule_group_activity, schedule_user_activity,
)

SUMMARY_EXC_APPROVE = 'Approve compliance exception'
SUMMARY_EXC_REVISE = 'Revise rejected compliance exception'

EXCEPTION_CONTENT_FIELDS = {
    'rule_id', 'reason', 'conditions', 'valid_from', 'valid_to', 'reference',
    'res_model', 'res_id', 'requires_professional_verification',
}
EXCEPTION_PROTECTED_FIELDS = {
    'state', 'approved_by', 'approved_date', 'submitted_by', 'rejection_reason', 'requested_by',
}


class BondComplianceException(models.Model):
    _name = 'bond.compliance.exception'
    _description = 'Bond Compliance Exception'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Number', default='New', readonly=True, copy=False, index=True)
    rule_id = fields.Many2one(
        'bond.compliance.rule', string='Rule Version', required=True, ondelete='restrict',
        domain=[('verification_status', 'in', ('active', 'superseded'))],
        tracking=True, index=True)
    rule_code = fields.Char(related='rule_id.code', store=True, string='Rule Code')
    rule_version = fields.Integer(related='rule_id.version', store=True, string='Version')
    reference = fields.Char(
        string='Transaction Reference', required=True, tracking=True,
        help='Business reference the exception applies to (e.g. receipt or LC number).')
    res_model = fields.Char(string='Document Model')
    res_id = fields.Integer(string='Document ID')
    reason = fields.Text(string='Reason / Justification', required=True)
    conditions = fields.Text(string='Conditions')
    valid_from = fields.Date(tracking=True)
    valid_to = fields.Date(tracking=True)
    requires_professional_verification = fields.Boolean(tracking=True)
    professional_verified_by = fields.Char()
    professional_verified_date = fields.Date()
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
         ('rejected', 'Rejected'), ('revoked', 'Revoked'), ('expired', 'Expired')],
        default='draft', required=True, readonly=True, copy=False, tracking=True, index=True)
    requested_by = fields.Many2one(
        'res.users', default=lambda self: self.env.user, readonly=True, copy=False)
    submitted_by = fields.Many2one('res.users', readonly=True, copy=False)
    approved_by = fields.Many2one('res.users', readonly=True, copy=False, tracking=True)
    approved_date = fields.Datetime(readonly=True, copy=False)
    rejection_reason = fields.Text(readonly=True, copy=False)

    # ------------------------------------------------------------------
    @api.constrains('valid_from', 'valid_to')
    def _check_validity_dates(self):
        for exc in self:
            if exc.valid_from and exc.valid_to and exc.valid_to < exc.valid_from:
                raise ValidationError(_('"Valid To" cannot be earlier than "Valid From".'))

    def is_valid_on(self, on_date):
        self.ensure_one()
        return (self.state == 'approved' and self.valid_from and self.valid_to
                and self.valid_from <= on_date <= self.valid_to)

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        workflow = self.env.context.get(WORKFLOW_CTX)
        for vals in vals_list:
            if not workflow and (vals.get('state', 'draft') != 'draft' or (
                    set(vals) & (EXCEPTION_PROTECTED_FIELDS - {'state', 'requested_by'}))):
                raise UserError(_('Exceptions are always created as drafts.'))
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('bond.compliance.exception') or 'New'
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get(WORKFLOW_CTX):
            keys = set(vals)
            protected = keys & EXCEPTION_PROTECTED_FIELDS
            if protected:
                raise UserError(_(
                    'These fields are managed by the exception workflow: %s',
                    ', '.join(sorted(protected))))
            if keys & EXCEPTION_CONTENT_FIELDS:
                for exc in self:
                    if exc.state != 'draft':
                        raise UserError(_(
                            'Exception %s is not a draft and its content is locked.', exc.name))
        return super().write(vals)

    def unlink(self):
        for exc in self:
            if exc.state not in ('draft', 'rejected'):
                raise UserError(_(
                    'Exception %s is part of the audit history and cannot be deleted.', exc.name))
        return super().unlink()

    def _wf_write(self, vals):
        return self.with_context(**{WORKFLOW_CTX: True}).write(vals)

    # ------------------------------------------------------------------
    def _get_configuration_errors(self):
        self.ensure_one()
        errors = []
        if not self.reason or not self.reason.strip():
            errors.append(_('A justification is required.'))
        if not (self.valid_from and self.valid_to):
            errors.append(_('Exceptions must be time-boxed: set both "Valid From" and "Valid To".'))
        if self.rule_id.verification_status not in ('active', 'superseded'):
            errors.append(_('The selected rule version has not been activated.'))
        return errors

    def action_submit(self):
        require_any_group(self.env, (G_OFFICER,), _('submit compliance exceptions'))
        for exc in self:
            if exc.state != 'draft':
                raise UserError(_('Only draft exceptions can be submitted.'))
            errors = exc._get_configuration_errors()
            if errors:
                raise UserError(_('Exception %(name)s cannot be submitted:\n- %(errors)s',
                                  name=exc.name, errors='\n- '.join(errors)))
            exc._wf_write({'state': 'submitted', 'submitted_by': self.env.user.id})
            exc.message_post(body=_('Submitted for approval.'))
            schedule_group_activity(exc, G_APPROVER, SUMMARY_EXC_APPROVE,
                                    note=_('Please review this compliance exception.'))
        return True

    def action_approve(self):
        require_any_group(self.env, (G_APPROVER,), _('approve compliance exceptions'))
        for exc in self:
            if exc.state != 'submitted':
                raise UserError(_('Only submitted exceptions can be approved.'))
            check_segregation(self.env, exc.requested_by, _(
                'The approver must be a different person from the requester.'))
            check_segregation(self.env, exc.submitted_by, _(
                'The approver must be a different person from the one who submitted the exception.'))
            if exc.requires_professional_verification and not (
                    exc.professional_verified_by and exc.professional_verified_date):
                raise UserError(_(
                    'Exception %s requires professional verification before approval.', exc.name))
            errors = exc._get_configuration_errors()
            if errors:
                raise UserError(_('Exception %(name)s cannot be approved:\n- %(errors)s',
                                  name=exc.name, errors='\n- '.join(errors)))
            exc._wf_write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            exc.message_post(body=_('Exception approved.'))
            clear_activities(exc, [SUMMARY_EXC_APPROVE])
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Exception'),
            'res_model': 'bond.compliance.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def action_reject(self, reason=None):
        reason = (reason or '').strip()
        if not reason:
            raise UserError(_('A rejection reason is required.'))
        require_any_group(self.env, (G_APPROVER,), _('reject compliance exceptions'))
        for exc in self:
            if exc.state != 'submitted':
                raise UserError(_('Only submitted exceptions can be rejected.'))
            requester = exc.requested_by
            exc._wf_write({'state': 'rejected', 'rejection_reason': reason})
            exc.message_post(body=Markup('%s %s') % (_('Exception rejected. Reason:'), reason))
            clear_activities(exc, [SUMMARY_EXC_APPROVE])
            schedule_user_activity(exc, requester, SUMMARY_EXC_REVISE, note=reason)
        return True

    def action_return_to_draft(self):
        require_any_group(self.env, (G_OFFICER,), _('revise compliance exceptions'))
        for exc in self:
            if exc.state != 'rejected':
                raise UserError(_('Only rejected exceptions can be returned to draft.'))
            exc._wf_write({'state': 'draft', 'rejection_reason': False, 'submitted_by': False})
            clear_activities(exc, [SUMMARY_EXC_REVISE])
        return True

    def action_revoke(self):
        require_any_group(self.env, (G_APPROVER,), _('revoke compliance exceptions'))
        for exc in self:
            if exc.state != 'approved':
                raise UserError(_('Only approved exceptions can be revoked.'))
            exc._wf_write({'state': 'revoked'})
            exc.message_post(body=_('Exception revoked.'))
        return True

    @api.model
    def _cron_expire_exceptions(self):
        today = fields.Date.context_today(self)
        expired = self.sudo().search([('state', '=', 'approved'), ('valid_to', '<', today)])
        for exc in expired:
            exc._wf_write({'state': 'expired'})
            exc.message_post(body=_('Exception expired on %s.', exc.valid_to))
        return True
