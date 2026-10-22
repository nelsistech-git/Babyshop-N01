# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentTechAttachment(models.Model):
    """Buyer Tech Pack Import + Digital Files (SRS section 17) —
    garment.tech.attachment. Stores buyer-provided files (PDF/Excel/Word/
    Image/Email/Portal) and the AI OCR extraction result, which always
    requires human verification before it is trusted (SRS: 'AI extracted
    data must require human verification before approval')."""
    _name = 'garment.tech.attachment'
    _description = 'Garment Tech Pack Attachment'
    _order = 'sequence'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='File Name', required=True)
    source = fields.Selection([
        ('pdf', 'PDF'), ('excel', 'Excel'), ('word', 'Word'), ('image', 'Image'),
        ('email_attachment', 'Email Attachment'), ('portal_upload', 'Portal Upload'),
    ], string='Source', required=True)
    file = fields.Binary(string='File', attachment=True, required=True)
    filename = fields.Char(string='Filename')
    uploaded_by_id = fields.Many2one('res.users', string='Uploaded By', default=lambda s: s.env.user)
    upload_date = fields.Date(string='Upload Date', default=fields.Date.context_today)

    ai_extracted_data = fields.Text(string='AI Extracted Data', readonly=True,
                                     help='Raw text/field extraction produced by the AI Tech Pack Assistant. '
                                          'Always requires human verification before use.')
    ai_extraction_done = fields.Boolean(string='AI Extraction Run', default=False, readonly=True)
    human_verified = fields.Boolean(string='Human Verified', default=False,
                                     help='Must be checked by a technical user before extracted data can be '
                                          'trusted or copied into the Tech Pack.')

    def action_run_ai_extraction(self):
        """Automatic Tech Pack Reading (SRS section 17 / 25.1)."""
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            extracted = ai_engine.extract_techpack_data(rec)
            rec.write({'ai_extracted_data': extracted, 'ai_extraction_done': True, 'human_verified': False})
        return True

    @api.onchange('ai_extracted_data')
    def _onchange_reset_verification(self):
        self.human_verified = False
