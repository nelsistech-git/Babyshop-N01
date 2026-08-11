from odoo import fields, models, api
from odoo.addons.helper import validator


class InheritedHRDesignation(models.Model):
    _inherit = 'hr.job'

    user_work_location_id = fields.Many2one('stock.location', string="Work/Job Location", ondelete='restrict',
                                            help="Address where employees are working",
                                            domain=[('is_work_loc', '=', True), ('state', '=', 'done')])

    approved_man = fields.Integer(string="Approved Manpower")

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.department_id:
                # name = "%s [%s]" % (name, record.department_id.name_get()[0][1])
                # name = "%s (%s)" % (name, record.department_id.display_name)
                name = "%s (%s) - %s" % (name, record.department_id.name, record.department_id.company_id.short_code)
            result.append((record.id, name))
        return result

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        if self.name:
            msg = 'Designation "%s"' % self.name
            envobj = self.env['hr.job']
            conditionlist = [('name', '=', self.name), ('department_id', '=', self.department_id.id)]
            validator.check_duplicate_value(self, envobj, conditionlist, msg)
