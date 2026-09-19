# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwSample(models.Model):
    _name = 'fw.sample'
    _description = 'Footwear Sample Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    name = fields.Char(string='Sample Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.sample') or 'New')
    style_id = fields.Many2one('fw.style', string='Style', required=True, tracking=True,
                                ondelete='cascade')
    sample_type = fields.Selection([
        ('proto', 'Proto Sample'),
        ('fit', 'Fit Sample'),
        ('sms', 'Salesman Sample (SMS)'),
        ('size_set', 'Size Set Sample'),
        ('pp', 'Pre-Production (PP) Sample'),
        ('tod', 'Top of Delivery (TOD) Sample'),
    ], string='Sample Type', required=True, default='proto', tracking=True)

    request_date = fields.Date(string='Request Date', default=fields.Date.context_today)
    due_date = fields.Date(string='Due Date')
    responsible_id = fields.Many2one('res.users', string='Responsible',
                                      default=lambda self: self.env.user)

    state = fields.Selection([
        ('requested', 'Requested'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted to Buyer'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revise', 'Revise & Resubmit'),
    ], string='Status', default='requested', tracking=True)

    buyer_comments = fields.Text(string='Buyer Comments')
    internal_comments = fields.Text(string='Internal Comments')
    approved_date = fields.Date(string='Approved Date', readonly=True, copy=False)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.sample') or 'New'
        return super().create(vals_list)

    def action_start_progress(self):
        self.write({'state': 'in_progress'})

    def action_submit_buyer(self):
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({'state': 'approved', 'approved_date': fields.Date.context_today(self)})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_revise(self):
        self.write({'state': 'revise'})
