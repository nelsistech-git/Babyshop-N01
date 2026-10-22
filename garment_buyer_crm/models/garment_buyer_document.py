# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from datetime import timedelta

from odoo import api, fields, models, _


class GarmentBuyerDocument(models.Model):
    _name = 'garment.buyer.document'
    _description = 'Garment Buyer Document'
    _order = 'expiry_date'

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, ondelete='cascade')
    document_type = fields.Selection([
        ('trade_license', 'Trade License'),
        ('vat_certificate', 'VAT Certificate'),
        ('tax_certificate', 'Tax Certificate'),
        ('company_profile', 'Company Profile'),
        ('nda', 'NDA'),
        ('buyer_agreement', 'Buyer Agreement'),
        ('purchase_agreement', 'Purchase Agreement'),
        ('compliance_certificate', 'Compliance Certificate'),
        ('product_catalog', 'Product Catalog'),
        ('brand_guideline', 'Brand Guidelines'),
        ('packaging_guideline', 'Packaging Guidelines'),
        ('artwork_file', 'Artwork Files'),
        ('technical_file', 'Technical Files'),
        ('quality_manual', 'Quality Manual'),
        ('test_report', 'Test Reports'),
        ('lc_document', 'LC Documents'),
        ('other', 'Other Attachment'),
    ], string='Document Type', required=True)
    name = fields.Char(string='Document Name', required=True)
    attachment = fields.Binary(string='File', attachment=True, required=True)
    attachment_filename = fields.Char(string='Filename')
    version = fields.Char(string='Version', default='1.0')
    uploaded_by_id = fields.Many2one('res.users', string='Uploaded By', default=lambda s: s.env.user)
    uploaded_date = fields.Date(string='Uploaded Date', default=fields.Date.context_today)
    expiry_date = fields.Date(string='Expiry Date')
    reminder_days_before = fields.Integer(string='Reminder Before Expiry (days)', default=30)
    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft')
    is_expiring_soon = fields.Boolean(string='Expiring Soon', compute='_compute_is_expiring_soon', store=True)

    @api.depends('expiry_date', 'reminder_days_before')
    def _compute_is_expiring_soon(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.expiry_date:
                rec.is_expiring_soon = rec.expiry_date <= today + timedelta(days=rec.reminder_days_before or 0)
            else:
                rec.is_expiring_soon = False

    @api.model
    def _cron_notify_expiring_documents(self):
        """Scheduled action: notify uploaders / buyer owner about soon-to-expire documents."""
        expiring = self.search([('is_expiring_soon', '=', True), ('approval_status', '=', 'approved')])
        for doc in expiring:
            doc.buyer_id.message_post(
                body=_('Document "%s" (%s) is expiring on %s.') % (doc.name, doc.document_type, doc.expiry_date)
            )
