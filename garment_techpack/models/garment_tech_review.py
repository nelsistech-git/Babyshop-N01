# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentTechReview(models.Model):
    """Technical Review Checklist (SRS section 20) — garment.tech.review."""
    _name = 'garment.tech.review'
    _description = 'Garment Tech Pack Technical Review'
    _inherit = ['mail.thread']
    _order = 'review_date desc'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    reviewer_id = fields.Many2one('res.users', string='Reviewer', default=lambda s: s.env.user)
    review_date = fields.Date(string='Review Date', default=fields.Date.context_today)

    # Product Checklist
    chk_product_description_verified = fields.Boolean(string='Product description verified')
    chk_style_number_verified = fields.Boolean(string='Style number verified')
    chk_buyer_requirement_checked = fields.Boolean(string='Buyer requirement checked')
    chk_construction_reviewed = fields.Boolean(string='Construction reviewed')
    chk_design_details_confirmed = fields.Boolean(string='Design details confirmed')

    # Fabric Checklist
    chk_fabric_composition_verified = fields.Boolean(string='Fabric composition verified')
    chk_gsm_verified = fields.Boolean(string='GSM verified')
    chk_width_verified = fields.Boolean(string='Width verified')
    chk_shrinkage_verified = fields.Boolean(string='Shrinkage verified')
    chk_color_standard_received = fields.Boolean(string='Color standard received')

    # Measurement Checklist
    chk_measurement_chart_attached = fields.Boolean(string='Measurement chart attached')
    chk_size_range_confirmed = fields.Boolean(string='Size range confirmed')
    chk_tolerance_defined = fields.Boolean(string='Tolerance defined')
    chk_grade_rules_available = fields.Boolean(string='Grade rules available')

    # Trim Checklist
    chk_labels_confirmed = fields.Boolean(string='Labels confirmed')
    chk_accessories_confirmed = fields.Boolean(string='Accessories confirmed')
    chk_color_matching_verified = fields.Boolean(string='Color matching verified')
    chk_supplier_info_available = fields.Boolean(string='Supplier information available')

    # Packaging Checklist
    chk_poly_bag_spec = fields.Boolean(string='Poly bag specification')
    chk_carton_spec = fields.Boolean(string='Carton specification')
    chk_folding_method = fields.Boolean(string='Folding method')
    chk_barcode_requirement = fields.Boolean(string='Barcode requirement')
    chk_shipping_mark_requirement = fields.Boolean(string='Shipping mark requirement')

    status = fields.Selection([
        ('draft', 'Draft'), ('in_progress', 'In Progress'), ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    comments = fields.Text(string='Comments')

    def action_mark_completed(self):
        self.write({'status': 'completed'})
