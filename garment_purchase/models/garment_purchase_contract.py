# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentPurchaseContract(models.Model):
    """Purchase Contract + Blanket Purchase Agreement (SRS sections 30-31)
    — garment.purchase.contract."""
    _name = 'garment.purchase.contract'
    _description = 'Garment Purchase Contract'
    _inherit = ['mail.thread']
    _order = 'start_date desc'

    contract_number = fields.Char(string='Contract Number', copy=False, readonly=True, default=lambda s: _('New'))
    contract_type = fields.Selection([
        ('standard', 'Standard Contract'), ('blanket', 'Blanket Purchase Agreement'),
    ], string='Contract Type', default='standard', required=True)
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True)
    material_category = fields.Selection([
        ('fabric', 'Fabric'), ('trim', 'Trim/Accessory'), ('packaging', 'Packaging'), ('other', 'Other'),
    ], string='Material Category')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    total_committed_qty = fields.Float(string='Total Committed Quantity',
                                        help='Used for blanket agreements: overall volume commitment.')
    consumed_qty = fields.Float(string='Consumed Quantity', compute='_compute_consumed_qty', store=True)
    remaining_qty = fields.Float(string='Remaining Quantity', compute='_compute_consumed_qty', store=True)
    price_terms = fields.Text(string='Price Terms')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    order_ids = fields.One2many('garment.purchase.order', 'contract_id', string='Purchase Orders')
    status = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired'), ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('order_ids.line_ids.quantity', 'total_committed_qty')
    def _compute_consumed_qty(self):
        for rec in self:
            consumed = sum(rec.order_ids.mapped('line_ids').mapped('quantity'))
            rec.consumed_qty = consumed
            rec.remaining_qty = max(0.0, (rec.total_committed_qty or 0.0) - consumed)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('contract_number', _('New')) == _('New'):
                vals['contract_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.purchase.contract') or _('New')
        return super().create(vals_list)
