from odoo import models, fields, api
from odoo.models import NewId
from datetime import datetime

class UpdateManualReasonNote(models.TransientModel):
    _name = 'update.manual.reason.note.wizard'
    _description = 'Update Manual Reason Note'

    record = fields.Integer(string="Record ID")
    note = fields.Text(string="Note")
    manual_reason = fields.Text(string='Manual Reason')
    manual_uid = fields.Many2one('res.users', string='Last Manual Edited By')
    manual_time = fields.Datetime(string='Last Manual Edited Time')

    @api.model
    def default_get(self, fields):
        res = super(UpdateManualReasonNote, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        att_obj = self.env['hr.attendance'].browse(active_id)
        res['record'] = att_obj.id
        res['note'] = att_obj.note
        res['manual_reason'] = att_obj.manual_reason
        res['manual_uid'] = att_obj.manual_uid.id or None
        res['manual_time'] = att_obj.manual_time or None
        return res

    def action_update_manual_reason(self):
        active_id = self.env.context.get('active_id')
        att_obj = self.env['hr.attendance'].browse(active_id)
        att_obj.note = self.note
        att_obj.manual_reason = self.manual_reason
        att_obj.manual_uid=self.env.user
        att_obj.manual_time=datetime.now()
