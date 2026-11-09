# -*- coding: utf-8 -*-
from odoo import models, fields


class RealEstateQcChecklistTemplateLine(models.Model):
    _name = 'real.estate.qc.checklist.template.line'
    _description = 'Real Estate QC Checklist Template Item'
    _order = 'sequence, id'

    template_id = fields.Many2one('real.estate.qc.checklist.template', string='Template',
                                   required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    item_name = fields.Char(string='Checklist Item', required=True,
                             help='e.g. Foundation, Column, Wiring, Pipe, Paint...')
    description = fields.Char(string='Description / Standard to Check')
