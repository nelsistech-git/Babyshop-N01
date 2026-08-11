# coding=utf-8

from odoo import fields, models, api


class HRFacilities(models.Model):
    """ HR Facilities model """

    _name = 'hr.facilities'
    _description = 'HR Facilities'
    _rec_name = "employee_id"

    employee_id = fields.Many2one('hr.employee', string='Employee')
    dept_name = fields.Selection([('it', 'IT'),
                                  ('admin', 'Admin'),
                                  ('hr', 'HR')
                                  ], string='Department')
    particular_id = fields.Many2one('hr.particulars', string="Particular", domain="[('dept_name', '=', dept_name)]")
    date = fields.Date(string="Date", help="Benefits Given date")
    value = fields.Float(string="Value", help="Put any type of value here")
    qty = fields.Integer(string="Qty", help="Put qty of particulars")

    @api.onchange('dept_name')
    def _onchange_dept_name(self):
        if self.dept_name:
            particular_obj = self.env['hr.particulars'].search([('name', '=', self.dept_name)])

            self.particular_id = particular_obj.name



