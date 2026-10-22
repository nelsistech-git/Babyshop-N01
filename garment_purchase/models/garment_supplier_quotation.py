# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentSupplierQuotation(models.Model):
    """Supplier Quotation Management + Comparison (SRS sections 16-17) —
    garment.supplier.quotation."""
    _name = 'garment.supplier.quotation'
    _description = 'Garment Supplier Quotation'
    _order = 'price'

    rfq_id = fields.Many2one('garment.purchase.rfq', string='RFQ', required=True, ondelete='cascade')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True)
    material_name = fields.Char(string='Material', related='rfq_id.material_name', store=True)
    price = fields.Monetary(string='Price', currency_field='currency_id', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    moq = fields.Float(string='MOQ')
    lead_time_days = fields.Integer(string='Lead Time (days)')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    validity_date = fields.Date(string='Validity Date')

    quality_rating_pct = fields.Float(string='Quality Rating (%)')
    delivery_rating_pct = fields.Float(string='Delivery Performance Rating (%)')
    previous_performance_note = fields.Char(string='Previous Performance Note')

    attachment = fields.Binary(string='Quotation Document', attachment=True)
    attachment_filename = fields.Char(string='Filename')

    status = fields.Selection([
        ('received', 'Received'), ('under_review', 'Under Review'), ('selected', 'Selected'), ('rejected', 'Rejected'),
    ], string='Status', default='received', tracking=False)

    def action_select(self):
        self.write({'status': 'selected'})
        self.rfq_id.write({'status': 'quoted'})
        (self.rfq_id.quotation_ids - self).write({'status': 'rejected'})
