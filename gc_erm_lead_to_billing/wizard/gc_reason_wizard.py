# -*- coding: utf-8 -*-
"""Shared reject / request-revision wizard (SRS 11 / 24)."""

from odoo import _, fields, models
from odoo.exceptions import UserError

SUPPORTED_MODELS = (
    'gc.erm.lead',
    'gc.erm.proposal',
    'gc.erm.technical.report',
)


class GcErmReasonWizard(models.TransientModel):
    _name = 'gc.erm.reason.wizard'
    _description = 'GC ERM Reject / Revision Reason'

    mode = fields.Selection([
        ('reject', 'Reject'),
        ('revision', 'Request Revision'),
    ], string='Action', required=True, default='reject')
    res_model = fields.Char(string='Document Model', required=True)
    res_id = fields.Integer(string='Document ID', required=True)
    document_name = fields.Char(string='Document', readonly=True)
    reason = fields.Text(
        string='Reason / Comment', required=True,
        help='This explanation is mandatory and is stored in the audit trail.')
    notify_owner = fields.Boolean(string='Notify the owner', default=True)

    def _get_document(self):
        self.ensure_one()
        if self.res_model not in SUPPORTED_MODELS:
            raise UserError(_(
                'The reason wizard does not support documents of type "%s".',
                self.res_model))
        document = self.env[self.res_model].browse(self.res_id)
        if not document.exists():
            raise UserError(_('The related document no longer exists.'))
        return document

    def action_confirm(self):
        self.ensure_one()
        reason = (self.reason or '').strip()
        if not reason:
            raise UserError(_(
                'A written reason is mandatory before this action can be '
                'completed.'))
        document = self._get_document()
        if self.mode == 'reject':
            document._gc_apply_rejection(reason)
            body = _('Rejected: %s', reason)
        else:
            document._gc_apply_revision(reason)
            body = _('Revision requested: %s', reason)
        document.message_post(
            body=body, message_type='notification',
            subtype_xmlid='mail.mt_note')
        return {'type': 'ir.actions.act_window_close'}
