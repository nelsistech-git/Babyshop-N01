from odoo import models, fields, api, tools, _
import babel
import time
from datetime import datetime, timedelta


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    # comment-for-upgrade
    # @api.model
    # def __def_att_policy(self):
    #     att_policy_id = self.env['hr.attendance.policy'].search([('id', '!=', 0)], order="id desc", limit=1)
    #     if att_policy_id:
    #         return att_policy_id.id
    #     else:
    #         return self.env.company.resource_calendar_id.id

    # att_policy_id = fields.Many2one('hr.attendance.policy',
    #                                 string='Attendance Policy', default=lambda self: self.__def_att_policy())
    att_policy_id = fields.Many2one('hr.attendance.policy', string='Attendance Policy')
