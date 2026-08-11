from odoo import fields, models


class SalaryAdvanceSettings(models.Model):
    _name = 'salary.advance.settings'
    _description = 'Salary Advance Settings'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    value = fields.Integer(string='Value', default=0, required=True)
