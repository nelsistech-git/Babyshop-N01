# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentStyleRevision(models.Model):
    """Style Version Control (SRS section 23) — garment.style.revision.
    Previous versions remain read-only for audit purposes."""
    _name = 'garment.style.revision'
    _description = 'Garment Style Revision'
    _inherit = ['mail.thread']
    _order = 'version_number desc'

    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    version_number = fields.Integer(string='Version Number', required=True, default=1)
    revision_number = fields.Char(string='Revision Number')
    parent_version_id = fields.Many2one('garment.style.revision', string='Parent Version')
    change_type = fields.Selection([
        ('measurement', 'Measurements'), ('colorway', 'Colorways'), ('fabric', 'Fabric'), ('trim', 'Trims'),
        ('artwork', 'Artwork'), ('label', 'Labels'), ('packaging', 'Packaging'), ('bom', 'BOM'),
        ('technical_note', 'Technical Notes'), ('other', 'Other'),
    ], string='Change Type', required=True)
    change_reason = fields.Text(string='Change Reason')
    changed_by_id = fields.Many2one('res.users', string='Changed By', default=lambda s: s.env.user)
    changed_date = fields.Datetime(string='Changed Date', default=fields.Datetime.now)
    buyer_reference = fields.Char(string='Buyer Reference')
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)
    snapshot_note = fields.Text(string='Snapshot / Notes',
                                 help='Free-text description of the style state at this revision, '
                                      'since prior versions are locked read-only for audit purposes.')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.style_id.message_post(
                body=_('Revision v%s created (%s): %s') % (
                    rec.version_number, rec.change_type, rec.change_reason or '-')
            )
        return records

    def action_approve(self):
        for rec in self:
            rec.write({'approval_status': 'approved'})
            rec.style_id.write({'is_locked': True})
