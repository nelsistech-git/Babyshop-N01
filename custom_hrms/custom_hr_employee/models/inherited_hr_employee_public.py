from odoo import api, fields, models, tools


class HrEmployeePublicInh(models.Model):
    _name = "hr.employee.public.two"
    _inherit = ['hr.employee', 'hr.employee.public']
    _description = 'Employee List'
    _order = 'name'

    name = fields.Char(readonly=True)
    identification_id = fields.Char(readonly=True)
    department_id = fields.Many2one(readonly=True)
    inter_company_id = fields.Many2one(readonly=True)
    company_unit_id = fields.Many2one(readonly=True)
    user_work_location_id = fields.Many2one(readonly=True, domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    sales_location_id = fields.Many2one(readonly=True)
    job_id = fields.Many2one(readonly=True)
    employee_type_id = fields.Many2one('hr.employee.type', string='Employee Type', readonly=True)
    contact_no = fields.Char(string="Mobile (Personal)", readonly=True)

    @api.model
    def _get_fields(self):
        return ','.join('emp.%s' % name for name, field in self._fields.items() if
                        field.store and field.type not in ['many2many', 'one2many'])
