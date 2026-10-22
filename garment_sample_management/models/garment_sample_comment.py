# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models, _


class GarmentSampleComment(models.Model):
    """Buyer Comment Management (SRS section 17) — garment.sample.comment."""
    _name = 'garment.sample.comment'
    _description = 'Garment Sample Buyer Comment'
    _order = 'comment_date desc'

    sample_id = fields.Many2one('garment.sample', string='Sample', required=True, ondelete='cascade')
    comment_date = fields.Date(string='Comment Date', default=fields.Date.context_today)
    buyer_user_id = fields.Many2one('res.users', string='Buyer User')
    comment_description = fields.Text(string='Comment Description', required=True)
    image_attachment = fields.Binary(string='Image Attachment', attachment=True)
    action_required = fields.Char(string='Action Required')
    responsible_person_id = fields.Many2one('res.users', string='Responsible Person')
    completion_status = fields.Selection([
        ('open', 'Open'), ('in_progress', 'In Progress'), ('completed', 'Completed'),
    ], string='Completion Status', default='open')

    def action_mark_completed(self):
        self.write({'completion_status': 'completed'})
        for rec in self:
            rec.sample_id.message_post(
                body=_('Buyer comment marked completed: %s') % (rec.comment_description or '-'))
