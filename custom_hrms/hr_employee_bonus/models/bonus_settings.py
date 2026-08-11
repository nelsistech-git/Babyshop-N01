from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class HrBonusSettings(models.Model):
    """ To create probation period length """
    _name = 'hr.bonus.settings'
    _description = 'Bonus Settings'

    head_id = fields.Many2one('hr.employee.bonus.type', string='Settings', ondelete="cascade")

    settings_type = fields.Selection(string='Settings Type', related='head_id.settings_type')

    employee_type_id = fields.Many2one('hr.employee.type', string='Employee Type', groups="hr.group_hr_user")

    days_from = fields.Integer(string='From (Days)', default=0)
    days_to = fields.Integer(string='To (Days)', default=0)
    reference = fields.Char(string='References')

    based_on_type = fields.Selection([
        ('gross', 'Gross'),
        ('basic', 'Basic'),
    ], string='Based On', required=True, default='gross')
    amount_percentage = fields.Float(string='Percentage(%)', default=0, required=True)

    @api.onchange('amount_percentage')
    def _onchange_amount_negative_check(self):
        for rec in self:
            if rec.amount_percentage < 0:
                raise ValidationError("Value cannot be negative value")
