# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentMerchReviewChecklist(models.Model):
    """Internal Review Checklist (SRS section 11) — garment.merch.review.checklist.
    Gate before proceeding to costing."""
    _name = 'garment.merch.review.checklist'
    _description = 'Garment Merchandising Internal Review Checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'review_date desc'

    inquiry_id = fields.Many2one('garment.merch.inquiry', string='Inquiry', required=True, ondelete='cascade')
    style_id = fields.Many2one('garment.style', string='Style')
    reviewer_id = fields.Many2one('res.users', string='Reviewer', default=lambda s: s.env.user)
    review_date = fields.Date(string='Review Date', default=fields.Date.context_today)

    # Product Review
    chk_style_complete = fields.Boolean(string='Style Complete')
    chk_techpack_verified = fields.Boolean(string='Tech Pack Verified')
    chk_measurement_verified = fields.Boolean(string='Measurement Verified')
    chk_artwork_verified = fields.Boolean(string='Artwork Verified')
    chk_fabric_requirement_verified = fields.Boolean(string='Fabric Requirement Verified')
    chk_accessories_verified = fields.Boolean(string='Accessories Verified')
    chk_packaging_verified = fields.Boolean(string='Packaging Verified')
    chk_testing_requirements_verified = fields.Boolean(string='Testing Requirements Verified')

    # Compliance Review
    chk_buyer_compliance = fields.Boolean(string='Buyer Compliance')
    chk_factory_compliance = fields.Boolean(string='Factory Compliance')
    chk_chemical_compliance = fields.Boolean(string='Chemical Compliance')
    chk_sustainability_requirements = fields.Boolean(string='Sustainability Requirements')
    chk_packaging_compliance = fields.Boolean(string='Packaging Compliance')
    chk_country_regulations = fields.Boolean(string='Country Regulations')

    # Commercial Review
    chk_delivery_date_verified = fields.Boolean(string='Delivery Date Verified')
    chk_payment_terms_confirmed = fields.Boolean(string='Payment Terms Confirmed')
    chk_incoterms_confirmed = fields.Boolean(string='Incoterms Confirmed')
    chk_moq_verified = fields.Boolean(string='MOQ Verified')
    chk_currency_confirmed = fields.Boolean(string='Currency Confirmed')

    status = fields.Selection([
        ('draft', 'Draft'), ('in_progress', 'In Progress'), ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    remarks = fields.Text(string='Remarks')

    def action_mark_completed(self):
        self.write({'status': 'completed'})
        for rec in self:
            rec.inquiry_id.write({'status': 'costing'})
