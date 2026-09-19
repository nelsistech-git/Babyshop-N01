# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError


class FwCrmLead(models.Model):
    _name = 'fw.crm.lead'
    _description = 'Footwear Buyer Acquisition Lead'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id desc'

    name = fields.Char(string='Lead / Company Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)

    contact_name = fields.Char(string='Contact Person')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    country_id = fields.Many2one('res.country', string='Country')

    source = fields.Selection([
        ('trade_show', 'Trade Show'),
        ('referral', 'Referral / Agent'),
        ('website', 'Website Inquiry'),
        ('cold_outreach', 'Cold Outreach'),
        ('existing_network', 'Existing Network'),
        ('other', 'Other'),
    ], string='Source', default='trade_show', tracking=True)

    expected_category = fields.Selection([
        ('sneaker', 'Sneaker / Sports'),
        ('sandal', 'Sandal'),
        ('boot', 'Boot'),
        ('formal', 'Formal / Dress Shoe'),
        ('slipper', 'Slipper / Indoor'),
        ('leather_goods', 'Leather Goods'),
        ('other', 'Other'),
    ], string='Expected Category')
    expected_annual_volume = fields.Integer(string='Expected Annual Volume (Pairs)')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    expected_revenue = fields.Monetary(string='Expected Annual Revenue',
                                        currency_field='currency_id')
    probability = fields.Float(string='Probability (%)', default=10.0)

    stage_id = fields.Many2one('fw.crm.stage', string='Stage',
                                default=lambda self: self.env['fw.crm.stage'].search(
                                    [], order='sequence', limit=1),
                                group_expand='_read_group_stage_ids', tracking=True)
    assigned_to = fields.Many2one('res.users', string='Assigned To',
                                   default=lambda self: self.env.user)

    state = fields.Selection([
        ('open', 'Open'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ], string='Result', default='open', tracking=True)
    lost_reason = fields.Char(string='Lost Reason')

    converted_buyer_id = fields.Many2one('fw.buyer', string='Converted Buyer', readonly=True,
                                          copy=False)

    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """Ensure all stages show as Kanban columns even when empty."""
        return stages.search([], order='sequence')

    def action_mark_lost(self):
        self.write({'state': 'lost', 'active': False})

    def action_reset_open(self):
        self.write({'state': 'open', 'active': True, 'lost_reason': False})

    def action_convert_to_buyer(self):
        self.ensure_one()
        if self.converted_buyer_id:
            raise UserError("This lead has already been converted to Buyer '%s'."
                             % self.converted_buyer_id.name)

        partner = self.env['res.partner'].create({
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'country_id': self.country_id.id,
            'is_company': True,
            'supplier_rank': 0,
            'customer_rank': 1,
        })

        buyer_code = self.name[:10].upper().replace(' ', '') if self.name else 'BUYER'
        existing_codes = self.env['fw.buyer'].search([('code', '=like', buyer_code + '%')])
        if existing_codes:
            buyer_code = "%s%d" % (buyer_code, len(existing_codes) + 1)

        buyer = self.env['fw.buyer'].create({
            'name': self.name,
            'code': buyer_code,
            'partner_id': partner.id,
            'country_id': self.country_id.id,
        })

        won_stage = self.env['fw.crm.stage'].search([('is_won', '=', True)], limit=1)
        self.write({
            'state': 'won',
            'probability': 100.0,
            'converted_buyer_id': buyer.id,
            'stage_id': won_stage.id if won_stage else self.stage_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Buyer',
            'res_model': 'fw.buyer',
            'view_mode': 'form',
            'res_id': buyer.id,
        }
