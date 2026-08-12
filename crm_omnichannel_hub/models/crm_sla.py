# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CrmSla(models.Model):
    _name = 'crm.sla'
    _description = 'SLA Policy'

    name = fields.Char(required=True)
    channel_ids = fields.Many2many('crm.channel', string='Channels',
                                    help='Leave empty to apply to all channels.')
    green_minutes = fields.Integer(string='Green Threshold (minutes)', default=1,
                                    help='Respond within this time = On Time (Green).')
    yellow_minutes = fields.Integer(string='Yellow Threshold (minutes)', default=2,
                                     help='Respond within this time = At Risk (Yellow).')
    red_minutes = fields.Integer(string='Red Threshold (minutes)', default=5,
                                  help='Beyond the yellow threshold and up to this time = Breached (Red).')
    escalate_user_ids = fields.Many2many('res.users', string='Escalate To (Manager Notification)')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.constrains('green_minutes', 'yellow_minutes', 'red_minutes')
    def _check_thresholds(self):
        for rec in self:
            if rec.green_minutes <= 0 or rec.yellow_minutes <= 0 or rec.red_minutes <= 0:
                raise ValidationError(_('SLA thresholds must be positive numbers of minutes.'))
            if not (rec.green_minutes <= rec.yellow_minutes <= rec.red_minutes):
                raise ValidationError(
                    _('Thresholds must be in ascending order: Green <= Yellow <= Red.'))
