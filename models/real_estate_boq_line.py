# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RealEstateBoqLine(models.Model):
    _name = 'real.estate.boq.line'
    _description = 'Real Estate BOQ Line'
    _order = 'id'

    boq_id = fields.Many2one('real.estate.boq', string='BOQ', required=True, ondelete='cascade')
    project_id = fields.Many2one(related='boq_id.project_id', store=True, readonly=True)
    work_package_id = fields.Many2one(related='boq_id.work_package_id', store=True, readonly=True)

    product_id = fields.Many2one('product.product', string='Item/Product',
                                  help='Optional link to a standard Odoo product.')
    description = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', digits=(12, 2), required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit')

    estimated_rate = fields.Monetary(string='Estimated Rate')
    estimated_amount = fields.Monetary(string='Estimated Amount', compute='_compute_amounts', store=True)

    approved_rate = fields.Monetary(string='Approved Rate')
    approved_amount = fields.Monetary(string='Approved Amount', compute='_compute_amounts', store=True)

    actual_quantity = fields.Float(string='Actual Quantity', digits=(12, 2))
    actual_amount = fields.Monetary(string='Actual Amount', compute='_compute_amounts', store=True)

    variance_amount = fields.Monetary(string='Variance', compute='_compute_amounts', store=True)

    company_id = fields.Many2one(related='boq_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(related='boq_id.currency_id', readonly=True)

    @api.depends('quantity', 'estimated_rate', 'approved_rate', 'actual_quantity')
    def _compute_amounts(self):
        for rec in self:
            rec.estimated_amount = rec.quantity * rec.estimated_rate
            rec.approved_amount = rec.quantity * (rec.approved_rate or rec.estimated_rate)
            rec.actual_amount = rec.actual_quantity * (rec.approved_rate or rec.estimated_rate)
            rec.variance_amount = rec.approved_amount - rec.actual_amount

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.display_name
            self.uom_id = self.product_id.uom_id
