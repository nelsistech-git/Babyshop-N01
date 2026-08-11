# -*- coding: utf-8 -*-
from odoo import models, fields


class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'

    x_page_link = fields.Char(string='Page Link')
    x_brand_name = fields.Char(string='Brand Name')
    x_category = fields.Selection([
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
    ], string='Category')
