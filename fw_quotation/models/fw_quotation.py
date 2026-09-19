# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwQuotation(models.Model):
    _name = 'fw.quotation'
    _description = 'Footwear Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'quotation_date desc'

    name = fields.Char(string='Quotation Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.quotation') or 'New')
    buyer_id = fields.Many2one('fw.buyer', string='Buyer', tracking=True)
    lead_id = fields.Many2one('fw.crm.lead', string='CRM Lead', tracking=True)

    quotation_date = fields.Date(string='Quotation Date', default=fields.Date.context_today)
    valid_until = fields.Date(string='Valid Until', required=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    line_ids = fields.One2many('fw.quotation.line', 'quotation_id', string='Quotation Lines')
    total_qty = fields.Integer(string='Total Qty (Pairs)', compute='_compute_totals', store=True)
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_totals', store=True,
                                    currency_field='currency_id')

    terms_conditions = fields.Text(string='Terms & Conditions')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', tracking=True)

    converted_order_id = fields.Many2one('fw.buyer.order', string='Converted Buyer Order',
                                          readonly=True, copy=False)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.quotation') or 'New'
        return super().create(vals_list)

    @api.constrains('buyer_id', 'lead_id')
    def _check_target(self):
        for rec in self:
            if not rec.buyer_id and not rec.lead_id:
                raise ValidationError(
                    "Please set either a Buyer or a CRM Lead on the Quotation.")

    @api.depends('line_ids.qty', 'line_ids.amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_qty = sum(rec.line_ids.mapped('qty'))
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    def action_send(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Cannot send a Quotation with no lines.")
        self.write({'state': 'sent'})

    def action_accept(self):
        self.write({'state': 'accepted'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.model
    def _cron_expire_quotations(self):
        """Scheduled action: auto-expire quotations whose Valid Until date has passed
        and which have not yet been accepted/rejected/converted."""
        today = fields.Date.context_today(self)
        overdue = self.search([
            ('state', 'in', ('draft', 'sent')),
            ('valid_until', '<', today),
        ])
        overdue.write({'state': 'expired'})

    def action_convert_to_order(self):
        self.ensure_one()
        if self.state != 'accepted':
            raise UserError("Only an Accepted Quotation can be converted to a Buyer Order.")
        if self.converted_order_id:
            raise UserError("This Quotation has already been converted to Buyer Order '%s'."
                             % self.converted_order_id.name)
        buyer = self.buyer_id
        if not buyer:
            if self.lead_id and self.lead_id.converted_buyer_id:
                buyer = self.lead_id.converted_buyer_id
            else:
                raise UserError(
                    "No Buyer is set on this Quotation, and the linked CRM Lead has not "
                    "been converted to a Buyer yet. Please convert the Lead to a Buyer "
                    "first (CRM > Buyer Pipeline).")

        order_line_vals = [(0, 0, {
            'style_id': line.style_id.id,
            'color_id': line.color_id.id,
            'size_curve_id': line.size_curve_id.id,
            'total_qty': line.qty,
            'unit_price': line.unit_price,
        }) for line in self.line_ids]

        order = self.env['fw.buyer.order'].create({
            'buyer_id': buyer.id,
            'currency_id': self.currency_id.id,
            'line_ids': order_line_vals,
        })
        self.write({'buyer_id': buyer.id, 'converted_order_id': order.id})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Buyer Order',
            'res_model': 'fw.buyer.order',
            'view_mode': 'form',
            'res_id': order.id,
        }


class FwQuotationLine(models.Model):
    _name = 'fw.quotation.line'
    _description = 'Footwear Quotation Line'
    _order = 'sequence, id'

    quotation_id = fields.Many2one('fw.quotation', string='Quotation', required=True,
                                    ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    style_id = fields.Many2one('fw.style', string='Style', required=True)
    color_id = fields.Many2one('fw.color', string='Color')
    size_curve_id = fields.Many2one('fw.size.curve', string='Size Curve')
    qty = fields.Integer(string='Qty (Pairs)', required=True, default=0)
    unit_price = fields.Float(string='Unit Price', digits='Product Price')
    currency_id = fields.Many2one(related='quotation_id.currency_id', string='Currency',
                                   store=True)
    amount = fields.Monetary(string='Amount', compute='_compute_amount', store=True,
                              currency_field='currency_id')

    @api.depends('qty', 'unit_price')
    def _compute_amount(self):
        for rec in self:
            rec.amount = (rec.qty or 0) * (rec.unit_price or 0.0)

    @api.onchange('style_id')
    def _onchange_style_id(self):
        if self.style_id:
            if self.style_id.size_curve_id:
                self.size_curve_id = self.style_id.size_curve_id
            if not self.unit_price and self.style_id.last_price:
                self.unit_price = self.style_id.last_price
