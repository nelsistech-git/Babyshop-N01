from odoo import models, fields


class InheritedHREmployee(models.Model):
    """ Inherited HR Employee to add a flag whether the employee can employee requisition or not """
    _inherit = 'hr.employee'

    is_recruiter = fields.Boolean(string="EMP. Recruiter", default=False,
                                  help="IF the employee has employee requisition permission then marked as check else "
                                       "uncheck", groups="hr.group_hr_user")
