# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentTechpackVersion(models.Model):
    """Version control (SRS section 18) — garment.techpack.version."""
    _name = 'garment.techpack.version'
    _description = 'Garment Tech Pack Version'
    _inherit = ['mail.thread']
    _order = 'version_number desc'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    version_number = fields.Char(string='Revision Number', required=True)
    revision_date = fields.Date(string='Revision Date', default=fields.Date.context_today)
    changed_by_id = fields.Many2one('res.users', string='Changed By', default=lambda s: s.env.user)
    change_reason = fields.Text(string='Change Reason')
    buyer_reference = fields.Char(string='Buyer Reference')
    effective_date = fields.Date(string='Effective Date')
    revision_type = fields.Selection([
        ('minor', 'Minor Revision'), ('major', 'Major Revision'),
    ], string='Revision Type', default='minor', required=True)
    impact_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='Impact Level', default='low')
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)
    previous_version_id = fields.Many2one('garment.techpack.version', string='Previous Version Reference')
    # Revision Workflow last step "Old Version Archived" (SRS section 18): the
    # single non-archived version for a given Tech Pack. Superseded on approval
    # of a newer version, never on mere creation.
    is_current = fields.Boolean(string='Current Version', default=True, copy=False, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('previous_version_id') and vals.get('techpack_id'):
                latest = self.search([
                    ('techpack_id', '=', vals['techpack_id']), ('is_current', '=', True),
                ], order='create_date desc', limit=1)
                if latest:
                    vals['previous_version_id'] = latest.id
        records = super().create(vals_list)
        for rec in records:
            rec.techpack_id.message_post(
                body=_('Version %s created (%s): %s') % (
                    rec.version_number, rec.revision_type, rec.change_reason or '-'))
        return records

    def action_approve(self):
        for rec in self:
            rec.write({'approval_status': 'approved', 'is_current': True})
            # Archive every other version of this Tech Pack (SRS 18: "New Version
            # Released -> Old Version Archived").
            (rec.techpack_id.version_ids - rec).write({'is_current': False})
            rec.techpack_id.write({'version': rec.version_number, 'is_locked': True})
