# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwBuyerPriceAgreement(models.Model):
    _name = 'fw.buyer.price.agreement'
    _description = 'Footwear Buyer Negotiated Price Agreement'
    _inherit = ['mail.thread']
    _order = 'valid_from desc'

    name = fields.Char(string='Agreement Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.buyer.price.agreement') or 'New')
    buyer_id = fields.Many2one('fw.buyer', string='Buyer', required=True, tracking=True)

    style_id = fields.Many2one('fw.style', string='Style',
                                help="Leave empty for a category-wide agreement.")
    category = fields.Selection([
        ('sneaker', 'Sneaker / Sports'),
        ('sandal', 'Sandal'),
        ('boot', 'Boot'),
        ('formal', 'Formal / Dress Shoe'),
        ('slipper', 'Slipper / Indoor'),
        ('leather_goods', 'Leather Goods'),
        ('other', 'Other'),
    ], string='Category', help="Used when this agreement applies to a category rather "
                                "than a single Style.")
    season_id = fields.Many2one('fw.season', string='Season')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    price_from = fields.Monetary(string='Price Band From', currency_field='currency_id')
    price_to = fields.Monetary(string='Price Band To', currency_field='currency_id')

    valid_from = fields.Date(string='Valid From', required=True)
    valid_to = fields.Date(string='Valid To', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', tracking=True)

    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.buyer.price.agreement') or 'New'
        return super().create(vals_list)

    @api.constrains('valid_from', 'valid_to')
    def _check_dates(self):
        for rec in self:
            if rec.valid_from and rec.valid_to and rec.valid_from > rec.valid_to:
                raise ValidationError("Valid From cannot be after Valid To.")

    @api.constrains('price_from', 'price_to')
    def _check_price_band(self):
        for rec in self:
            if rec.price_from and rec.price_to and rec.price_from > rec.price_to:
                raise ValidationError("Price Band From cannot be greater than Price Band To.")

    def action_activate(self):
        self.write({'state': 'active'})

    def action_expire(self):
        self.write({'state': 'expired'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.model
    def _cron_expire_agreements(self):
        """Scheduled action: auto-expire agreements whose Valid To date has passed."""
        today = fields.Date.context_today(self)
        overdue = self.search([('state', '=', 'active'), ('valid_to', '<', today)])
        overdue.write({'state': 'expired'})
