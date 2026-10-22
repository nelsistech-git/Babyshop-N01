# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Supplier Comparison (SRS section 15): compares selected suppliers on
Price / Quality / Delivery / Capacity / Compliance / Payment Terms so a
purchase officer can pick between them, e.g. Supplier A 92%, Supplier B
85%, Supplier C 78%."""

from odoo import fields, models


class GarmentSupplierComparisonWizard(models.TransientModel):
    _name = 'garment.supplier.comparison.wizard'
    _description = 'Garment Supplier Comparison Wizard'

    supplier_ids = fields.Many2many('garment.supplier', string='Suppliers to Compare')
    line_ids = fields.One2many('garment.supplier.comparison.line', 'wizard_id', string='Comparison')

    def action_compare(self):
        self.ensure_one()
        self.line_ids.unlink()
        lines = []
        for supplier in self.supplier_ids:
            latest_rating = supplier.rating_ids.sorted('rating_date', reverse=True)[:1]
            products = supplier.product_ids
            avg_price = (sum(products.mapped('unit_price')) / len(products)) if products else 0.0
            lines.append((0, 0, {
                'supplier_id': supplier.id,
                'avg_price': avg_price,
                'quality_score': latest_rating.quality_score if latest_rating else 0.0,
                'delivery_score': latest_rating.delivery_score if latest_rating else 0.0,
                'cost_score': latest_rating.cost_score if latest_rating else 0.0,
                'compliance_score': latest_rating.compliance_score if latest_rating else 0.0,
                'capacity': supplier.production_capacity,
                'payment_term_id': supplier.payment_term_id.id,
                'overall_score': supplier.rating,
            }))
        self.line_ids = lines
        return {
            'type': 'ir.actions.act_window',
            'name': 'Supplier Comparison',
            'res_model': 'garment.supplier.comparison.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class GarmentSupplierComparisonLine(models.TransientModel):
    _name = 'garment.supplier.comparison.line'
    _description = 'Garment Supplier Comparison Line'
    _order = 'overall_score desc'

    wizard_id = fields.Many2one('garment.supplier.comparison.wizard', ondelete='cascade')
    supplier_id = fields.Many2one('garment.supplier', string='Supplier')
    avg_price = fields.Float(string='Avg. Product Price')
    quality_score = fields.Float(string='Quality %')
    delivery_score = fields.Float(string='Delivery %')
    cost_score = fields.Float(string='Cost (Price) %')
    compliance_score = fields.Float(string='Compliance %')
    capacity = fields.Char(string='Production Capacity')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    overall_score = fields.Float(string='Overall Score %')
