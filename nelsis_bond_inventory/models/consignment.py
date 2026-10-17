# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class BondConsignment(models.Model):
    """Imported consignment (LC / Bill of Entry) received in one or more partial receipts."""
    _name = 'bond.inventory.consignment'
    _inherit = ['bond.inventory.reference.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Bond Consignment'
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', required=True, readonly=True, index=True,
                                 default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Supplier', required=True, tracking=True)
    lc_ref = fields.Reference(selection='_selection_lc_models', string='LC Record')
    lc_number = fields.Char(string='LC Number', tracking=True)
    boe_number = fields.Char(string='Bill of Entry No.', tracking=True)
    boe_date = fields.Date(string='Bill of Entry Date')
    customs_ref = fields.Reference(selection='_selection_customs_models', string='Customs Document Record')
    state = fields.Selection(
        [('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed'), ('cancelled', 'Cancelled')],
        default='draft', required=True, copy=False, readonly=True, tracking=True, index=True)
    line_ids = fields.One2many('bond.inventory.consignment.line', 'consignment_id', string='Lines', copy=True)
    receipt_ids = fields.One2many('bond.inventory.receipt', 'consignment_id', string='Receipts')
    receipt_count = fields.Integer(compute='_compute_receipt_count')
    lc_label = fields.Char(string='LC', compute='_compute_lc_label')
    note = fields.Text()

    @api.depends('lc_ref', 'lc_number')
    def _compute_lc_label(self):
        for rec in self:
            rec.lc_label = rec.lc_ref.sudo().display_name if rec.lc_ref else (rec.lc_number or False)

    @api.depends('receipt_ids')
    def _compute_receipt_count(self):
        for rec in self:
            rec.receipt_count = len(rec.receipt_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bond.inventory.consignment') or _('New')
        return super().create(vals_list)

    def unlink(self):
        if any(rec.state not in ('draft', 'cancelled') for rec in self):
            raise UserError(_('Only draft or cancelled consignments can be deleted.'))
        return super().unlink()

    def action_open(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft consignments can be opened.'))
            if not rec.line_ids:
                raise UserError(_('Add at least one consignment line.'))
            if not (rec.lc_ref or rec.lc_number):
                raise UserError(_('An LC reference or number is required.'))
            if not rec.boe_number:
                raise UserError(_('The Bill of Entry number is required.'))
            rec.state = 'open'

    def action_close(self):
        for rec in self:
            if rec.state != 'open':
                raise UserError(_('Only open consignments can be closed.'))
            rec.state = 'closed'

    def action_reopen(self):
        for rec in self:
            if rec.state != 'closed':
                raise UserError(_('Only closed consignments can be reopened.'))
            rec.state = 'open'

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'open'):
                raise UserError(_('Only draft or open consignments can be cancelled.'))
            if rec.receipt_ids.filtered(lambda r: r.state not in ('cancelled', 'rejected')):
                raise UserError(_('Consignment %s has active receipts and cannot be cancelled.', rec.name))
            rec.state = 'cancelled'

    def action_view_receipts(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('nelsis_bond_inventory.action_bond_receipt')
        action['domain'] = [('consignment_id', '=', self.id)]
        action['context'] = {'default_consignment_id': self.id}
        return action


class BondConsignmentLine(models.Model):
    _name = 'bond.inventory.consignment.line'
    _description = 'Bond Consignment Line'
    _order = 'consignment_id, id'

    consignment_id = fields.Many2one('bond.inventory.consignment', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='consignment_id.company_id', store=True, index=True)
    product_id = fields.Many2one('product.product', required=True, domain=[('detailed_type', '=', 'product')])
    hs_code = fields.Char(string='HS Code', compute='_compute_hs_code', store=True, readonly=False, precompute=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True,
                                     compute='_compute_product_uom_id', store=True, readonly=False,
                                     precompute=True)
    declared_qty = fields.Float(string='Declared Qty', digits='Product Unit of Measure', required=True)
    receipt_line_ids = fields.One2many('bond.inventory.receipt.line', 'consignment_line_id')
    received_qty = fields.Float(string='Received Qty', digits='Product Unit of Measure',
                                compute='_compute_received')
    accepted_qty = fields.Float(string='Accepted Qty', digits='Product Unit of Measure',
                                compute='_compute_received')
    remaining_qty = fields.Float(string='Remaining Qty', digits='Product Unit of Measure',
                                 compute='_compute_received')

    @api.depends('product_id')
    def _compute_hs_code(self):
        for line in self:
            line.hs_code = line.product_id.bond_hs_code or line.hs_code

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.depends('declared_qty', 'receipt_line_ids.received_qty', 'receipt_line_ids.accepted_qty',
                 'receipt_line_ids.receipt_id.state')
    def _compute_received(self):
        for line in self:
            done = line.receipt_line_ids.filtered(lambda l: l.receipt_id.state == 'done')
            line.received_qty = sum(done.mapped('received_qty'))
            line.accepted_qty = sum(done.mapped('accepted_qty'))
            line.remaining_qty = max(line.declared_qty - line.received_qty, 0.0)

    @api.constrains('declared_qty', 'product_id', 'product_uom_id')
    def _check_line(self):
        for line in self:
            if float_compare(line.declared_qty, 0.0, precision_rounding=line.product_uom_id.rounding or 0.01) <= 0:
                raise ValidationError(_('The declared quantity must be positive.'))
            if line.product_uom_id.category_id != line.product_id.uom_id.category_id:
                raise ValidationError(_(
                    'The unit of measure of "%s" must be in the same category as the product unit. '
                    'No automatic conversion between incompatible units (e.g. pieces to area) is made.',
                    line.product_id.display_name))
