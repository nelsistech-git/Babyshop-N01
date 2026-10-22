# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models, _


class GarmentMerchStyleLine(models.Model):
    """Style Development lines under an Inquiry (SRS section 9) —
    garment.merch.style.line. Each inquiry can contain multiple styles;
    once development starts, links to the real garment.style record."""
    _name = 'garment.merch.style.line'
    _description = 'Garment Merchandising Inquiry Style Line'
    _order = 'sequence'

    inquiry_id = fields.Many2one('garment.merch.inquiry', string='Inquiry', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    style_id = fields.Many2one('garment.style', string='Style')
    style_name = fields.Char(string='Style Name (working title)')
    buyer_style_number = fields.Char(string='Buyer Style Number')
    factory_style_number = fields.Char(string='Factory Style Number')
    product_type = fields.Char(string='Product Type')
    gender = fields.Selection([
        ('men', 'Men'), ('women', 'Women'), ('unisex', 'Unisex'), ('boys', 'Boys'), ('girls', 'Girls'),
    ], string='Gender')
    age_group = fields.Selection([
        ('adult', 'Adult'), ('kids', 'Kids'), ('infant', 'Infant'), ('toddler', 'Toddler'),
    ], string='Age Group')

    # Product Specification (SRS section 9)
    fit_type = fields.Char(string='Fit Type')
    construction_type = fields.Char(string='Construction Type')

    # Material Details (SRS section 9)
    main_fabric = fields.Char(string='Main Fabric')

    # Size Details (SRS section 9)
    size_range = fields.Char(string='Size Range')

    # Color Details (SRS section 9)
    color_name = fields.Char(string='Color Name')
    pantone_code = fields.Char(string='Pantone')

    status = fields.Selection([
        ('not_started', 'Not Started'), ('in_development', 'In Development'),
        ('ready_for_costing', 'Ready for Costing'), ('costed', 'Costed'), ('dropped', 'Dropped'),
    ], string='Status', default='not_started')

    def action_create_style(self):
        for rec in self:
            if rec.style_id:
                continue
            style = self.env['garment.style'].create({
                'style_name': rec.style_name or _('New Style'),
                'buyer_id': rec.inquiry_id.buyer_id.id,
                'buyer_style_number': rec.buyer_style_number,
                'style_category_id': rec.inquiry_id.product_category_id.id,
                'gender': rec.gender,
            })
            rec.write({'style_id': style.id, 'status': 'in_development'})
        return True
