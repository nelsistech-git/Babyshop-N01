from odoo import models, fields, api


class RosteringShiftSettings(models.Model):
    _name = "rostering.shift.settings"
    _description = "Rostering Shift Settings"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    remarks = fields.Text(string='Remarks')
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    active = fields.Boolean(default=True)
    
    @api.onchange('start_time', 'end_time')
    def _onchange_hours(self):
        # avoid negative or after midnight
        self.start_time = min(self.start_time, 23.99)
        self.start_time = max(self.start_time, 0.0)
        self.end_time = min(self.end_time, 23.99)
        self.end_time = max(self.end_time, 0.0)

        # avoid wrong order
        # self.end_time = max(self.end_time, self.start_time)
