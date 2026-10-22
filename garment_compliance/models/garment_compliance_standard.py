# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Compliance Master Management (SRS1 sec. 7, SRS2 sec. 6) — garment.compliance.standard.
The master list of standards/authorities the factory is measured against
(buyer codes of conduct, social-compliance schemes, ISO management systems,
Bangladesh government/industry bodies).
"""
from odoo import fields, models


class GarmentComplianceStandard(models.Model):
    _name = 'garment.compliance.standard'
    _description = 'Garment Compliance Standard'
    _order = 'category, name'

    name = fields.Char(string='Standard Name', required=True)
    code = fields.Char(string='Short Code')
    category = fields.Selection([
        ('buyer', 'Buyer Compliance'),
        ('social', 'Social Compliance'),
        ('safety', 'Safety Compliance'),
        ('fire', 'Fire Safety'),
        ('building', 'Building Safety'),
        ('environmental', 'Environmental Compliance'),
        ('quality_iso', 'Quality / ISO Management System'),
        ('government', 'Government / Regulatory'),
        ('trade_association', 'Trade Association'),
        ('esg', 'ESG / Sustainability'),
    ], string='Category', required=True)
    standard_authority = fields.Char(
        string='Standard Authority',
        help='Issuing/owning body, e.g. Amfori BSCI, WRAP Inc., SEDEX, Accord/Alliance/RSC, '
             'DIFE, Department of Environment, BGMEA, BKMEA.')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

    requirement_ids = fields.One2many('garment.compliance.requirement', 'standard_id', string='Requirements')
    requirement_count = fields.Integer(compute='_compute_counts')
    certificate_ids = fields.One2many('garment.compliance.certificate', 'standard_id', string='Certificates')
    certificate_count = fields.Integer(compute='_compute_counts')
    audit_ids = fields.One2many('garment.compliance.audit', 'standard_id', string='Audits')
    audit_count = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        for rec in self:
            rec.requirement_count = len(rec.requirement_ids)
            rec.certificate_count = len(rec.certificate_ids)
            rec.audit_count = len(rec.audit_ids)
