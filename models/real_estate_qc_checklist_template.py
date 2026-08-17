# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateQcChecklistTemplate(models.Model):
    """Configurable, reusable QC checklist (e.g. 'Civil - Foundation Stage')
    that can be attached to a QC Inspection to auto-populate its lines."""
    _name = 'real.estate.qc.checklist.template'
    _description = 'Real Estate QC Checklist Template'
    _rec_name = 'name'
    _order = 'category, name'

    name = fields.Char(string='Template Name', required=True)
    category = fields.Selection([
        ('civil', 'Civil'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('finishing', 'Finishing'),
        ('other', 'Other'),
    ], string='Category', required=True, default='civil')
    line_ids = fields.One2many('real.estate.qc.checklist.template.line', 'template_id',
                                string='Checklist Items')
    line_count = fields.Integer(compute='_compute_line_count')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
