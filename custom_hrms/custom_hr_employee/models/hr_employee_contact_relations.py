from odoo import api, fields, models
from odoo.addons.helper import validator


class HrEmployeeContactRelation(models.Model):
    _name = 'hr.employee.contact.relation'
    _description = 'Employee Contact Relation'
    _order = 'name'

    name = fields.Char(string="Name", required=True, trim=True)
    active = fields.Boolean(string="Active", default=True)

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = 'Name "%s"' % self.name
        envobj = self.env['hr.employee.contact.relation']
        conditionlist = [('name', '=', self.name)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)
