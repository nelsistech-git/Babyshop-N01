
from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    emp_broad_factor = fields.Boolean(
        string="Broad Factor", help="It will display in broad factor type")
