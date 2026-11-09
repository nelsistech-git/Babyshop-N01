# -*- coding: utf-8 -*-
from odoo import models, fields


class RealEstateQcInspectionLine(models.Model):
    _name = 'real.estate.qc.inspection.line'
    _description = 'Real Estate QC Inspection Checklist Result'
    _order = 'id'

    inspection_id = fields.Many2one('real.estate.qc.inspection', string='Inspection',
                                     required=True, ondelete='cascade')
    item_name = fields.Char(string='Checklist Item', required=True)
    description = fields.Char(string='Description')
    result = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('na', 'N/A'),
    ], string='Result', default='pending', required=True)
    remarks = fields.Char(string='Remarks')
