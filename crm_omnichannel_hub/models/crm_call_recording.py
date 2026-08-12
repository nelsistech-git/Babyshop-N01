# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmCallRecording(models.Model):
    _name = 'crm.call.recording'
    _description = 'Call Recording'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    call_id = fields.Many2one('crm.call.log', string='Call', required=True,
                               ondelete='cascade', index=True)
    partner_id = fields.Many2one(related='call_id.partner_id', store=True, string='Customer')
    agent_id = fields.Many2one(related='call_id.agent_id', store=True, string='Agent')
    call_date = fields.Datetime(related='call_id.call_date', store=True, string='Call Date')
    duration_seconds = fields.Integer(string='Duration (s)')
    audio_file = fields.Binary(string='Audio File', attachment=True)
    audio_filename = fields.Char(string='File Name')
    recording_url = fields.Char(
        string='External Recording URL',
        help='Populated by the IP Calling connector when the recording is stored '
             'on the telephony provider or an S3-compatible bucket instead of Odoo.')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('call_id', 'call_id.display_name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.call_id.display_name or 'Recording'

    def action_download(self):
        self.ensure_one()
        if self.audio_file:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/crm.call.recording/%s/audio_file/%s?download=true' % (
                    self.id, self.audio_filename or 'recording.mp3'),
                'target': 'self',
            }
        if self.recording_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.recording_url,
                'target': 'new',
            }
        return False
