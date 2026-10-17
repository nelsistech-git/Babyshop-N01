# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class NelsisCommercialLine(models.Model):
    """A documented quantity taken from a verified source document. It is NOT stock."""
    _name = 'nelsis.commercial.line'
    _description = 'Documented Quantity Line'
    _order = 'file_id, id'

    file_id = fields.Many2one('nelsis.commercial.file', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='file_id.company_id', store=True, index=True)
    shipment_id = fields.Many2one('nelsis.commercial.shipment', domain="[('file_id', '=', file_id)]")
    boe_id = fields.Many2one('nelsis.commercial.boe', domain="[('file_id', '=', file_id)]")
    document_id = fields.Many2one('nelsis.commercial.document', string='Source Document',
                                  domain="[('file_id', '=', file_id)]")
    source_kind = fields.Selection(
        [('invoice', 'Commercial Invoice'), ('packing_list', 'Packing List'),
         ('boe', 'Bill of Entry'), ('other', 'Other')], required=True, default='invoice')
    product_id = fields.Many2one('product.product', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', required=True)
    qty = fields.Float(string='Documented Quantity', digits='Product Unit of Measure', required=True)
    value = fields.Monetary(string='Documented Value', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id

    @api.constrains('qty')
    def _check_qty(self):
        for rec in self:
            if rec.qty < 0:
                raise ValidationError(_("Documented quantity cannot be negative."))

    @api.constrains('product_id', 'uom_id')
    def _check_uom_category(self):
        for rec in self:
            if rec.product_id.uom_id.category_id != rec.uom_id.category_id:
                raise ValidationError(_("Unit '%(u)s' is not in the same unit category as product '%(p)s'. "
                                        "Use a valid unit of measure; no silent conversion is performed.",
                                        u=rec.uom_id.name, p=rec.product_id.display_name))
