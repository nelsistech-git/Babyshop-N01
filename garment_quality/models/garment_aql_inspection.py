# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentAqlInspection(models.Model):
    """AQL Sampling & Final Inspection — international buyer inspection
    standard (AQL 1.0/1.5/2.5/4.0) with automatic accept/reject decision and
    buyer portal approval. See AQL Inspection System (base QMS SRS sec.
    33-35), AQL Sampling Management System (Garment QMS SRS sec. 26-27) and
    AQL Inspection System (Advanced QMS SRS sec. 31-33)."""
    _name = 'garment.aql.inspection'
    _description = 'Garment AQL / Final Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'inspection_date desc'

    aql_no = fields.Char(string='AQL Inspection No.', copy=False, readonly=True, default=lambda s: _('New'))
    inspection_type = fields.Selection([
        ('final', 'Final Inspection'),
        ('pre_production', 'Pre-Production Audit'),
        ('inline_audit', 'Inline Audit'),
        ('social', 'Social Quality Audit'),
    ], string='Inspection Type', default='final', required=True)
    inspection_scope = fields.Selection([
        ('full', '100% Inspection'),
        ('sampling', 'Sampling Inspection'),
        ('buyer', 'Buyer Inspection'),
    ], string='Inspection Scope', default='sampling')

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    order_reference = fields.Char(string='Order / PO Reference',
                                   help='Free-text order reference pending the future Order Management module.')
    production_order_id = fields.Char(string='Production Order Ref.',
                                       help='Soft reference — see IMPLEMENTATION_NOTES.md.')
    supplier_id = fields.Many2one('garment.supplier', string='Supplier')
    inspector_id = fields.Many2one('res.users', string='Inspector / Auditor', default=lambda s: s.env.user)
    inspection_date = fields.Datetime(string='Inspection Date', default=fields.Datetime.now, tracking=True)

    lot_size = fields.Float(string='Lot Size (PCS)', required=True)
    sample_size = fields.Float(string='Sample Size (PCS)')
    inspection_level = fields.Selection([
        ('s1', 'Special Level S-1'),
        ('s2', 'Special Level S-2'),
        ('s3', 'Special Level S-3'),
        ('s4', 'Special Level S-4'),
        ('g1', 'General Level I'),
        ('g2', 'General Level II'),
        ('g3', 'General Level III'),
    ], string='Inspection Level', default='g2')
    aql_critical = fields.Float(string='AQL - Critical', default=0.0)
    aql_major = fields.Float(string='AQL - Major', default=2.5)
    aql_minor = fields.Float(string='AQL - Minor', default=4.0)
    accept_number_major = fields.Integer(string='Accept Number (Major)')
    reject_number_major = fields.Integer(string='Reject Number (Major)')
    accept_number_minor = fields.Integer(string='Accept Number (Minor)')
    reject_number_minor = fields.Integer(string='Reject Number (Minor)')

    critical_defect_qty = fields.Integer(string='Critical Defects Found', default=0)
    major_defect_qty = fields.Integer(string='Major Defects Found', compute='_compute_defect_qty', store=True)
    minor_defect_qty = fields.Integer(string='Minor Defects Found', compute='_compute_defect_qty', store=True)
    defect_ids = fields.One2many('garment.quality.defect', 'aql_inspection_id', string='Defects Found')

    result = fields.Selection([
        ('pass', 'Accepted (Pass)'),
        ('fail', 'Rejected (Fail)'),
    ], string='Result', compute='_compute_result', store=True, tracking=True)

    carton_qty = fields.Integer(string='Carton Quantity')
    packing_ok = fields.Boolean(string='Packing OK')
    documentation_ok = fields.Boolean(string='Documentation OK')

    buyer_approval_status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Buyer Approval', default='pending', tracking=True)
    buyer_comments = fields.Text(string='Buyer Comments')
    shipment_release = fields.Boolean(string='Shipment Released', default=False, tracking=True, copy=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('inspecting', 'Inspecting'),
        ('completed', 'Completed'),
        ('buyer_review', 'Buyer Review'),
        ('released', 'Shipment Released'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('defect_ids', 'defect_ids.severity', 'defect_ids.quantity')
    def _compute_defect_qty(self):
        for rec in self:
            defects = rec.defect_ids
            rec.major_defect_qty = int(sum(defects.filtered(lambda d: d.severity == 'major').mapped('quantity')))
            rec.minor_defect_qty = int(sum(defects.filtered(lambda d: d.severity == 'minor').mapped('quantity')))

    @api.depends('critical_defect_qty', 'major_defect_qty', 'minor_defect_qty',
                 'reject_number_major', 'reject_number_minor')
    def _compute_result(self):
        # AQL Decision Engine — IF Defect <= Accept Level THEN PASS ELSE FAIL (base QMS SRS sec. 34)
        for rec in self:
            if rec.critical_defect_qty > 0:
                rec.result = 'fail'
            elif rec.reject_number_major and rec.major_defect_qty >= rec.reject_number_major:
                rec.result = 'fail'
            elif rec.reject_number_minor and rec.minor_defect_qty >= rec.reject_number_minor:
                rec.result = 'fail'
            else:
                rec.result = 'pass'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('aql_no', _('New')) == _('New'):
                vals['aql_no'] = self.env['ir.sequence'].next_by_code('garment.aql.inspection') or _('New')
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'inspecting'})

    def action_complete(self):
        for rec in self:
            if rec.state != 'inspecting':
                raise UserError(_('Only an inspection in progress can be completed.'))
            rec.state = 'completed' if rec.result == 'pass' else 'rejected'

    def action_submit_buyer(self):
        self.write({'state': 'buyer_review', 'buyer_approval_status': 'pending'})

    def action_buyer_approve(self):
        self.write({'buyer_approval_status': 'approved'})

    def action_buyer_reject(self):
        self.write({'buyer_approval_status': 'rejected', 'state': 'rejected'})

    def action_release_shipment(self):
        for rec in self:
            if rec.result != 'pass' or rec.buyer_approval_status != 'approved':
                raise UserError(_('Shipment can only be released after a Pass result and Buyer Approval.'))
        self.write({'shipment_release': True, 'state': 'released'})

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/my/aql_inspections/%s' % rec.id
