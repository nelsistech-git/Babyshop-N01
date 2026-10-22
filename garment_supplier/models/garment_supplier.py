# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentSupplier(models.Model):
    """Supplier Master (SRS sections 6-10, 36) — garment.supplier. Linked
    1-to-1 with res.partner so it flows into Purchase/Invoicing/Portal,
    while keeping garment-industry supplier data on its own model —
    mirrors the garment.buyer pattern from Module 1. Inherits portal.mixin
    (SRS sections 19-20, 37-38 — Supplier Portal) so a supplier's linked
    partner can be given portal access scoped to its own record only."""
    _name = 'garment.supplier'
    _description = 'Garment Supplier'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'name'

    supplier_code = fields.Char(string='Supplier Code', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Supplier Name', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Related Contact', ondelete='restrict')
    supplier_type = fields.Selection([
        ('material', 'Material Supplier'), ('service', 'Service Supplier'),
        ('processing', 'Processing Supplier'), ('logistics', 'Logistics Supplier'),
        ('compliance', 'Compliance Supplier'),
    ], string='Supplier Type', required=True, tracking=True)
    category_id = fields.Many2one('garment.supplier.category', string='Category')
    registration_source = fields.Selection([
        ('internal', 'Internal Creation'), ('portal', 'Supplier Portal'), ('invitation', 'Invitation Link'),
    ], string='Registration Source', default='internal', tracking=True,
        help='How this supplier entered the system (SRS section 8 - Supplier Registration Management).')
    classification = fields.Selection([
        ('strategic', 'Strategic Supplier'), ('approved', 'Approved Supplier'),
        ('temporary', 'Temporary Supplier'), ('blocked', 'Blocked Supplier'),
    ], string='Classification', default='temporary', tracking=True)

    country_id = fields.Many2one('res.country', string='Country')
    address = fields.Char(string='Address')
    contact_person = fields.Char(string='Contact Person')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    website = fields.Char(string='Website')
    tax_id = fields.Char(string='Tax ID')
    registration_number = fields.Char(string='Registration Number')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')

    # Registration / Company Details (SRS section 8)
    year_established = fields.Integer(string='Year Established')
    factory_location = fields.Char(string='Factory Location')
    production_capacity = fields.Char(string='Production Capacity')
    employee_count = fields.Integer(string='Employee Count')
    monthly_capacity = fields.Char(string='Monthly Capacity')
    export_experience = fields.Char(string='Export Experience')
    major_customers = fields.Char(string='Major Customers')

    status = fields.Selection([
        ('registration', 'Registration'), ('purchase_review', 'Purchase Review'),
        ('quality_review', 'Quality Review'), ('compliance_review', 'Compliance Review'),
        ('management_approval', 'Management Approval'), ('active', 'Active'), ('inactive', 'Inactive'),
    ], string='Status', default='registration', tracking=True, group_expand='_expand_states')

    compliance_status = fields.Selection([
        ('compliant', 'Compliant'), ('minor_issues', 'Minor Issues'), ('non_compliant', 'Non-Compliant'),
        ('under_review', 'Under Review'),
    ], string='Compliance Status', default='under_review', tracking=True)

    # Supplier Approval Workflow stage stamps (SRS sections 10, 37, 39 —
    # each stage is approved by the role named in the SRS Access Matrix).
    purchase_review_by_id = fields.Many2one('res.users', string='Purchase Review By', readonly=True, copy=False)
    purchase_review_date = fields.Date(string='Purchase Review Date', readonly=True, copy=False)
    quality_review_by_id = fields.Many2one('res.users', string='Quality Review By', readonly=True, copy=False)
    quality_review_date = fields.Date(string='Quality Review Date', readonly=True, copy=False)
    compliance_review_by_id = fields.Many2one('res.users', string='Compliance Review By', readonly=True, copy=False)
    compliance_review_date = fields.Date(string='Compliance Review Date', readonly=True, copy=False)
    management_approval_by_id = fields.Many2one('res.users', string='Management Approval By',
                                                  readonly=True, copy=False)
    management_approval_date = fields.Date(string='Management Approval Date', readonly=True, copy=False)

    # Bangladesh Garment Supplier Standards — Compliance Requirements
    # (SRS section 45): tracked as simple checklist flags, consistent with
    # the boolean-checklist pattern already used on garment.supplier.audit.
    cert_bsci = fields.Boolean(string='BSCI')
    cert_sedex = fields.Boolean(string='SEDEX')
    cert_wrap = fields.Boolean(string='WRAP')
    cert_iso = fields.Boolean(string='ISO')
    cert_oeko_tex = fields.Boolean(string='OEKO-TEX')
    cert_gots = fields.Boolean(string='GOTS')

    # Blacklist (SRS section 40, embedded rather than a separate model)
    is_blacklisted = fields.Boolean(string='Blacklisted', default=False, tracking=True)
    blacklist_reason = fields.Selection([
        ('poor_quality', 'Poor Quality'), ('repeated_delay', 'Repeated Delay'), ('fraud', 'Fraud Issue'),
        ('compliance_failure', 'Compliance Failure'), ('contract_violation', 'Contract Violation'),
    ], string='Blacklist Reason')
    blacklist_date = fields.Date(string='Blacklist Date')
    blacklisted_by_id = fields.Many2one('res.users', string='Blacklisted By')
    blacklist_evidence = fields.Binary(string='Evidence Document', attachment=True)

    # Relations
    product_ids = fields.One2many('garment.supplier.product', 'supplier_id', string='Product Catalog')
    document_ids = fields.One2many('garment.supplier.document', 'supplier_id', string='Documents')
    rating_ids = fields.One2many('garment.supplier.rating', 'supplier_id', string='Performance Ratings')
    audit_ids = fields.One2many('garment.supplier.audit', 'supplier_id', string='Audits')
    capa_ids = fields.One2many('garment.supplier.capa', 'supplier_id', string='Corrective Actions')
    risk_ids = fields.One2many('garment.supplier.risk', 'supplier_id', string='Risk Records')

    # Latest score / ranking (SRS sections 17, 42-43)
    rating = fields.Float(string='Latest Score (%)', compute='_compute_latest_rating', store=True)
    ranking = fields.Selection([
        ('platinum', 'Platinum (90-100%)'), ('gold', 'Gold (80-89%)'),
        ('silver', 'Silver (70-79%)'), ('restricted', 'Restricted (< 70%)'),
    ], string='Ranking', compute='_compute_latest_rating', store=True)
    risk_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], string='Risk Level', compute='_compute_risk_level', store=True, tracking=True)

    # Purchase transaction summary (reads Module 9 — no duplicate models)
    rfq_count = fields.Integer(compute='_compute_purchase_counts')
    po_count = fields.Integer(compute='_compute_purchase_counts')
    delivery_count = fields.Integer(compute='_compute_purchase_counts')
    on_time_delivery_pct = fields.Float(string='On-Time Delivery %', compute='_compute_purchase_counts')

    # AI Assist
    ai_risk_prediction_note = fields.Text(string='AI Risk Prediction', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    document_count = fields.Integer(compute='_compute_counts')
    expiring_document_count = fields.Integer(compute='_compute_counts')

    # Supplier Portal Dashboard — Payment Status (SRS section 20), read
    # from Module 12 (garment_finance)'s garment.payment, which links to
    # this model directly — no duplicate payment tracking here.
    payment_pending_count = fields.Integer(string='Pending Payments', compute='_compute_payment_summary')
    payment_paid_count = fields.Integer(string='Paid Invoices', compute='_compute_payment_summary')
    payment_due_amount = fields.Monetary(string='Due Amount', compute='_compute_payment_summary',
                                          currency_field='currency_id')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('supplier_code_uniq', 'unique(supplier_code, company_id)', 'Supplier Code must be unique per company!'),
    ]

    @api.depends('rating_ids.final_score')
    def _compute_latest_rating(self):
        for rec in self:
            latest = rec.rating_ids.sorted('rating_date', reverse=True)[:1]
            score = latest.final_score if latest else 0.0
            rec.rating = score
            if score >= 90:
                rec.ranking = 'platinum'
            elif score >= 80:
                rec.ranking = 'gold'
            elif score >= 70:
                rec.ranking = 'silver'
            else:
                rec.ranking = 'restricted'

    @api.depends('risk_ids.risk_level', 'is_blacklisted')
    def _compute_risk_level(self):
        order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        for rec in self:
            if rec.is_blacklisted:
                rec.risk_level = 'critical'
                continue
            open_risks = rec.risk_ids.filtered(lambda r: r.status != 'closed')
            if not open_risks:
                rec.risk_level = 'low'
                continue
            rec.risk_level = max(open_risks.mapped('risk_level'), key=lambda l: order.get(l, 0))

    def _compute_purchase_counts(self):
        Rfq = self.env['garment.purchase.rfq']
        Po = self.env['garment.purchase.order']
        Delivery = self.env['garment.purchase.delivery']
        for rec in self:
            partner = rec.partner_id
            rec.rfq_count = Rfq.search_count([('supplier_id', '=', partner.id)]) if partner else 0
            rec.po_count = Po.search_count([('supplier_id', '=', partner.id)]) if partner else 0
            deliveries = Delivery.search([('supplier_id', '=', partner.id)]) if partner else Delivery.browse()
            rec.delivery_count = len(deliveries)
            on_time = deliveries.filtered(lambda d: d.delay_days <= 0)
            rec.on_time_delivery_pct = (len(on_time) / len(deliveries) * 100.0) if deliveries else 0.0

    @api.depends('document_ids.expiry_status')
    def _compute_counts(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)
            rec.expiring_document_count = len(rec.document_ids.filtered(
                lambda d: d.expiry_status in ('expiring_soon', 'expired')))

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    def _compute_payment_summary(self):
        # garment_finance already depends on garment_supplier (garment.payment
        # has a structural Many2one to garment.supplier) — adding a reverse
        # 'garment_finance' dependency here would create a circular module
        # dependency, so this reads garment.payment defensively via the
        # registry instead of a hard depends (same pattern used elsewhere in
        # the suite, e.g. garment_techpack's BOM smart button).
        Payment = self.env.registry.models.get('garment.payment') and self.env['garment.payment'].sudo()
        for rec in self:
            if Payment is None or not rec.id:
                rec.payment_pending_count = 0
                rec.payment_paid_count = 0
                rec.payment_due_amount = 0.0
                continue
            payments = Payment.search([('supplier_id', '=', rec.id)])
            rec.payment_pending_count = len(payments.filtered(
                lambda p: p.payment_status in ('unpaid', 'partially_paid', 'overdue')))
            rec.payment_paid_count = len(payments.filtered(lambda p: p.payment_status == 'paid'))
            rec.payment_due_amount = sum(payments.mapped('outstanding_amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('supplier_code', _('New')) == _('New'):
                vals['supplier_code'] = self.env['ir.sequence'].next_by_code('garment.supplier') or _('New')
        return super().create(vals_list)

    def action_create_related_partner(self):
        Partner = self.env['res.partner']
        for rec in self:
            if rec.partner_id:
                continue
            partner = Partner.create({
                'name': rec.name, 'is_company': True, 'email': rec.email, 'phone': rec.phone,
                'street': rec.address, 'country_id': rec.country_id.id, 'website': rec.website,
                'supplier_rank': 1,
            })
            rec.partner_id = partner.id
        return True

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/my/supplier'

    # ------------------------------------------------------------------
    # Supplier Approval Workflow (SRS sections 10, 37, 39):
    # Registration -> Purchase Review -> Quality Review -> Compliance
    # Review -> Management Approval -> Active. Each stage is approved by
    # the role named in the SRS section 37 Access Matrix.
    # ------------------------------------------------------------------
    def action_submit_purchase_review(self):
        for rec in self:
            if rec.status != 'registration':
                raise UserError(_('Only a supplier in Registration can be submitted for Purchase Review.'))
            rec.status = 'purchase_review'

    def action_approve_purchase_review(self):
        if not self.env.user.has_group('garment_supplier.group_supplier_purchase_manager'):
            raise UserError(_('Only a Purchase Manager can approve the Purchase Review stage.'))
        for rec in self:
            if rec.status != 'purchase_review':
                raise UserError(_('Supplier is not currently in Purchase Review.'))
            rec.write({
                'status': 'quality_review',
                'purchase_review_by_id': self.env.user.id,
                'purchase_review_date': fields.Date.context_today(rec),
            })

    def action_approve_quality_review(self):
        if not (self.env.user.has_group('garment_supplier.group_supplier_qa_manager')
                or self.env.user.has_group('garment_supplier.group_supplier_purchase_manager')):
            raise UserError(_('Only a QA Manager can approve the Quality Review stage.'))
        for rec in self:
            if rec.status != 'quality_review':
                raise UserError(_('Supplier is not currently in Quality Review.'))
            rec.write({
                'status': 'compliance_review',
                'quality_review_by_id': self.env.user.id,
                'quality_review_date': fields.Date.context_today(rec),
            })

    def action_approve_compliance_review(self):
        if not (self.env.user.has_group('garment_supplier.group_supplier_compliance_manager')
                or self.env.user.has_group('garment_supplier.group_supplier_purchase_manager')):
            raise UserError(_('Only a Compliance Manager can approve the Compliance Review stage.'))
        for rec in self:
            if rec.status != 'compliance_review':
                raise UserError(_('Supplier is not currently in Compliance Review.'))
            rec.write({
                'status': 'management_approval',
                'compliance_review_by_id': self.env.user.id,
                'compliance_review_date': fields.Date.context_today(rec),
            })

    def action_approve_management(self):
        if not self.env.user.has_group('garment_supplier.group_supplier_top_management'):
            raise UserError(_('Only Top Management can grant the final activation approval.'))
        for rec in self:
            if rec.status != 'management_approval':
                raise UserError(_('Supplier is not currently awaiting Management Approval.'))
            rec.write({
                'status': 'active',
                'management_approval_by_id': self.env.user.id,
                'management_approval_date': fields.Date.context_today(rec),
            })

    def action_activate(self):
        self.write({'status': 'active'})

    def action_blacklist(self):
        self.write({'is_blacklisted': True, 'blacklist_date': fields.Date.context_today(self),
                    'blacklisted_by_id': self.env.user.id, 'classification': 'blocked'})

    def action_remove_blacklist(self):
        self.write({'is_blacklisted': False})

    def action_run_ai_analysis(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            note = ai_engine.predict_supplier_risk(rec)
            rec.write({'ai_risk_prediction_note': note, 'ai_last_run': fields.Datetime.now()})
        return True
