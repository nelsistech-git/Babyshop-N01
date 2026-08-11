# coding=utf-8
from odoo import models, fields, api
from odoo.addons.helper import validator


class Particulars(models.Model):
    """ Particulars Name """

    _name = 'hr.particulars'
    _description = 'Particulars Name'

    name = fields.Char(string="Name", help="Particular Name", trim=True)
    dept_name = fields.Selection([('it', 'IT'),
                                  ('admin', 'Admin'), ('hr', 'HR'), ], string='Department', default='it')
    active = fields.Boolean(string="Active", default=True)
    employee_id = fields.Many2many('hr.employee')

    @api.constrains('name')
    def _check_unique_constraint(self):
        """ Check unique name """
        msg = "Name " + self.name
        envObj = self.env['hr.particulars']
        conditionList = [('name', '=ilike', self.name), '|', ('active', '=', True), ('active', '=', False)]

        validator.check_duplicate_value(self, envObj, conditionList, msg)
