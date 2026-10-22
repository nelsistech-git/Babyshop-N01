# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityAudit(models.Model):
    """Quality Audit management — Internal / Buyer / Compliance / Process /
    Pre-Production / Inline / Social audits. This is the factory-floor and
    buyer process audit (distinct from garment_supplier's
    garment.supplier.audit, which is a supplier compliance audit). See
    Quality Audit Management (Garment QMS SRS sec. 33) and Buyer Quality
    Audit Management (Advanced QMS SRS sec. 34)."""
    _name = 'garment.quality.audit'
    _description = 'Garment Quality Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'audit_date desc'

    audit_no = fields.Char(string='Audit No.', copy=False, readonly=True, default=lambda s: _('New'))
    audit_type = fields.Selection([
        ('internal', 'Internal Audit'),
        ('buyer', 'Buyer Audit'),
        ('compliance', 'Compliance Audit'),
        ('process', 'Process Audit'),
        ('pre_production', 'Pre-Production Audit'),
        ('inline', 'Inline Audit'),
        ('social', 'Social Quality Audit'),
    ], string='Audit Type', required=True, default='internal')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer')
    style_id = fields.Many2one('garment.style', string='Style')
    supplier_id = fields.Many2one('garment.supplier', string='Supplier')
    production_order_id = fields.Char(string='Production Order Ref.',
                                       help='Soft reference — see IMPLEMENTATION_NOTES.md.')
    audit_date = fields.Date(string='Audit Date', default=fields.Date.context_today)
    auditor_id = fields.Many2one('res.users', string='Auditor', default=lambda s: s.env.user)
    score = fields.Float(string='Audit Score (%)')
    finding_ids = fields.One2many('garment.quality.audit.finding', 'audit_id', string='Findings')
    finding_count = fields.Integer(compute='_compute_finding_count')
    capa_ids = fields.One2many('garment.quality.capa', 'audit_id', string='CAPA')
    capa_count = fields.Integer(compute='_compute_capa_count')
    status = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
    ], string='Status', default='planned', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('finding_ids')
    def _compute_finding_count(self):
        for rec in self:
            rec.finding_count = len(rec.finding_ids)

    @api.depends('capa_ids')
    def _compute_capa_count(self):
        for rec in self:
            rec.capa_count = len(rec.capa_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('audit_no', _('New')) == _('New'):
                vals['audit_no'] = self.env['ir.sequence'].next_by_code('garment.quality.audit') or _('New')
        return super().create(vals_list)

    def action_view_findings(self):
        self.ensure_one()
        return {
            'name': _('Findings'), 'type': 'ir.actions.act_window', 'res_model': 'garment.quality.audit.finding',
            'view_mode': 'tree,form', 'domain': [('audit_id', '=', self.id)],
            'context': {'default_audit_id': self.id},
        }


class GarmentQualityAuditFinding(models.Model):
    _name = 'garment.quality.audit.finding'
    _description = 'Garment Quality Audit Finding'
    _order = 'sequence, id'

    audit_id = fields.Many2one('garment.quality.audit', string='Audit', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    finding = fields.Char(string='Finding', required=True)
    severity = fields.Selection([
        ('critical', 'Critical'),
        ('major', 'Major'),
        ('minor', 'Minor'),
        ('observation', 'Observation'),
    ], string='Severity', default='minor')
    corrective_action = fields.Char(string='Corrective Action')
    status = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='Status', default='open')
