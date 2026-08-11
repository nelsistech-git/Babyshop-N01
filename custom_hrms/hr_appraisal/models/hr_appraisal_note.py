# -*- coding: utf-8 -*-


from odoo import api, fields, models


class HrAppraisalNote(models.Model):
    _name = "hr.appraisal.note"
    _description = "Appraisal Assessment Note"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
