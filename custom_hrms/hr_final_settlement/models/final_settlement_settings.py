# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class EmployeeClearance(models.Model):
    _name = 'final.settlement.settings'
    _description = "Final Settlement Settings"
    _rec_name = "particulars"

    section_type = fields.Selection([
        ('a', 'Section A (Concerned Dept.)'),
        ('b', 'Section B (Accounts)'),
        ('c', 'Section C (Admin)'),
        ('d', 'Section D (IT)'),
        ('e', 'Section E (HR)')
    ], string="Section", copy=False)

    particulars = fields.Char(string="Particulars")