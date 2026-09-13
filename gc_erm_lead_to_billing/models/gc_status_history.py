# -*- coding: utf-8 -*-
"""Immutable audit log of every controlled state change (SRS 62)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class GcErmStatusHistory(models.Model):
    _name = 'gc.erm.status.history'
    _description = 'GC ERM Status History'
    _order = 'change_date desc, id desc'
    _rec_name = 'document_ref'

    model_name = fields.Char(
        string='Document Model', required=True, index=True, readonly=True,
        help='Technical model of the document the entry belongs to.')
    res_id = fields.Integer(
        string='Document ID', required=True, index=True, readonly=True)
    document_ref = fields.Char(
        string='Document', readonly=True, index=True,
        help='Human readable reference of the document at the time of change.')
    document_model_label = fields.Char(
        string='Document Type', compute='_compute_document_model_label', store=True)

    old_state = fields.Char(string='Old State (technical)', readonly=True)
    new_state = fields.Char(string='New State (technical)', readonly=True)
    old_state_label = fields.Char(string='From', readonly=True)
    new_state_label = fields.Char(string='To', readonly=True)

    user_id = fields.Many2one(
        'res.users', string='Changed By', required=True, readonly=True,
        default=lambda self: self.env.user, index=True)
    change_date = fields.Datetime(
        string='Changed On', required=True, readonly=True,
        default=fields.Datetime.now, index=True)
    comment = fields.Text(string='Comment', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', index=True)

    @api.depends('model_name')
    def _compute_document_model_label(self):
        for record in self:
            model = self.env['ir.model'].sudo().search(
                [('model', '=', record.model_name)], limit=1)
            record.document_model_label = model.name or record.model_name

    def action_open_document(self):
        """Jump from the audit log back to the source document."""
        self.ensure_one()
        if self.model_name not in self.env:
            raise UserError(_('The related document model no longer exists.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.model_name,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def write(self, vals):
        # The audit trail is append-only for regular users.  Superuser writes
        # are still allowed so that stored computations and data migrations
        # keep working.
        if not self.env.su:
            raise UserError(_(
                'Status history entries are part of the audit trail and '
                'cannot be modified.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group('gc_erm_lead_to_billing.group_gc_erm_admin') \
                and not self.env.su:
            raise UserError(_(
                'Status history entries are part of the audit trail and can '
                'only be removed by an ERM Administrator.'))
        return super().unlink()
