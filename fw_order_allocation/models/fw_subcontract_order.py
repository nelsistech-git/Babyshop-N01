# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwSubcontractOrder(models.Model):
    _name = 'fw.subcontract.order'
    _description = 'Footwear Subcontract (CMT) Order - Material Out / Goods In'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Subcontract Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.subcontract.order') or 'New')
    allocation_line_id = fields.Many2one('fw.order.allocation.line', string='Allocation Line',
                                          required=True, tracking=True)
    subcontractor_id = fields.Many2one(related='allocation_line_id.factory_id',
                                        string='Subcontractor', store=True)
    allocation_id = fields.Many2one(related='allocation_line_id.allocation_id',
                                     string='Order Allocation', store=True)
    style_id = fields.Many2one(related='allocation_id.style_id', string='Style', store=True)
    color_id = fields.Many2one(related='allocation_id.color_id', string='Color', store=True)
    buyer_order_id = fields.Many2one(related='allocation_id.buyer_order_id',
                                      string='Buyer Order', store=True)

    qty = fields.Integer(related='allocation_line_id.qty_allocated', string='Contracted Qty',
                          store=True)
    currency_id = fields.Many2one(related='allocation_line_id.currency_id', string='Currency',
                                   store=True)
    conversion_cost_per_pair = fields.Monetary(string='CMT Rate (per Pair)',
                                                currency_field='currency_id')
    total_conversion_cost = fields.Monetary(string='Total CMT Cost', compute='_compute_totals',
                                             store=True, currency_field='currency_id')

    material_out_line_ids = fields.One2many('fw.subcontract.material.line', 'subcontract_id',
                                             string='Material Sent Out')
    finished_goods_in_line_ids = fields.One2many('fw.subcontract.finished.line',
                                                  'subcontract_id', string='Finished Goods Received')

    total_qty_received = fields.Integer(string='Total Qty Received', compute='_compute_totals',
                                         store=True)
    balance_qty = fields.Integer(string='Balance to Receive', compute='_compute_totals',
                                  store=True)

    aql_inspection_id = fields.Many2one('fw.aql.inspection', string='Incoming QC Inspection',
                                         help="Optional link to an AQL Inspection performed on "
                                              "the finished goods received back from the "
                                              "subcontractor.")

    state = fields.Selection([
        ('material_sent', 'Material Sent'),
        ('in_process', 'In Process at Subcontractor'),
        ('goods_received', 'Goods Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='material_sent', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.subcontract.order') or 'New'
        return super().create(vals_list)

    @api.depends('qty', 'conversion_cost_per_pair', 'finished_goods_in_line_ids.qty_received')
    def _compute_totals(self):
        for rec in self:
            rec.total_conversion_cost = (rec.qty or 0) * (rec.conversion_cost_per_pair or 0.0)
            rec.total_qty_received = sum(rec.finished_goods_in_line_ids.mapped('qty_received'))
            rec.balance_qty = (rec.qty or 0) - rec.total_qty_received

    def action_start_process(self):
        for rec in self:
            if not rec.material_out_line_ids:
                raise UserError("Please record at least one Material Sent Out line first.")
        self.write({'state': 'in_process'})

    def action_mark_goods_received(self):
        for rec in self:
            if not rec.finished_goods_in_line_ids:
                raise UserError("Please record at least one Finished Goods Received line first.")
        self.write({'state': 'goods_received'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'material_sent'})


class FwSubcontractMaterialLine(models.Model):
    _name = 'fw.subcontract.material.line'
    _description = 'Subcontract Material Sent Out Line'
    _order = 'sent_date desc, id'

    subcontract_id = fields.Many2one('fw.subcontract.order', string='Subcontract Order',
                                      required=True, ondelete='cascade')
    component_id = fields.Many2one('product.product', string='Material / Component',
                                    required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM',
                              default=lambda self: self.env.ref('uom.product_uom_unit', False))
    qty_sent = fields.Float(string='Qty Sent', required=True, default=0.0)
    sent_date = fields.Date(string='Sent Date', default=fields.Date.context_today)
    challan_no = fields.Char(string='Delivery Challan No.',
                              help="Reference number of the outgoing delivery/gate pass "
                                   "document accompanying the material.")
    remarks = fields.Char(string='Remarks')

    @api.constrains('qty_sent')
    def _check_qty_sent_non_negative(self):
        for rec in self:
            if rec.qty_sent < 0:
                raise ValidationError("Qty Sent cannot be negative.")


class FwSubcontractFinishedLine(models.Model):
    _name = 'fw.subcontract.finished.line'
    _description = 'Subcontract Finished Goods Received Line'
    _order = 'received_date desc, id'

    subcontract_id = fields.Many2one('fw.subcontract.order', string='Subcontract Order',
                                      required=True, ondelete='cascade')
    qty_received = fields.Integer(string='Qty Received (Good)', required=True, default=0)
    defect_qty = fields.Integer(string='Defect Qty', default=0)
    received_date = fields.Date(string='Received Date', default=fields.Date.context_today)
    challan_no = fields.Char(string='Delivery Challan No.')
    remarks = fields.Char(string='Remarks')

    @api.constrains('qty_received', 'defect_qty')
    def _check_non_negative(self):
        for rec in self:
            if rec.qty_received < 0:
                raise ValidationError("Qty Received cannot be negative.")
            if rec.defect_qty < 0:
                raise ValidationError("Defect Qty cannot be negative.")
