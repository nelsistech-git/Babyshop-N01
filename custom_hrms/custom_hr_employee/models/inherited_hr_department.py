from odoo import models, api
from odoo.addons.helper import validator


class InheritedHRDepartment(models.Model):
    """ add duplicate validation for HR Departments """
    _inherit = 'hr.department'

    @api.onchange('name')
    def _remove_space(self):
        for r in self:
            if r.name:
                r.name = str(r.name).strip()

    @api.constrains('name')
    def _check_unique_constraint(self):
        msg = "Department Name"
        envObj = self.env['hr.department']

        conditionList1 = [('company_id.id', '=', self.company_id.id), ('name', '=ilike', self.name)]
        validator.check_duplicate_value(self, envObj, conditionList1, msg)

    def name_get(self):
        result = []
        for record in self:
            name = ''
            dept_name = record.name
            if record.company_id:
                # name = "%s [%s]" % (record.parent_id.name_get()[0][1])
                # name = "%s [%s]" % (name,record.parent_id.name)
                name = "%s - %s" % (dept_name, record.company_id.short_code)
                if record.parent_id:
                    name = "%s/%s - %s" % (record.parent_id.name, dept_name, record.company_id.short_code)
            result.append((record.id, name))
        return result
