from odoo import fields, models


class InheritedHREmployee(models.Model):
    """ Inherited HR Employee to add transfer, promotion/demotion or disciplinary action history """

    _inherit = 'hr.employee'

    transfer_ids = fields.One2many('hr.employee.transfer.history', 'employee_id', string="Transfer History")
