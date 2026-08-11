# coding=utf-8
from odoo import fields, models


class InheritedHREmployee(models.Model):
    """ Inherited HR Employee to add employee facilities """
    _inherit = 'hr.employee'

    facility_ids = fields.One2many('hr.facilities', 'employee_id', string="Fringe Benefits")
