# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FwBundle(models.Model):
    _name = 'fw.bundle'
    _description = 'Footwear WIP Cutting Bundle'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Bundle Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.bundle') or 'New')
    barcode = fields.Char(string='Barcode', copy=False,
                           help="Print this value as a barcode label to attach to the "
                                "physical bundle ticket.")

    production_order_id = fields.Many2one('fw.production.order', string='Production Order',
                                           required=True, tracking=True)
    style_id = fields.Many2one(related='production_order_id.style_id', string='Style',
                                store=True)
    color_id = fields.Many2one(related='production_order_id.color_id', string='Color',
                                store=True)
    size_id = fields.Many2one('fw.size', string='Size')

    bundle_qty = fields.Integer(string='Bundle Qty (Pairs/Pieces)', required=True, default=0)

    @api.constrains('bundle_qty')
    def _check_bundle_qty_non_negative(self):
        for rec in self:
            if rec.bundle_qty < 0:
                raise ValidationError("Bundle Qty cannot be negative.")

    current_stage = fields.Selection([
        ('cutting', 'Cutting'),
        ('stitching', 'Stitching / Upper'),
        ('assembly', 'Assembly / Lasting'),
        ('finishing', 'Finishing / Packing'),
    ], string='Current Stage', default='cutting', tracking=True)

    current_location_id = fields.Many2one('stock.location', string='Current Stock Location')

    state = fields.Selection([
        ('created', 'Created'),
        ('in_process', 'In Process'),
        ('completed', 'Completed'),
    ], string='Status', default='created', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('barcode_uniq', 'unique(barcode)', 'Bundle Barcode must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.bundle') or 'New'
            if not vals.get('barcode'):
                vals['barcode'] = vals['name'].replace('/', '')
        return super().create(vals_list)

    def action_move_next_stage(self):
        stage_order = ['cutting', 'stitching', 'assembly', 'finishing']
        for rec in self:
            if rec.current_stage in stage_order:
                idx = stage_order.index(rec.current_stage)
                if idx < len(stage_order) - 1:
                    rec.write({'current_stage': stage_order[idx + 1], 'state': 'in_process'})
                else:
                    rec.write({'state': 'completed'})

    def action_reset_created(self):
        self.write({'state': 'created', 'current_stage': 'cutting'})
