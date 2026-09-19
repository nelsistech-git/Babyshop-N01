# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwWarrantyClaim(models.Model):
    _name = 'fw.warranty.claim'
    _description = 'Footwear Warranty Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'claim_date desc'

    name = fields.Char(string='Claim Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.warranty.claim') or 'New')
    channel_partner_id = fields.Many2one('fw.channel.partner', string='Dealer/Retail Outlet',
                                          required=True, tracking=True)
    style_id = fields.Many2one('fw.style', string='Style')

    customer_name = fields.Char(string='End Customer Name')
    customer_phone = fields.Char(string='End Customer Phone')
    purchase_date = fields.Date(string='Original Purchase Date')
    claim_date = fields.Date(string='Claim Date', default=fields.Date.context_today)

    defect_description = fields.Text(string='Defect Description', required=True)

    resolution = fields.Selection([
        ('pending', 'Pending'),
        ('repair', 'Repair'),
        ('replace', 'Replace'),
        ('reject', 'Reject'),
        ('refund', 'Refund'),
    ], string='Resolution', default='pending', tracking=True)
    resolution_notes = fields.Text(string='Resolution Notes')

    state = fields.Selection([
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='submitted', tracking=True)

    handled_by = fields.Many2one('res.users', string='Handled By',
                                  default=lambda self: self.env.user)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.warranty.claim') or 'New'
        return super().create(vals_list)

    def action_start_review(self):
        self.write({'state': 'under_review'})

    def action_resolve(self):
        for rec in self:
            if rec.resolution == 'pending':
                rec.resolution = 'repair'
        self.write({'state': 'resolved'})

    def action_reject(self):
        self.write({'state': 'rejected', 'resolution': 'reject'})

    def action_reset_submitted(self):
        self.write({'state': 'submitted'})
