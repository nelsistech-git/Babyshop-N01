# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityRca(models.Model):
    """Root Cause Analysis — 5-Why, Fishbone and Pareto methods. See Root
    Cause Analysis (base QMS SRS sec. 38, Garment QMS SRS sec. 32 and
    Advanced QMS SRS sec. 37 — 'garment.quality.rca')."""
    _name = 'garment.quality.rca'
    _description = 'Garment Quality Root Cause Analysis'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Problem Title', required=True)
    capa_id = fields.Many2one('garment.quality.capa', string='CAPA')
    defect_id = fields.Many2one('garment.quality.defect', string='Defect')
    method = fields.Selection([
        ('5why', '5 Why Analysis'),
        ('fishbone', 'Fishbone Diagram'),
        ('pareto', 'Pareto Analysis'),
    ], string='Method', default='5why', required=True)
    problem_statement = fields.Text(string='Problem Statement', required=True)

    why_1 = fields.Char(string='Why 1')
    why_2 = fields.Char(string='Why 2')
    why_3 = fields.Char(string='Why 3')
    why_4 = fields.Char(string='Why 4')
    why_5 = fields.Char(string='Why 5')

    fishbone_category = fields.Selection([
        ('man', 'Man'),
        ('machine', 'Machine'),
        ('material', 'Material'),
        ('method', 'Method'),
        ('measurement', 'Measurement'),
        ('environment', 'Environment'),
    ], string='Fishbone Category')

    pareto_rank = fields.Integer(string='Pareto Rank')
    pareto_percentage = fields.Float(string='Pareto Contribution (%)')

    root_cause = fields.Text(string='Root Cause', required=True)
    recommended_action = fields.Text(string='Recommended Action')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('analysis', 'Analysis in Progress'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
