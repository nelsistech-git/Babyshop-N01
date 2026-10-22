# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentSampleRevision(models.Model):
    """Sample Revision Management (SRS section 18) — garment.sample.revision."""
    _name = 'garment.sample.revision'
    _description = 'Garment Sample Revision'
    _inherit = ['mail.thread']
    _order = 'revision_number desc'

    sample_id = fields.Many2one('garment.sample', string='Sample', required=True, ondelete='cascade')
    revision_number = fields.Integer(string='Revision Number', required=True, default=1)
    comment_id = fields.Many2one('garment.sample.comment', string='Triggering Buyer Comment',
                                  domain="[('sample_id', '=', sample_id)]",
                                  help='Previous Sample Reference (SRS section 40) — the buyer comment that '
                                       'raised this revision, when the revision follows a buyer comment.')
    previous_issue = fields.Text(string='Previous Issue')
    correction_action = fields.Text(string='Correction Action')
    responsible_department = fields.Selection([
        ('merchandising', 'Merchandising'), ('pattern', 'Pattern Room'), ('cutting', 'Cutting'),
        ('sewing', 'Sewing / Sample Room'), ('finishing', 'Finishing'), ('quality', 'Quality (QA)'),
    ], string='Responsible Department')
    new_sample_date = fields.Date(string='New Sample Date')
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.sample_id.write({'status': 'revision'})
            rec.sample_id.message_post(
                body=_('Sample revision #%s created: %s') % (rec.revision_number, rec.correction_action or '-'))
        return records
