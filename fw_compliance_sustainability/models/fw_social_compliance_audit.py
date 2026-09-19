# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwSocialComplianceAudit(models.Model):
    _name = 'fw.social.compliance.audit'
    _description = 'Footwear Factory Internal Social Compliance Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'audit_date desc'

    name = fields.Char(string='Audit Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.social.compliance.audit') or 'New')
    factory_id = fields.Many2one('fw.factory', string='Factory', required=True, tracking=True)

    audit_type = fields.Selection([
        ('internal_self_assessment', 'Internal Self-Assessment'),
        ('third_party', 'Third-Party Pre-Audit'),
        ('government_inspection', 'Government Inspection'),
    ], string='Audit Type', required=True, default='internal_self_assessment')

    audit_date = fields.Date(string='Audit Date', required=True, default=fields.Date.context_today)
    auditor_name = fields.Char(string='Auditor / Team')

    score = fields.Float(string='Score (0-100)')
    result = fields.Selection([
        ('pass', 'Pass'),
        ('pass_with_cap', 'Pass with CAP'),
        ('fail', 'Fail'),
    ], string='Result', tracking=True)

    findings = fields.Text(string='Findings')
    cap_line_ids = fields.One2many('fw.social.compliance.cap.line', 'audit_id',
                                    string='Corrective Action Plan')
    open_cap_count = fields.Integer(string='Open CAP Items', compute='_compute_cap_counts',
                                     store=True)
    closed_cap_count = fields.Integer(string='Closed CAP Items', compute='_compute_cap_counts',
                                       store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.social.compliance.audit') or 'New'
        return super().create(vals_list)

    @api.depends('cap_line_ids.status')
    def _compute_cap_counts(self):
        for rec in self:
            rec.open_cap_count = len(rec.cap_line_ids.filtered(
                lambda l: l.status != 'closed'))
            rec.closed_cap_count = len(rec.cap_line_ids.filtered(
                lambda l: l.status == 'closed'))

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class FwSocialComplianceCapLine(models.Model):
    _name = 'fw.social.compliance.cap.line'
    _description = 'Internal Audit Corrective Action Plan Line'
    _order = 'target_date'

    audit_id = fields.Many2one('fw.social.compliance.audit', string='Audit', required=True,
                                ondelete='cascade')
    finding = fields.Char(string='Finding / Non-Conformance', required=True)
    corrective_action = fields.Char(string='Corrective Action')
    responsible_id = fields.Many2one('hr.employee', string='Responsible')
    target_date = fields.Date(string='Target Closure Date')
    status = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ], string='Status', default='open')
    closed_date = fields.Date(string='Closed Date')
    remarks = fields.Char(string='Remarks')
