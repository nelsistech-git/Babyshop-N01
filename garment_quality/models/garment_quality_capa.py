# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityCapa(models.Model):
    """CAPA — Corrective And Preventive Action. This is the general
    production-floor / quality-process CAPA (defects, inspections,
    complaints, audits). Supplier compliance-audit CAPA already exists as
    ``garment.supplier.capa`` in garment_supplier — this model is
    deliberately kept separate (different scope/trigger) but can optionally
    point at the supplier when a quality issue is supplier-caused. See CAPA
    Management System (base QMS SRS sec. 37, Garment QMS SRS sec. 31 and
    Advanced QMS SRS sec. 38)."""
    _name = 'garment.quality.capa'
    _description = 'Garment Quality CAPA (Corrective And Preventive Action)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    capa_no = fields.Char(string='CAPA No.', copy=False, readonly=True, default=lambda s: _('New'))
    source = fields.Selection([
        ('defect', 'Defect'),
        ('inspection', 'Inspection'),
        ('complaint', 'Buyer Complaint'),
        ('audit', 'Audit'),
        ('rca', 'Root Cause Analysis'),
        ('other', 'Other'),
    ], string='Source', default='defect', required=True)
    defect_id = fields.Many2one('garment.quality.defect', string='Defect')
    inspection_id = fields.Many2one('garment.quality.inspection', string='Inspection')
    complaint_id = fields.Many2one('garment.quality.complaint', string='Buyer Complaint')
    audit_id = fields.Many2one('garment.quality.audit', string='Audit')
    rca_ids = fields.One2many('garment.quality.rca', 'capa_id', string='Root Cause Analyses')
    style_id = fields.Many2one('garment.style', string='Style')
    supplier_id = fields.Many2one(
        'garment.supplier', string='Supplier',
        help='Set only when the corrective action targets a supplier-caused quality issue. For '
             'supplier compliance-audit CAPA, see garment_supplier.garment.supplier.capa instead.')
    department = fields.Selection([
        ('incoming', 'Incoming / Warehouse'),
        ('cutting', 'Cutting'),
        ('sewing', 'Sewing'),
        ('washing', 'Washing'),
        ('finishing', 'Finishing'),
        ('packing', 'Packing'),
        ('quality', 'Quality'),
    ], string='Department')

    problem_description = fields.Text(string='Problem Description', required=True)
    root_cause_method = fields.Selection([
        ('5why', '5 Why Analysis'),
        ('fishbone', 'Fishbone Diagram'),
        ('pareto', 'Pareto Analysis'),
        ('other', 'Other'),
    ], string='Root Cause Method')
    root_cause = fields.Text(string='Root Cause')
    corrective_action = fields.Text(string='Corrective Action')
    preventive_action = fields.Text(string='Preventive Action')
    responsible_id = fields.Many2one('res.users', string='Responsible Person')
    target_date = fields.Date(string='Target Date')
    verification_date = fields.Date(string='Verification Date')
    verified_by_id = fields.Many2one('res.users', string='Verified By')
    verification_result = fields.Selection([
        ('effective', 'Effective'),
        ('not_effective', 'Not Effective'),
    ], string='Verification Result')
    status = fields.Selection([
        ('open', 'Open'),
        ('root_cause', 'Root Cause Analysis'),
        ('action_planned', 'Action Planned'),
        ('in_progress', 'In Progress'),
        ('verification', 'Verification'),
        ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('capa_no', _('New')) == _('New'):
                vals['capa_no'] = self.env['ir.sequence'].next_by_code('garment.quality.capa') or _('New')
        return super().create(vals_list)

    def action_close(self):
        self.write({'status': 'closed'})
