# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityStandard(models.Model):
    """Quality Standard master — buyer / product / process inspection rules.
    See Quality Master Setup (Garment QMS SRS sec. 6) and Quality Standard
    Management (Advanced QMS SRS sec. 6)."""
    _name = 'garment.quality.standard'
    _description = 'Garment Quality Standard'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Standard Name', required=True, tracking=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer')
    style_id = fields.Many2one('garment.style', string='Style')
    standard_type = fields.Selection([
        ('buyer', 'Buyer Standard'),
        ('product', 'Product Standard'),
        ('process', 'Process / Inspection Rule'),
        ('defect_classification', 'Defect Classification'),
    ], string='Standard Type', default='buyer', required=True, tracking=True)
    aql_level = fields.Selection([
        ('1.0', 'AQL 1.0'),
        ('1.5', 'AQL 1.5'),
        ('2.5', 'AQL 2.5'),
        ('4.0', 'AQL 4.0'),
    ], string='AQL Level', default='2.5')
    inspection_level = fields.Selection([
        ('s1', 'Special Level S-1'),
        ('s2', 'Special Level S-2'),
        ('s3', 'Special Level S-3'),
        ('s4', 'Special Level S-4'),
        ('g1', 'General Level I'),
        ('g2', 'General Level II'),
        ('g3', 'General Level III'),
    ], string='Inspection Level', default='g2')
    inspection_method = fields.Selection([
        ('4_point', '4-Point System'),
        ('10_point', '10-Point System'),
        ('buyer_specific', 'Buyer-Specific Method'),
    ], string='Fabric Inspection Method', default='4_point')
    measurement_tolerance = fields.Char(string='Measurement Tolerance', help='e.g. ±0.5 inch')
    defect_limit_critical = fields.Integer(string='Critical Defect Limit', default=0)
    defect_limit_major = fields.Integer(string='Major Defect Limit', default=0)
    defect_limit_minor = fields.Integer(string='Minor Defect Limit', default=0)
    packaging_rules = fields.Text(string='Packaging Rules')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)
