# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

DEFAULT_DOCUMENTS = [
    'commercial_invoice', 'packing_list', 'bl_awb', 'certificate_of_origin',
    'beneficiary_certificate', 'insurance_certificate',
]


class FwLetterOfCredit(models.Model):
    _name = 'fw.letter.of.credit'
    _description = 'Footwear Letter of Credit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'

    name = fields.Char(string='L/C Reference (System)', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.letter.of.credit') or 'New')
    lc_no = fields.Char(string="Bank's L/C Number", required=True, tracking=True)
    buyer_order_id = fields.Many2one('fw.buyer.order', string='Buyer Order', required=True,
                                      tracking=True)
    buyer_id = fields.Many2one(related='buyer_order_id.buyer_id', string='Buyer', store=True)

    lc_type = fields.Selection([
        ('sight', 'Sight L/C'),
        ('usance', 'Usance L/C'),
        ('revolving', 'Revolving L/C'),
        ('transferable', 'Transferable L/C'),
        ('back_to_back', 'Back-to-Back L/C'),
        ('other', 'Other'),
    ], string='L/C Type', default='sight', required=True, tracking=True)

    issuing_bank = fields.Char(string='Issuing Bank')
    advising_bank = fields.Char(string='Advising / Negotiating Bank')

    currency_id = fields.Many2one(related='buyer_order_id.currency_id', string='Currency',
                                   store=True)
    lc_amount = fields.Monetary(string='L/C Amount', currency_field='currency_id')

    @api.constrains('lc_amount')
    def _check_lc_amount_non_negative(self):
        for rec in self:
            if rec.lc_amount < 0:
                raise ValidationError("L/C Amount cannot be negative.")

    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)
    latest_shipment_date = fields.Date(string='Latest Shipment Date', tracking=True)

    partial_shipment_allowed = fields.Boolean(string='Partial Shipment Allowed', default=True)
    transshipment_allowed = fields.Boolean(string='Transshipment Allowed', default=False)
    payment_terms = fields.Char(string='Payment Terms',
                                 help="E.g. 'At Sight', '90 days from B/L date'")

    document_line_ids = fields.One2many('fw.lc.document.line', 'lc_id',
                                         string='Required Document Checklist')
    all_documents_submitted = fields.Boolean(string='All Documents Submitted',
                                              compute='_compute_all_documents_submitted',
                                              store=True)

    discrepancy_notes = fields.Text(string='Bank Discrepancy Notes')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('received', 'Received'),
        ('active', 'Active'),
        ('utilized', 'Utilized (Documents Presented)'),
        ('expired', 'Expired'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.letter.of.credit') or 'New'
        return super().create(vals_list)

    @api.depends('document_line_ids.submitted')
    def _compute_all_documents_submitted(self):
        for rec in self:
            required = rec.document_line_ids.filtered('required')
            rec.all_documents_submitted = bool(required) and all(
                required.mapped('submitted'))

    def action_generate_standard_checklist(self):
        for rec in self:
            existing_types = rec.document_line_ids.mapped('document_type')
            new_lines = [(0, 0, {
                'document_type': doc_type,
                'required': True,
            }) for doc_type in DEFAULT_DOCUMENTS if doc_type not in existing_types]
            if new_lines:
                rec.document_line_ids = new_lines

    def action_mark_received(self):
        self.write({'status': 'received'})

    def action_activate(self):
        self.write({'status': 'active'})

    def action_mark_utilized(self):
        for rec in self:
            required = rec.document_line_ids.filtered('required')
            if required and not all(required.mapped('submitted')):
                raise UserError(
                    "Not all required documents have been marked as submitted yet.")
        self.write({'status': 'utilized'})

    def action_close(self):
        self.write({'status': 'closed'})

    def action_reset_draft(self):
        self.write({'status': 'draft'})

    @api.model
    def _cron_notify_lc_deadlines(self):
        """Scheduled action: flag L/Cs whose expiry or latest shipment date is within
        14 days and still open (not utilized/expired/closed), with a To-Do activity."""
        today = fields.Date.context_today(self)
        cutoff = today + timedelta(days=14)
        lcs = self.search([
            ('status', 'not in', ('utilized', 'expired', 'closed')),
            '|',
            ('expiry_date', '<=', cutoff),
            ('latest_shipment_date', '<=', cutoff),
        ])
        for lc in lcs:
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'fw.letter.of.credit'),
                ('res_id', '=', lc.id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ], limit=1)
            if existing:
                continue
            note = "L/C %s (Buyer Order %s) is approaching its expiry (%s) or latest " \
                   "shipment date (%s). Please review." % (
                       lc.lc_no, lc.buyer_order_id.name, lc.expiry_date or 'N/A',
                       lc.latest_shipment_date or 'N/A')
            lc.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='L/C deadline approaching',
                note=note,
            )


class FwLcDocumentLine(models.Model):
    _name = 'fw.lc.document.line'
    _description = 'L/C Required Document Checklist Line'
    _order = 'id'

    lc_id = fields.Many2one('fw.letter.of.credit', string='Letter of Credit', required=True,
                             ondelete='cascade')
    document_type = fields.Selection([
        ('commercial_invoice', 'Commercial Invoice'),
        ('packing_list', 'Packing List'),
        ('bl_awb', 'Bill of Lading / Airway Bill'),
        ('certificate_of_origin', 'Certificate of Origin'),
        ('beneficiary_certificate', "Beneficiary's Certificate"),
        ('insurance_certificate', 'Insurance Certificate'),
        ('inspection_certificate', 'Inspection Certificate'),
        ('other', 'Other'),
    ], string='Document Type', required=True, default='other')
    document_name = fields.Char(string='Document Name (if Other)')
    required = fields.Boolean(string='Required', default=True)
    submitted = fields.Boolean(string='Submitted')
    submitted_date = fields.Date(string='Submitted Date')
    remarks = fields.Char(string='Remarks')

    @api.onchange('submitted')
    def _onchange_submitted(self):
        if self.submitted and not self.submitted_date:
            self.submitted_date = fields.Date.context_today(self)
