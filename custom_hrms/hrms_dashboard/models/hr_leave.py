
from odoo import fields, models


class HrLeave(models.Model):
    """ Adds field to show leave duration on hr.leave """
    _inherit = 'hr.leave'

    duration_display = fields.Char(
        string='Requested (Days/Hours)', compute='_compute_duration_display',
        store=True, help="Field allowing to see the leave request duration "
                         "in days or hours depending on the "
                         "leave_type_request_unit")
