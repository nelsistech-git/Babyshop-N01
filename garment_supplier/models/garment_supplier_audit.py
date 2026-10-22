# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentSupplierAudit(models.Model):
    """Supplier Audit Management (SRS section 27) — garment.supplier.audit."""
    _name = 'garment.supplier.audit'
    _description = 'Garment Supplier Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'audit_date desc'

    audit_number = fields.Char(string='Audit Number', copy=False, readonly=True, default=lambda s: _('New'))
    supplier_id = fields.Many2one('garment.supplier', string='Supplier', required=True, ondelete='cascade')
    audit_type = fields.Selection([
        ('factory', 'Factory Audit'), ('quality', 'Quality Audit'), ('social', 'Social Audit'),
        ('environmental', 'Environmental Audit'),
    ], string='Audit Type', required=True)
    audit_date = fields.Date(string='Audit Date', default=fields.Date.context_today)
    auditor_id = fields.Many2one('res.users', string='Auditor')

    # Factory Checklist
    chk_production_capacity = fields.Boolean(string='Production Capacity OK')
    chk_machine_condition = fields.Boolean(string='Machine Condition OK')
    chk_safety_system = fields.Boolean(string='Safety System OK')
    # Quality Checklist
    chk_qc_process = fields.Boolean(string='QC Process OK')
    chk_testing_facility = fields.Boolean(string='Testing Facility OK')
    chk_documentation = fields.Boolean(string='Documentation OK')
    # Compliance Checklist
    chk_worker_safety = fields.Boolean(string='Worker Safety OK')
    chk_environment = fields.Boolean(string='Environment OK')
    chk_certifications = fields.Boolean(string='Certifications OK')

    findings = fields.Text(string='Findings')
    status = fields.Selection([
        ('planning', 'Audit Planning'), ('execution', 'Audit Execution'), ('findings', 'Findings'),
        ('corrective_action', 'Corrective Action'), ('closed', 'Closure'),
    ], string='Status', default='planning', tracking=True)
    capa_ids = fields.One2many('garment.supplier.capa', 'audit_id', string='Corrective Actions')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('audit_number', _('New')) == _('New'):
                vals['audit_number'] = self.env['ir.sequence'].next_by_code('garment.supplier.audit') or _('New')
        return super().create(vals_list)

    def action_next_stage(self):
        flow = ['planning', 'execution', 'findings', 'corrective_action', 'closed']
        for rec in self:
            idx = flow.index(rec.status)
            if idx < len(flow) - 1:
                rec.status = flow[idx + 1]
