from odoo import api, fields, models
from odoo.addons.helper import validator


class HrBank(models.Model):
    _name = 'hr.bank'
    _description = 'Hr Bank'

    name = fields.Char(string="Name", required=True, trim=True)

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = 'Name "%s"' % self.name
        envobj = self.env['hr.bank']
        conditionlist = [('name', '=', self.name)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)
