# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

DEFAULT_CHECKLIST_ITEMS = [
    'Door Keys', 'Access Cards', 'Parking', 'Electricity Meter', 'Water Meter',
    'Gas Documents', 'Utility Documents', 'Property Documents',
    'Warranty Documents', 'Maintenance Documents', 'Building Rules', 'Other',
]


class RealEstateHandover(models.Model):
    """The handover process for a sold unit: verifies financial, QC and
    documentation clearance before the unit can be marked Handed Over.
    Deliberately reads its clearance inputs from the Sale Agreement,
    Installment/Collection records and QC Inspections already built in
    earlier phases rather than duplicating any of that data."""
    _name = 'real.estate.handover'
    _description = 'Real Estate Handover'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Handover Number', copy=False, tracking=True,
                        default='New', readonly=True)
    unit_id = fields.Many2one('real.estate.unit', string='Unit', required=True,
                               tracking=True, ondelete='restrict')
    project_id = fields.Many2one(related='unit_id.project_id', store=True, readonly=True)
    building_id = fields.Many2one(related='unit_id.building_id', store=True, readonly=True)
    sale_agreement_id = fields.Many2one('real.estate.sale.agreement', string='Sale Agreement',
                                         tracking=True, domain="[('unit_id', '=', unit_id)]")
    customer_id = fields.Many2one(related='sale_agreement_id.customer_id', store=True, readonly=True)

    handover_date = fields.Date(string='Handover Date', default=fields.Date.context_today)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('handover_requested', 'Handover Requested'),
        ('financial_clearance', 'Financial Clearance'),
        ('qc_clearance', 'QC Clearance'),
        ('documentation_clearance', 'Documentation Clearance'),
        ('final_inspection', 'Final Inspection'),
        ('approved', 'Approved'),
        ('handed_over', 'Handed Over'),
        ('completed', 'Completed'),
    ], string='State', default='draft', tracking=True, required=True, copy=False)

    # ---- Financial Clearance ----
    total_price = fields.Monetary(related='sale_agreement_id.net_price', readonly=True)
    total_paid = fields.Monetary(string='Total Paid', compute='_compute_financial')
    approved_adjustment = fields.Monetary(string='Approved Adjustment',
                                           help='Negotiated waivers/credits approved by management.')
    outstanding_balance = fields.Monetary(string='Outstanding Balance', compute='_compute_financial')
    financial_override = fields.Boolean(string='Authorized Override',
                                         help='Allows handover to proceed with an outstanding balance.')
    financial_override_reason = fields.Text(string='Override Reason')
    financial_cleared = fields.Boolean(string='Financial Cleared', compute='_compute_financial')

    # ---- QC Clearance ----
    open_critical_defect_count = fields.Integer(string='Open Critical Defects', compute='_compute_qc')
    final_qc_passed = fields.Boolean(string='Final QC Passed', compute='_compute_qc')
    qc_cleared = fields.Boolean(string='QC Cleared', compute='_compute_qc')

    # ---- Documentation Clearance ----
    doc_agreement_signed = fields.Boolean(string='Agreement Signed')
    doc_customer_documents = fields.Boolean(string='Customer Documents Received')
    doc_payment_records = fields.Boolean(string='Payment Records Complete')
    doc_legal_documents = fields.Boolean(string='Required Legal Documents Complete')
    documentation_cleared = fields.Boolean(string='Documentation Cleared', compute='_compute_documentation')

    # ---- Checklist ----
    checklist_line_ids = fields.One2many('real.estate.handover.checklist.line', 'handover_id',
                                          string='Handover Checklist')

    # ---- Certificate details ----
    keys_delivered = fields.Char(string='Keys Delivered')
    parking_slot = fields.Char(string='Parking Slot(s)')
    electricity_meter_number = fields.Char(string='Electricity Meter No.')
    water_meter_number = fields.Char(string='Water Meter No.')
    gas_meter_number = fields.Char(string='Gas Meter No.')
    remarks = fields.Text(string='Remarks')

    customer_signed = fields.Boolean(string='Customer Signed')
    customer_signed_date = fields.Date(string='Customer Signature Date')
    company_representative_id = fields.Many2one('res.users', string='Company Representative',
                                                  default=lambda self: self.env.user)
    company_signed = fields.Boolean(string='Company Representative Signed')
    company_signed_date = fields.Date(string='Company Signature Date')

    company_id = fields.Many2one(related='unit_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)

    @api.depends('sale_agreement_id', 'approved_adjustment')
    def _compute_financial(self):
        for rec in self:
            paid = 0.0
            if rec.sale_agreement_id:
                collections = self.env['real.estate.collection'].search([
                    ('sale_agreement_id', '=', rec.sale_agreement_id.id),
                    ('state', '=', 'confirmed'),
                ])
                paid = sum(collections.mapped('amount'))
            rec.total_paid = paid
            outstanding = (rec.total_price or 0.0) - paid - rec.approved_adjustment
            rec.outstanding_balance = outstanding
            rec.financial_cleared = outstanding <= 0.01 or rec.financial_override

    @api.depends('unit_id.defect_ids.status', 'unit_id.defect_ids.severity',
                 'unit_id.qc_inspection_ids.result', 'unit_id.qc_inspection_ids.inspection_type')
    def _compute_qc(self):
        for rec in self:
            defects = rec.unit_id.defect_ids.filtered(
                lambda d: d.severity == 'critical' and d.status != 'closed')
            rec.open_critical_defect_count = len(defects)
            final_inspections = rec.unit_id.qc_inspection_ids.filtered(
                lambda i: i.inspection_type == 'final')
            rec.final_qc_passed = bool(final_inspections) and all(
                i.result == 'passed' for i in final_inspections)
            rec.qc_cleared = rec.open_critical_defect_count == 0 and rec.final_qc_passed

    @api.depends('doc_agreement_signed', 'doc_customer_documents', 'doc_payment_records',
                 'doc_legal_documents')
    def _compute_documentation(self):
        for rec in self:
            rec.documentation_cleared = bool(
                rec.doc_agreement_signed and rec.doc_customer_documents and
                rec.doc_payment_records and rec.doc_legal_documents)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'real.estate.handover') or 'New'
        records = super().create(vals_list)
        for rec in records:
            if not rec.checklist_line_ids:
                rec.checklist_line_ids = [(0, 0, {'item_name': item}) for item in DEFAULT_CHECKLIST_ITEMS]
        return records

    def _require_state(self, expected):
        for rec in self:
            if rec.state != expected:
                raise UserError('Handover "%s" must be in state "%s" for this '
                                 'action (currently "%s").' % (rec.name, expected, rec.state))

    def action_request(self):
        self._require_state('draft')
        self.write({'state': 'handover_requested'})
        self.mapped('unit_id').write({'status': 'handover_pending'})

    def action_financial_clearance(self):
        self._require_state('handover_requested')
        for rec in self:
            if not rec.financial_cleared:
                raise UserError(
                    'Handover "%s" cannot pass Financial Clearance: outstanding '
                    'balance is %.2f. Collect the balance or set an Authorized '
                    'Override with a reason.' % (rec.name, rec.outstanding_balance))
        self.write({'state': 'financial_clearance'})

    def action_qc_clearance(self):
        self._require_state('financial_clearance')
        for rec in self:
            if not rec.qc_cleared:
                raise UserError(
                    'Handover "%s" cannot pass QC Clearance: %d open critical '
                    'defect(s) and/or no Passed Final QC inspection on this unit.' % (
                        rec.name, rec.open_critical_defect_count))
        self.write({'state': 'qc_clearance'})

    def action_documentation_clearance(self):
        self._require_state('qc_clearance')
        for rec in self:
            if not rec.documentation_cleared:
                raise UserError(
                    'Handover "%s" cannot pass Documentation Clearance: tick all '
                    'four documentation checkboxes first.' % rec.name)
        self.write({'state': 'documentation_clearance'})

    def action_final_inspection(self):
        self._require_state('documentation_clearance')
        self.write({'state': 'final_inspection'})

    def action_approve(self):
        self._require_state('final_inspection')
        self.write({'state': 'approved'})

    def action_handover(self):
        self._require_state('approved')
        for rec in self:
            if not (rec.customer_signed and rec.company_signed):
                raise UserError(
                    'Handover "%s" requires both Customer and Company Representative '
                    'signatures before it can be marked Handed Over.' % rec.name)
        self.write({'state': 'handed_over'})
        self.mapped('unit_id').write({'status': 'handed_over'})

    def action_complete(self):
        self._require_state('handed_over')
        self.write({'state': 'completed'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_print_certificate(self):
        return self.env.ref(
            'real_estate_project_management.action_report_real_estate_handover'
        ).report_action(self)
