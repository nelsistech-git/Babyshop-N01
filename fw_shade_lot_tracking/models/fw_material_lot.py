# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwMaterialLot(models.Model):
    _name = 'fw.material.lot'
    _description = 'Footwear Material Lot / Batch (Shade Tracking)'
    _inherit = ['mail.thread']
    _order = 'received_date desc'

    name = fields.Char(string='System Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.material.lot') or 'New')
    lot_no = fields.Char(string="Supplier's Lot / Batch No.", required=True, tracking=True)
    shade_code = fields.Char(string='Shade / Color Batch Code', tracking=True,
                              help="Critical for leather, synthetic upper material, and "
                                   "other materials where shade can vary batch to batch.")

    component_id = fields.Many2one('product.product', string='Material / Component',
                                    required=True)
    supplier_id = fields.Many2one('res.partner', string='Supplier',
                                   domain="[('supplier_rank', '>', 0)]")
    grn_id = fields.Many2one('fw.material.grn', string='Source GRN',
                              help="Optional link to the Goods Receipt this lot came from, "
                                   "for traceability.")

    uom_id = fields.Many2one('uom.uom', string='UoM',
                              default=lambda self: self.env.ref('uom.product_uom_unit', False))
    received_qty = fields.Float(string='Received Qty', required=True, default=0.0)
    received_date = fields.Date(string='Received Date', default=fields.Date.context_today)

    consumption_ids = fields.One2many('fw.lot.consumption', 'lot_id', string='Consumption Records')
    consumed_qty = fields.Float(string='Consumed Qty', compute='_compute_qty', store=True)
    remaining_qty = fields.Float(string='Remaining Qty', compute='_compute_qty', store=True)

    state = fields.Selection([
        ('active', 'Active'),
        ('quarantine', 'Quarantine (Shade Hold)'),
        ('exhausted', 'Exhausted'),
    ], string='Status', default='active', tracking=True)

    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.material.lot') or 'New'
        return super().create(vals_list)

    @api.depends('received_qty', 'consumption_ids.qty_used')
    def _compute_qty(self):
        for rec in self:
            rec.consumed_qty = sum(rec.consumption_ids.mapped('qty_used'))
            rec.remaining_qty = (rec.received_qty or 0.0) - rec.consumed_qty

    def action_set_quarantine(self):
        self.write({'state': 'quarantine'})

    def action_reactivate(self):
        self.write({'state': 'active'})

    def action_mark_exhausted(self):
        self.write({'state': 'exhausted'})


class FwLotConsumption(models.Model):
    _name = 'fw.lot.consumption'
    _description = 'Material Lot Consumption Record'
    _order = 'consumption_date desc, id desc'

    lot_id = fields.Many2one('fw.material.lot', string='Material Lot', required=True,
                              ondelete='cascade')
    shade_code = fields.Char(related='lot_id.shade_code', string='Shade Code', store=True)
    production_order_id = fields.Many2one('fw.production.order', string='Production Order')
    bundle_id = fields.Many2one('fw.bundle', string='WIP Bundle')
    qty_used = fields.Float(string='Qty Used', required=True, default=0.0)
    consumption_date = fields.Date(string='Consumption Date', default=fields.Date.context_today)
    remarks = fields.Char(string='Remarks')

    @api.constrains('qty_used')
    def _check_qty_used(self):
        for rec in self:
            if rec.qty_used <= 0:
                raise ValidationError("Consumed quantity must be greater than zero.")
            if rec.lot_id.state == 'quarantine':
                raise ValidationError(
                    "Lot '%s' is under Quarantine (shade hold) and cannot be consumed "
                    "until it is reactivated." % rec.lot_id.name)
            if rec.lot_id.remaining_qty < 0:
                raise ValidationError(
                    "This consumption would exceed the remaining quantity of lot '%s' "
                    "(%.2f available)." % (
                        rec.lot_id.name,
                        rec.lot_id.remaining_qty + rec.qty_used))
