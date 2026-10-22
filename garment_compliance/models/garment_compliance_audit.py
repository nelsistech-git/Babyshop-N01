# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Audit Management System (SRS1 secs. 9-12, SRS2 secs. 13-17, 65-67) —
garment.compliance.audit / garment.compliance.audit.line /
garment.compliance.finding.

This is the FACTORY-level compliance audit (Buyer/Social/Safety/Fire/
Environmental/Internal/Government/Certification audits of the factory
itself) — distinct from garment_supplier.garment.supplier.audit (audits
OF suppliers) and garment_quality.garment.quality.audit (production-floor
/ process quality audits). All three are deliberately separate models
because they audit different subjects with different checklists.
"""
from odoo import api, fields, models, _

AUDIT_STAGES = ['planning', 'checklist_review', 'execution', 'finding_review', 'corrective_action', 'closed']


class GarmentComplianceAudit(models.Model):
    _name = 'garment.compliance.audit'
    _description = 'Garment Compliance Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'audit_date desc'

    audit_no = fields.Char(string='Audit No.', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Audit Name', required=True)
    audit_type = fields.Selection([
        ('buyer', 'Buyer Audit'),
        ('social', 'Social Audit'),
        ('safety', 'Safety Audit'),
        ('fire', 'Fire Audit'),
        ('environmental', 'Environmental Audit'),
        ('internal', 'Internal Audit'),
        ('government', 'Government Audit'),
        ('certification', 'Certification Audit'),
    ], string='Audit Type', required=True, default='internal', tracking=True)
    standard_id = fields.Many2one('garment.compliance.standard', string='Standard')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', help='Set for buyer-commissioned audits.')
    department_id = fields.Many2one('garment.hr.department', string='Department')
    auditor_id = fields.Many2one('res.users', string='Internal Auditor', default=lambda s: s.env.user)
    external_auditor = fields.Char(string='External Auditor / Firm')
    audit_date = fields.Date(string='Audit Date', default=fields.Date.context_today, tracking=True)
    scope = fields.Text(string='Scope')

    checklist_line_ids = fields.One2many('garment.compliance.audit.line', 'audit_id', string='Checklist')
    checklist_total = fields.Integer(compute='_compute_checklist_score', store=True)
    checklist_compliant = fields.Integer(compute='_compute_checklist_score', store=True)
    score = fields.Float(string='Compliance Score (%)', compute='_compute_checklist_score', store=True,
                          help='Completed Requirements / Total Requirements x 100 (SRS2 sec. 17 formula). '
                               'Recomputed from the checklist; overridable for externally-scored buyer audits.',
                          readonly=False)
    finding_ids = fields.One2many('garment.compliance.finding', 'audit_id', string='Findings')
    finding_count = fields.Integer(compute='_compute_finding_count')
    open_finding_count = fields.Integer(compute='_compute_finding_count')
    capa_ids = fields.One2many('garment.compliance.capa', 'audit_id', string='Corrective Actions')
    capa_count = fields.Integer(compute='_compute_capa_count')
    status = fields.Selection([
        ('planning', 'Planning'),
        ('checklist_review', 'Checklist Review'),
        ('execution', 'Execution'),
        ('finding_review', 'Finding Identification'),
        ('corrective_action', 'Corrective Action'),
        ('closed', 'Audit Closure'),
    ], string='Status', default='planning', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('checklist_line_ids.complied')
    def _compute_checklist_score(self):
        for rec in self:
            total = len(rec.checklist_line_ids)
            compliant = len(rec.checklist_line_ids.filtered('complied'))
            rec.checklist_total = total
            rec.checklist_compliant = compliant
            if total:
                rec.score = compliant / total * 100.0
            # else: leave any manually-entered score (e.g. from an external
            # buyer audit report) untouched rather than overwriting it.

    @api.depends('finding_ids.status')
    def _compute_finding_count(self):
        for rec in self:
            rec.finding_count = len(rec.finding_ids)
            rec.open_finding_count = len(rec.finding_ids.filtered(lambda f: f.status != 'closed'))

    @api.depends('capa_ids')
    def _compute_capa_count(self):
        for rec in self:
            rec.capa_count = len(rec.capa_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('audit_no', _('New')) == _('New'):
                vals['audit_no'] = self.env['ir.sequence'].next_by_code('garment.compliance.audit') or _('New')
        return super().create(vals_list)

    def action_next_stage(self):
        for rec in self:
            idx = AUDIT_STAGES.index(rec.status)
            if idx < len(AUDIT_STAGES) - 1:
                rec.status = AUDIT_STAGES[idx + 1]

    def action_view_findings(self):
        self.ensure_one()
        return {
            'name': _('Findings'), 'type': 'ir.actions.act_window', 'res_model': 'garment.compliance.finding',
            'view_mode': 'tree,form', 'domain': [('audit_id', '=', self.id)],
            'context': {'default_audit_id': self.id},
        }

    def action_view_capa(self):
        self.ensure_one()
        return {
            'name': _('Corrective Actions'), 'type': 'ir.actions.act_window', 'res_model': 'garment.compliance.capa',
            'view_mode': 'tree,form', 'domain': [('audit_id', '=', self.id)],
            'context': {'default_audit_id': self.id},
        }


class GarmentComplianceAuditLine(models.Model):
    _name = 'garment.compliance.audit.line'
    _description = 'Garment Compliance Audit Checklist Line'
    _order = 'sequence, id'

    audit_id = fields.Many2one('garment.compliance.audit', string='Audit', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    requirement_id = fields.Many2one('garment.compliance.requirement', string='Requirement')
    checklist_item = fields.Char(string='Checklist Item', required=True)
    complied = fields.Boolean(string='Complied')
    remarks = fields.Char(string='Remarks')

    @api.onchange('requirement_id')
    def _onchange_requirement_id(self):
        if self.requirement_id and not self.checklist_item:
            self.checklist_item = self.requirement_id.name


class GarmentComplianceFinding(models.Model):
    _name = 'garment.compliance.finding'
    _description = 'Garment Compliance Audit Finding'
    _inherit = ['mail.thread']
    _order = 'due_date'

    finding_no = fields.Char(string='Finding No.', copy=False, readonly=True, default=lambda s: _('New'))
    audit_id = fields.Many2one('garment.compliance.audit', string='Audit', required=True, ondelete='cascade')
    category = fields.Selection([
        ('hr', 'HR Compliance'), ('safety', 'Safety Compliance'), ('fire', 'Fire Safety'),
        ('factory', 'Factory / Building'), ('environmental', 'Environmental'), ('government', 'Government'),
        ('other', 'Other'),
    ], string='Category', default='hr')
    description = fields.Text(string='Finding Description', required=True)
    severity = fields.Selection([
        ('critical', 'Critical - Immediate Action'), ('major', 'Major - High Priority'), ('minor', 'Minor - Improvement'),
    ], string='Severity', default='minor', required=True, tracking=True)
    responsible_department_id = fields.Many2one('garment.hr.department', string='Responsible Department')
    responsible_user_id = fields.Many2one('res.users', string='Responsible Person')
    due_date = fields.Date(string='Due Date')
    status = fields.Selection([
        ('open', 'Open'), ('in_progress', 'In Progress'), ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True)
    capa_ids = fields.One2many('garment.compliance.capa', 'finding_id', string='Corrective Actions')
    capa_count = fields.Integer(compute='_compute_capa_count')

    def _compute_capa_count(self):
        for rec in self:
            rec.capa_count = len(rec.capa_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('finding_no', _('New')) == _('New'):
                vals['finding_no'] = self.env['ir.sequence'].next_by_code('garment.compliance.finding') or _('New')
        return super().create(vals_list)

    def action_close(self):
        self.write({'status': 'closed'})
