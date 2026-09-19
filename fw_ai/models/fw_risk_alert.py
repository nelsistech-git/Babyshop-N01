# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwRiskAlert(models.Model):
    _name = 'fw.risk.alert'
    _description = 'Footwear Risk Alert (Rule-Based)'
    _inherit = ['mail.thread']
    _order = 'detected_date desc, severity desc'

    name = fields.Char(string='Alert Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.risk.alert') or 'New')
    scan_id = fields.Many2one('fw.ai.scan', string='Detected By Scan', ondelete='cascade')

    risk_type = fields.Selection([
        ('order_delay', 'Order Delay Risk'),
        ('machine_breakdown', 'Machine Reliability Risk'),
        ('supplier_quality', 'Supplier Quality Risk'),
        ('spare_stock', 'Spare Stock Risk'),
    ], string='Risk Type', required=True)

    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Severity', required=True, default='medium', tracking=True)

    buyer_order_id = fields.Many2one('fw.buyer.order', string='Buyer Order')
    machine_id = fields.Many2one('fw.machine', string='Machine')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    spare_part_id = fields.Many2one('fw.spare.part', string='Spare Part')

    description = fields.Text(string='Why This Was Flagged', required=True,
                               help="Plain-language explanation of the rule that triggered "
                                    "this alert.")
    detected_date = fields.Date(string='Detected On', default=fields.Date.context_today)

    state = fields.Selection([
        ('open', 'Open'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    ], string='Status', default='open', tracking=True)

    resolved_by = fields.Many2one('res.users', string='Resolved By', readonly=True, copy=False)
    resolved_date = fields.Date(string='Resolved Date', readonly=True, copy=False)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.risk.alert') or 'New'
        return super().create(vals_list)

    def action_acknowledge(self):
        self.write({'state': 'acknowledged'})

    def action_resolve(self):
        self.write({
            'state': 'resolved',
            'resolved_by': self.env.user.id,
            'resolved_date': fields.Date.context_today(self),
        })

    def action_reopen(self):
        self.write({'state': 'open', 'resolved_by': False, 'resolved_date': False})
