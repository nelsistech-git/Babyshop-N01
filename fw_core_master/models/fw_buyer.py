# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwBuyer(models.Model):
    _name = 'fw.buyer'
    _description = 'Footwear Buyer Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Buyer Name', required=True, tracking=True)
    code = fields.Char(string='Buyer Code', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Related Contact',
                                  help="Link to the commercial contact / company record.")
    country_id = fields.Many2one('res.country', string='Country')
    buyer_grade = fields.Selection([
        ('a', 'A - Strategic'),
        ('b', 'B - Regular'),
        ('c', 'C - Occasional'),
    ], string='Buyer Grade', default='b', tracking=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Default Payment Term')
    compliance_required = fields.Boolean(string='Compliance Audit Required', default=True)
    merchandiser_ids = fields.Many2many('res.users', string='Assigned Merchandisers')
    active = fields.Boolean(default=True)
    email = fields.Char(related='partner_id.email', string='Email', readonly=False, store=True)
    phone = fields.Char(related='partner_id.phone', string='Phone', readonly=False, store=True)
    order_count = fields.Integer(string='Buyer Orders', compute='_compute_order_count')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'Buyer Code must be unique per company!'),
    ]

    def _compute_order_count(self):
        # Placeholder: will connect to fw.merchandising buyer order model in Phase 1b.
        for rec in self:
            if 'fw.buyer.order' in self.env:
                rec.order_count = self.env['fw.buyer.order'].search_count(
                    [('buyer_id', '=', rec.id)])
            else:
                rec.order_count = 0

    def name_get(self):
        result = []
        for rec in self:
            label = "[%s] %s" % (rec.code, rec.name) if rec.code else rec.name
            result.append((rec.id, label))
        return result

    def action_view_orders(self):
        self.ensure_one()
        # Will open fw.buyer.order list once FW Merchandising module (Phase 1b) is installed.
        if 'fw.buyer.order' not in self.env:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Buyer Orders',
            'res_model': 'fw.buyer.order',
            'view_mode': 'list,form',
            'domain': [('buyer_id', '=', self.id)],
        }
