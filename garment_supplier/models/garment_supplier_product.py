# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentSupplierProduct(models.Model):
    """Supplier Product Catalog + Price Management (SRS sections 12-13),
    plus Bangladesh Garment Supplier Standards fabric/accessories tracking
    (SRS section 45) — garment.supplier.product."""
    _name = 'garment.supplier.product'
    _description = 'Garment Supplier Product'
    _order = 'sequence'

    supplier_id = fields.Many2one('garment.supplier', string='Supplier', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    product_name = fields.Char(string='Product Name', required=True)
    product_category = fields.Selection([
        ('fabric', 'Fabric'), ('accessory', 'Accessory / Trim'), ('other', 'Other'),
    ], string='Product Category', default='other',
        help='Determines which Bangladesh Standards fields below are relevant (SRS section 45).')
    specification = fields.Char(string='Specification')
    uom = fields.Char(string='UoM')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='supplier_id.currency_id', store=True)
    effective_date = fields.Date(string='Effective Date')
    validity_date = fields.Date(string='Validity')
    lead_time_days = fields.Integer(string='Lead Time (days)')
    moq = fields.Float(string='MOQ')
    previous_price = fields.Monetary(string='Previous Price', currency_field='currency_id',
                                      help='Mirrors the price captured in the last price_history_ids line.')

    # Fabric Supplier Information (SRS section 45)
    fabric_composition = fields.Char(string='Fabric Composition')
    gsm = fields.Float(string='GSM')
    width = fields.Char(string='Width')
    dyeing_process = fields.Selection([
        ('yarn_dyed', 'Yarn Dyed'), ('piece_dyed', 'Piece Dyed'), ('solution_dyed', 'Solution Dyed'),
        ('printed', 'Printed'), ('none', 'Not Applicable'),
    ], string='Dyeing Process')
    color_fastness_rating = fields.Char(string='Color Fastness Rating')
    test_report_ref = fields.Char(string='Test Report Reference')

    # Accessories Supplier Information (SRS section 45)
    material_type = fields.Char(string='Material Type')
    size_specification = fields.Char(string='Size Specification')
    color_matching_status = fields.Selection([
        ('pending', 'Pending'), ('matched', 'Matched'), ('mismatch', 'Mismatch'),
    ], string='Color Matching Status')
    sample_approval_status = fields.Selection([
        ('not_submitted', 'Not Submitted'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Sample Approval Status', default='not_submitted')

    # Price History (SRS section 13)
    price_history_ids = fields.One2many('garment.supplier.price.history', 'supplier_product_id',
                                         string='Price History')
    price_history_count = fields.Integer(compute='_compute_price_history_count')

    def _compute_price_history_count(self):
        for rec in self:
            rec.price_history_count = len(rec.price_history_ids)

    def action_log_price_history(self):
        """Snapshot the current unit_price into Price History (SRS section
        13) and move it into previous_price, mirroring how the on-screen
        example tracks a fabric's price year over year."""
        History = self.env['garment.supplier.price.history']
        for rec in self:
            if not rec.unit_price:
                continue
            History.create({
                'supplier_product_id': rec.id,
                'price': rec.unit_price,
                'effective_date': rec.effective_date or fields.Date.context_today(rec),
                'validity_date': rec.validity_date,
                'moq': rec.moq,
            })
            rec.previous_price = rec.unit_price
        return True

    def action_view_price_history(self):
        self.ensure_one()
        return {
            'name': _('Price History'),
            'type': 'ir.actions.act_window',
            'res_model': 'garment.supplier.price.history',
            'view_mode': 'tree,form',
            'domain': [('supplier_product_id', '=', self.id)],
            'context': {'default_supplier_product_id': self.id},
        }
