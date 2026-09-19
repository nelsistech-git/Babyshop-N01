# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwMaterialGrn(models.Model):
    _name = 'fw.material.grn'
    _description = 'Footwear Material GRN (Goods Receipt & Quality Inspection)'
    _inherit = ['mail.thread']
    _order = 'received_date desc'

    name = fields.Char(string='GRN Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.material.grn') or 'New')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True,
                                   domain="[('supplier_rank', '>', 0)]", tracking=True)
    po_reference = fields.Char(string='PO Reference')

    material_description = fields.Char(string='Material Description', required=True)
    uom_id = fields.Many2one('uom.uom', string='UoM',
                              default=lambda self: self.env.ref('uom.product_uom_unit', False))

    received_date = fields.Date(string='Received Date', default=fields.Date.context_today)
    received_qty = fields.Float(string='Received Qty', required=True, default=0.0)
    accepted_qty = fields.Float(string='Accepted Qty', default=0.0)
    rejected_qty = fields.Float(string='Rejected Qty', compute='_compute_rejected_qty',
                                 store=True)
    acceptance_rate = fields.Float(string='Acceptance Rate (%)', compute='_compute_rejected_qty',
                                    store=True)

    quality_remarks = fields.Text(string='Quality Remarks')
    inspected_by = fields.Many2one('res.users', string='Inspected By',
                                    default=lambda self: self.env.user)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('inspected', 'Inspected'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.material.grn') or 'New'
        return super().create(vals_list)

    @api.depends('received_qty', 'accepted_qty')
    def _compute_rejected_qty(self):
        for rec in self:
            rec.rejected_qty = max((rec.received_qty or 0.0) - (rec.accepted_qty or 0.0), 0.0)
            rec.acceptance_rate = (rec.accepted_qty / rec.received_qty * 100.0) \
                if rec.received_qty else 0.0

    @api.constrains('received_qty', 'accepted_qty')
    def _check_non_negative(self):
        for rec in self:
            if rec.received_qty < 0:
                raise ValidationError("Received Qty cannot be negative.")
            if rec.accepted_qty < 0:
                raise ValidationError("Accepted Qty cannot be negative.")

    def action_confirm_inspection(self):
        for rec in self:
            if rec.received_qty <= 0:
                raise UserError("Received quantity must be greater than zero.")
            if rec.accepted_qty > rec.received_qty:
                raise UserError("Accepted quantity cannot exceed received quantity.")
        self.write({'state': 'inspected'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
