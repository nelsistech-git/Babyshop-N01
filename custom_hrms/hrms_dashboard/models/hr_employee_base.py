
from datetime import timedelta
from odoo import models, fields


class HrEmployeeBase(models.AbstractModel):
    """Inherits the model hr.employee.base to override the
     method _compute_newly_hired"""
    _inherit = 'hr.employee.base'

    def _compute_newly_hired(self):
        new_hire_date = fields.Datetime.now() - timedelta(days=90)
        for employee in self:
            if employee['first_contract_date']:
                employee.newly_hired = (employee[
                                           'first_contract_date'] >
                                        new_hire_date.date())
            else:
                employee.newly_hired = employee[
                                           'create_date'] > new_hire_date
