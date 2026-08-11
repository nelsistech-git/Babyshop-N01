# -*- coding: utf-8 -*-
from odoo import models, fields


class InheritedHrEmployeeInheritHrFinalSettlement(models.Model):
    _inherit = 'hr.employee'

    pf_settlement_status = fields.Boolean(string="PF Final Settlement Status", default=False, store=True,
                                          groups="hr.group_hr_user")
    wppf_settlement_status = fields.Boolean(string="WPPF Final Settlement Status", default=False,
                                            groups="hr.group_hr_user")
    final_settlement_status = fields.Boolean(string="Final Settlement Status", default=False, store=True,
                                             groups="hr.group_hr_user")
