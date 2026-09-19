# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwStyle(models.Model):
    _name = 'fw.style'
    _description = 'Footwear Style Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Style Name', required=True, tracking=True)
    style_no = fields.Char(string='Style Number', required=True, tracking=True, copy=False)
    image_1920 = fields.Image(string='Style Image', max_width=1920, max_height=1920)

    category = fields.Selection([
        ('sneaker', 'Sneaker / Sports'),
        ('sandal', 'Sandal'),
        ('boot', 'Boot'),
        ('formal', 'Formal / Dress Shoe'),
        ('slipper', 'Slipper / Indoor'),
        ('leather_goods', 'Leather Goods'),
        ('other', 'Other'),
    ], string='Category', tracking=True)

    gender = fields.Selection([
        ('men', 'Men'),
        ('women', 'Women'),
        ('kids', 'Kids'),
        ('unisex', 'Unisex'),
    ], string='Gender', default='unisex', tracking=True)

    season_id = fields.Many2one('fw.season', string='Season', tracking=True)
    buyer_id = fields.Many2one('fw.buyer', string='Buyer', tracking=True)
    factory_id = fields.Many2one('fw.factory', string='Primary Factory', tracking=True)

    color_ids = fields.Many2many('fw.color', string='Colorways')
    size_curve_id = fields.Many2one('fw.size.curve', string='Size Curve')

    product_tmpl_id = fields.Many2one('product.template', string='Linked Product',
                                       help="Product template this style is sold/produced as.")

    state = fields.Selection([
        ('concept', 'Concept'),
        ('sampling', 'Sampling'),
        ('approved', 'Approved'),
        ('production', 'In Production'),
        ('discontinued', 'Discontinued'),
    ], string='Status', default='concept', tracking=True)

    last_price = fields.Float(string='Last FOB Price')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    description = fields.Html(string='Design Notes')

    _sql_constraints = [
        ('style_no_company_uniq', 'unique(style_no, company_id)',
         'Style Number must be unique per company!'),
    ]

    def name_get(self):
        result = []
        for rec in self:
            label = "[%s] %s" % (rec.style_no, rec.name) if rec.style_no else rec.name
            result.append((rec.id, label))
        return result

    def action_set_sampling(self):
        self.write({'state': 'sampling'})

    def action_set_approved(self):
        self.write({'state': 'approved'})

    def action_set_production(self):
        self.write({'state': 'production'})

    def action_set_discontinued(self):
        self.write({'state': 'discontinued'})
