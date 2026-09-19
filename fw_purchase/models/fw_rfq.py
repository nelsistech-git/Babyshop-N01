# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwRfq(models.Model):
    _name = 'fw.rfq'
    _description = 'Footwear Request for Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'rfq_date desc'

    name = fields.Char(string='RFQ Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.rfq') or 'New')
    rfq_date = fields.Date(string='RFQ Date', default=fields.Date.context_today)
    due_date = fields.Date(string='Quote Due Date')

    line_ids = fields.One2many('fw.rfq.line', 'rfq_id', string='Materials Required')
    vendor_quote_ids = fields.One2many('fw.rfq.vendor.quote', 'rfq_id', string='Vendor Quotes')
    quote_count = fields.Integer(string='Quotes Received', compute='_compute_quote_count')

    selected_quote_id = fields.Many2one('fw.rfq.vendor.quote', string='Selected (Winning) Quote',
                                         readonly=True, copy=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent to Vendors'),
        ('quoted', 'Quotes Received'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.rfq') or 'New'
        return super().create(vals_list)

    def _compute_quote_count(self):
        for rec in self:
            rec.quote_count = len(rec.vendor_quote_ids)

    def action_send(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Please add at least one material line before sending.")
        self.write({'state': 'sent'})

    def action_mark_quoted(self):
        self.write({'state': 'quoted'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'selected_quote_id': False})


class FwRfqLine(models.Model):
    _name = 'fw.rfq.line'
    _description = 'RFQ Material Requirement Line'
    _order = 'id'

    rfq_id = fields.Many2one('fw.rfq', string='RFQ', required=True, ondelete='cascade')
    material_description = fields.Char(string='Material Description', required=True)
    product_id = fields.Many2one('product.product', string='Product (if in catalog)')
    qty = fields.Float(string='Qty Required', required=True, default=0.0)
    uom_id = fields.Many2one('uom.uom', string='UoM',
                              default=lambda self: self.env.ref('uom.product_uom_unit', False))

    @api.constrains('qty')
    def _check_qty_non_negative(self):
        for rec in self:
            if rec.qty < 0:
                raise ValidationError("RFQ material line quantity cannot be negative.")


class FwRfqVendorQuote(models.Model):
    _name = 'fw.rfq.vendor.quote'
    _description = 'RFQ Vendor Quote'
    _order = 'total_amount'

    rfq_id = fields.Many2one('fw.rfq', string='RFQ', required=True, ondelete='cascade')
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True,
                                 domain="[('supplier_rank', '>', 0)]")
    quote_date = fields.Date(string='Quote Date', default=fields.Date.context_today)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    quote_line_ids = fields.One2many('fw.rfq.vendor.quote.line', 'quote_id', string='Quote Lines')
    total_amount = fields.Monetary(string='Total Quote Amount', compute='_compute_total',
                                    store=True, currency_field='currency_id')
    is_selected = fields.Boolean(string='Selected as Winner', readonly=True, copy=False)

    @api.depends('quote_line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.quote_line_ids.mapped('amount'))

    def action_select_as_winner(self):
        self.ensure_one()
        self.rfq_id.vendor_quote_ids.write({'is_selected': False})
        self.write({'is_selected': True})
        self.rfq_id.write({'selected_quote_id': self.id, 'state': 'quoted'})

    def action_create_purchase_order(self):
        self.ensure_one()
        if not self.is_selected:
            raise UserError("Please select this quote as the winner first.")
        po_line_vals = [(0, 0, {
            'material_description': ql.rfq_line_id.material_description,
            'product_id': ql.rfq_line_id.product_id.id,
            'qty': ql.rfq_line_id.qty,
            'uom_id': ql.rfq_line_id.uom_id.id,
            'unit_price': ql.unit_price,
        }) for ql in self.quote_line_ids]
        po = self.env['fw.purchase.order'].create({
            'vendor_id': self.vendor_id.id,
            'rfq_id': self.rfq_id.id,
            'currency_id': self.currency_id.id,
            'line_ids': po_line_vals,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'fw.purchase.order',
            'view_mode': 'form',
            'res_id': po.id,
        }


class FwRfqVendorQuoteLine(models.Model):
    _name = 'fw.rfq.vendor.quote.line'
    _description = 'RFQ Vendor Quote Line'
    _order = 'id'

    quote_id = fields.Many2one('fw.rfq.vendor.quote', string='Vendor Quote', required=True,
                                ondelete='cascade')
    rfq_line_id = fields.Many2one('fw.rfq.line', string='Material Line', required=True)
    material_description = fields.Char(related='rfq_line_id.material_description',
                                        string='Material', store=True)
    qty = fields.Float(related='rfq_line_id.qty', string='Qty', store=True)
    currency_id = fields.Many2one(related='quote_id.currency_id', string='Currency', store=True)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    amount = fields.Monetary(string='Amount', compute='_compute_amount', store=True,
                              currency_field='currency_id')

    @api.depends('qty', 'unit_price')
    def _compute_amount(self):
        for rec in self:
            rec.amount = (rec.qty or 0.0) * (rec.unit_price or 0.0)

    @api.constrains('unit_price')
    def _check_unit_price_non_negative(self):
        for rec in self:
            if rec.unit_price < 0:
                raise ValidationError("Vendor quote unit price cannot be negative.")
