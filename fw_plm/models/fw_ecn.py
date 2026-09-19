# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwEcn(models.Model):
    _name = 'fw.ecn'
    _description = 'Footwear Engineering Change Notice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_requested desc'

    name = fields.Char(string='ECN Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.ecn') or 'New')
    style_id = fields.Many2one('fw.style', string='Style', required=True, tracking=True,
                                ondelete='cascade')
    bom_id = fields.Many2one('fw.bom.version', string='Related BOM Version',
                              domain="[('style_id', '=', style_id)]")
    techpack_id = fields.Many2one('fw.techpack', string='Related Tech Pack',
                                   domain="[('style_id', '=', style_id)]")

    change_reason = fields.Selection([
        ('cost', 'Cost Reduction'),
        ('quality', 'Quality Improvement'),
        ('availability', 'Material Availability'),
        ('buyer_request', 'Buyer Request'),
        ('compliance', 'Compliance / Safety'),
        ('other', 'Other'),
    ], string='Change Reason', required=True, tracking=True)

    description = fields.Text(string='Change Description', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('implemented', 'Implemented'),
    ], string='Status', default='draft', tracking=True)

    requested_by = fields.Many2one('res.users', string='Requested By',
                                    default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    date_requested = fields.Date(string='Date Requested', default=fields.Date.context_today)
    date_approved = fields.Date(string='Date Approved', readonly=True, copy=False)

    line_ids = fields.One2many('fw.ecn.line', 'ecn_id', string='Component Changes')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.ecn') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Please add at least one component change line before submitting.")
        self.write({'state': 'submitted'})

    def action_approve(self):
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'date_approved': fields.Date.context_today(self),
        })

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_implement(self):
        """Apply the ECN component changes onto the linked BOM version, if any."""
        for rec in self:
            if rec.state != 'approved':
                raise UserError("Only approved ECNs can be implemented.")
            if rec.bom_id:
                for line in rec.line_ids:
                    if line.new_component_id:
                        bom_line = rec.bom_id.line_ids.filtered(
                            lambda l: l.part_name == line.part_name)
                        if bom_line:
                            bom_line[0].write({
                                'component_id': line.new_component_id.id,
                                'qty_per_pair': line.new_qty or bom_line[0].qty_per_pair,
                            })
        self.write({'state': 'implemented'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'approved_by': False, 'date_approved': False})


class FwEcnLine(models.Model):
    _name = 'fw.ecn.line'
    _description = 'ECN Component Change Line'
    _order = 'id'

    ecn_id = fields.Many2one('fw.ecn', string='ECN', required=True, ondelete='cascade')
    part_name = fields.Char(string='Part', required=True)
    old_component_id = fields.Many2one('product.product', string='Old Component')
    new_component_id = fields.Many2one('product.product', string='New Component')
    old_qty = fields.Float(string='Old Qty per Pair')
    new_qty = fields.Float(string='New Qty per Pair')
    remarks = fields.Char(string='Remarks')

    @api.constrains('old_qty', 'new_qty')
    def _check_non_negative(self):
        for rec in self:
            if rec.old_qty < 0:
                raise ValidationError("Old Qty per Pair cannot be negative.")
            if rec.new_qty < 0:
                raise ValidationError("New Qty per Pair cannot be negative.")
