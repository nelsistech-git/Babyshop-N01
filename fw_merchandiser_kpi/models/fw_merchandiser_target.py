# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwMerchandiserTarget(models.Model):
    _name = 'fw.merchandiser.target'
    _description = 'Footwear Merchandiser Booking Target & Achievement'
    _inherit = ['mail.thread']
    _order = 'period_end desc'

    name = fields.Char(string='Target Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.merchandiser.target') or 'New')
    merchandiser_id = fields.Many2one('res.users', string='Merchandiser', required=True,
                                       tracking=True)
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    target_order_value = fields.Monetary(string='Target Order Value', currency_field='currency_id')
    target_order_qty = fields.Integer(string='Target Order Qty (Pairs)')

    @api.constrains('target_order_value', 'target_order_qty')
    def _check_target_non_negative(self):
        for rec in self:
            if rec.target_order_value < 0:
                raise ValidationError("Target Order Value cannot be negative.")
            if rec.target_order_qty < 0:
                raise ValidationError("Target Order Qty cannot be negative.")

    achieved_order_value = fields.Monetary(string='Achieved Order Value', readonly=True,
                                            currency_field='currency_id')
    achieved_order_qty = fields.Integer(string='Achieved Order Qty (Pairs)', readonly=True)
    order_count = fields.Integer(string='Confirmed Orders Counted', readonly=True)

    value_achievement_percent = fields.Float(string='Value Achievement %',
                                              compute='_compute_achievement_percent', store=True)
    qty_achievement_percent = fields.Float(string='Qty Achievement %',
                                            compute='_compute_achievement_percent', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.merchandiser.target') or 'New'
        return super().create(vals_list)

    @api.depends('achieved_order_value', 'target_order_value',
                 'achieved_order_qty', 'target_order_qty')
    def _compute_achievement_percent(self):
        for rec in self:
            rec.value_achievement_percent = (
                rec.achieved_order_value / rec.target_order_value * 100.0
            ) if rec.target_order_value else 0.0
            rec.qty_achievement_percent = (
                rec.achieved_order_qty / rec.target_order_qty * 100.0
            ) if rec.target_order_qty else 0.0

    def action_compute_achievement(self):
        for rec in self:
            if not rec.period_start or not rec.period_end:
                raise UserError("Please set both Period Start and Period End first.")
            orders = self.env['fw.buyer.order'].search([
                ('order_date', '>=', rec.period_start),
                ('order_date', '<=', rec.period_end),
                ('state', 'not in', ('draft', 'cancelled')),
                ('buyer_id.merchandiser_ids', 'in', rec.merchandiser_id.id),
            ])
            rec.write({
                'achieved_order_value': sum(orders.mapped('total_amount')),
                'achieved_order_qty': sum(orders.mapped('total_qty')),
                'order_count': len(orders),
            })

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
