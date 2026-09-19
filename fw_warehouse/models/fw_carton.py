# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwCarton(models.Model):
    _name = 'fw.carton'
    _description = 'Footwear Packing Carton'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Carton Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.carton') or 'New')
    barcode = fields.Char(string='Barcode', copy=False,
                           help="Print this value as a barcode label to attach to the "
                                "physical carton.")
    carton_no = fields.Integer(string='Carton No.',
                                help="Sequential carton number within the shipment, "
                                     "e.g. 5 (of 120).")

    order_line_id = fields.Many2one('fw.buyer.order.line', string='Buyer Order Line')
    style_id = fields.Many2one(related='order_line_id.style_id', string='Style', store=True)
    color_id = fields.Many2one(related='order_line_id.color_id', string='Color', store=True)
    shipment_id = fields.Many2one('fw.shipment', string='Shipment', tracking=True)

    size_line_ids = fields.One2many('fw.carton.size.line', 'carton_id', string='Size Content')
    total_qty = fields.Integer(string='Total Qty (Pairs)', compute='_compute_total_qty',
                                store=True)

    gross_weight = fields.Float(string='Gross Weight (kg)')
    net_weight = fields.Float(string='Net Weight (kg)')
    length_cm = fields.Float(string='Length (cm)')
    width_cm = fields.Float(string='Width (cm)')
    height_cm = fields.Float(string='Height (cm)')

    @api.constrains('gross_weight', 'net_weight', 'length_cm', 'width_cm', 'height_cm')
    def _check_non_negative(self):
        for rec in self:
            for field_name, label in [
                ('gross_weight', 'Gross Weight'), ('net_weight', 'Net Weight'),
                ('length_cm', 'Length'), ('width_cm', 'Width'), ('height_cm', 'Height'),
            ]:
                if rec[field_name] < 0:
                    raise ValidationError("%s cannot be negative." % label)

    state = fields.Selection([
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
    ], string='Status', default='packed', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('barcode_uniq', 'unique(barcode)', 'Carton Barcode must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.carton') or 'New'
            if not vals.get('barcode'):
                vals['barcode'] = vals['name'].replace('/', '')
        return super().create(vals_list)

    @api.depends('size_line_ids.qty')
    def _compute_total_qty(self):
        for rec in self:
            rec.total_qty = sum(rec.size_line_ids.mapped('qty'))

    def action_mark_shipped(self):
        self.write({'state': 'shipped'})

    def action_reset_packed(self):
        self.write({'state': 'packed'})


class FwCartonSizeLine(models.Model):
    _name = 'fw.carton.size.line'
    _description = 'Carton Size Content Line'
    _order = 'size_id'

    carton_id = fields.Many2one('fw.carton', string='Carton', required=True, ondelete='cascade')
    size_id = fields.Many2one('fw.size', string='Size', required=True)
    qty = fields.Integer(string='Qty', required=True, default=1)

    _sql_constraints = [
        ('carton_size_uniq', 'unique(carton_id, size_id)',
         'This size already exists in this carton\'s content list!'),
    ]

    @api.constrains('qty')
    def _check_qty_non_negative(self):
        for rec in self:
            if rec.qty < 0:
                raise ValidationError("Size content Qty cannot be negative.")
