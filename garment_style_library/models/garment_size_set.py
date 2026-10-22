# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentSizeSet(models.Model):
    """Size Set Master (SRS section 16) — garment.size.set."""
    _name = 'garment.size.set'
    _description = 'Garment Size Set'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Size Set Name', required=True)
    size_set_code = fields.Char(string='Size Set Code')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer')
    brand = fields.Char(string='Brand')
    style_category_id = fields.Many2one('garment.style.category', string='Product Category')
    product_type = fields.Char(string='Product Type')
    gender = fields.Selection([
        ('men', 'Men'), ('women', 'Women'), ('unisex', 'Unisex'), ('boys', 'Boys'), ('girls', 'Girls'),
    ], string='Gender')
    age_group = fields.Selection([
        ('adult', 'Adult'), ('kids', 'Kids'), ('infant', 'Infant'), ('toddler', 'Toddler'),
    ], string='Age Group')
    season = fields.Char(string='Season')
    size_system = fields.Selection([
        ('international', 'International (XXS-5XL)'), ('numeric', 'Numeric (26-46)'),
        ('childrens', "Children's (Newborn-14Y)"), ('custom', 'Custom'),
    ], string='Size System', default='international')
    status = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived'),
    ], string='Status', default='draft')
    line_ids = fields.One2many('garment.size.set.line', 'size_set_id', string='Sizes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)


class GarmentSizeSetLine(models.Model):
    _name = 'garment.size.set.line'
    _description = 'Garment Size Set Line'
    _order = 'sequence'

    size_set_id = fields.Many2one('garment.size.set', string='Size Set', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    size_code = fields.Char(string='Size Code', required=True, help='e.g. S, M, L, 32, 6Y')
    is_base_size = fields.Boolean(string='Base Size')
