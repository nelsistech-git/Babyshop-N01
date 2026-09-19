# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwChannelPartner(models.Model):
    _name = 'fw.channel.partner'
    _description = 'Footwear Distribution Channel Partner (Dealer/Distributor/Retail)'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Partner Name', required=True, tracking=True)
    code = fields.Char(string='Partner Code', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Related Contact')

    channel_type = fields.Selection([
        ('dealer', 'Dealer'),
        ('distributor', 'Distributor'),
        ('retail_outlet', 'Retail Outlet'),
    ], string='Channel Type', required=True, default='dealer', tracking=True)

    territory = fields.Char(string='Territory / Region')
    credit_limit = fields.Monetary(string='Credit Limit', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    assigned_salesperson_id = fields.Many2one('res.users', string='Assigned Salesperson')

    order_ids = fields.One2many('fw.distribution.order', 'channel_partner_id',
                                 string='Distribution Orders')
    order_count = fields.Integer(string='Orders', compute='_compute_order_count')
    warranty_claim_ids = fields.One2many('fw.warranty.claim', 'channel_partner_id',
                                          string='Warranty Claims')
    warranty_claim_count = fields.Integer(string='Warranty Claims',
                                           compute='_compute_warranty_claim_count')

    email = fields.Char(related='partner_id.email', string='Email', readonly=False)
    phone = fields.Char(related='partner_id.phone', string='Phone', readonly=False)

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Partner Code must be unique!'),
    ]

    def _compute_order_count(self):
        for rec in self:
            rec.order_count = len(rec.order_ids)

    def _compute_warranty_claim_count(self):
        for rec in self:
            rec.warranty_claim_count = len(rec.warranty_claim_ids)

    def name_get(self):
        result = []
        for rec in self:
            label = "[%s] %s" % (rec.code, rec.name) if rec.code else rec.name
            result.append((rec.id, label))
        return result

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Distribution Orders',
            'res_model': 'fw.distribution.order',
            'view_mode': 'tree,form',
            'domain': [('channel_partner_id', '=', self.id)],
            'context': {'default_channel_partner_id': self.id},
        }

    def action_view_warranty_claims(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Warranty Claims',
            'res_model': 'fw.warranty.claim',
            'view_mode': 'tree,form',
            'domain': [('channel_partner_id', '=', self.id)],
            'context': {'default_channel_partner_id': self.id},
        }
