# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    daily_report_management_partner_ids = fields.Many2many(
        'res.partner', 'daily_report_mgmt_partner_rel', 'company_id', 'partner_id',
        string='Daily Report: Management / MD Partners',
        help="Outbound payments to these partners are reported as "
             "'MD Sir Cash Paid' on the Daily Sale & Official Cost report, "
             "instead of an ordinary Supplier Transaction.")
