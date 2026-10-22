# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Certification Management (SRS1 sec. 16, SRS1 sec. 52, SRS2 sec. 9, SRS2
sec. 68) — garment.compliance.certificate. Deliberately kept as ONE
unified expiry-tracked register rather than separate models per SRS
document: buyer social-compliance certificates (WRAP/BSCI/SEDEX), ISO
management-system certificates (9001/14001/45001), sustainability
certificates (Higg Index/GOTS/OEKO-TEX/LEED), and Bangladesh government
licenses/registrations/memberships (Fire Safety Certificate, Environmental
Clearance Certificate, Trade License, Factory License, BGMEA/BKMEA
Membership, Export/Tax/Registration documents) all share the same
Name/Number/Authority/Issue-Expiry/Responsible-Person/Status shape.
"""
from datetime import timedelta

from odoo import api, fields, models, _


class GarmentComplianceCertificate(models.Model):
    _name = 'garment.compliance.certificate'
    _description = 'Garment Compliance Certificate / License'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'expiry_date'

    reference = fields.Char(string='Reference No.', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Certificate / License Name', required=True, tracking=True)
    category = fields.Selection([
        ('social_compliance', 'Social Compliance (BSCI/WRAP/SEDEX/Accord-Alliance)'),
        ('quality_iso', 'Quality / ISO Management System'),
        ('sustainability', 'Sustainability (Higg Index/GOTS/OEKO-TEX/LEED)'),
        ('fire_safety', 'Fire Safety Certificate'),
        ('building_safety', 'Building / Structural Approval'),
        ('environmental', 'Environmental Clearance'),
        ('trade_license', 'Trade License'),
        ('factory_license', 'Factory License / Registration'),
        ('trade_association', 'Trade Association Membership (BGMEA/BKMEA)'),
        ('export_tax', 'Export / Tax Documentation'),
        ('other', 'Other'),
    ], string='Category', required=True, tracking=True)
    standard_id = fields.Many2one('garment.compliance.standard', string='Standard')
    certificate_number = fields.Char(string='Certificate Number')
    issuing_authority = fields.Char(string='Issuing Authority', required=True)
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    responsible_user_id = fields.Many2one('res.users', string='Responsible Person', default=lambda s: s.env.user)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', help='Set when this is a buyer-specific certification requirement.')
    attachment = fields.Binary(string='Certificate File', attachment=True)
    attachment_filename = fields.Char(string='Filename')
    status = fields.Selection([
        ('active', 'Active'), ('expiring_soon', 'Expiring Soon'), ('expired', 'Expired'),
    ], string='Status', compute='_compute_status', store=True, tracking=True)
    renewal_status = fields.Selection([
        ('not_started', 'Not Started'), ('in_progress', 'In Progress'), ('submitted', 'Submitted'), ('renewed', 'Renewed'),
    ], string='Renewal Status', default='not_started',
        help='Manual tracking of the renewal process, independent of the auto-computed expiry Status above.')
    is_suspended = fields.Boolean(string='Suspended', help='Certificate/license suspended by the issuing authority.')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('expiry_date')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.expiry_date:
                rec.status = 'active'
            elif rec.expiry_date < today:
                rec.status = 'expired'
            elif rec.expiry_date <= today + timedelta(days=30):
                rec.status = 'expiring_soon'
            else:
                rec.status = 'active'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('garment.compliance.certificate') or _('New')
        return super().create(vals_list)
