# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from .constants import G_OFFICER, require_group


class NelsisCommercialShipment(models.Model):
    _name = 'nelsis.commercial.shipment'
    _description = 'Commercial Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Shipment Reference', readonly=True, copy=False, default=lambda self: _('New'))
    file_id = fields.Many2one('nelsis.commercial.file', required=True, ondelete='restrict', index=True, tracking=True)
    company_id = fields.Many2one(related='file_id.company_id', store=True, index=True)
    lc_display = fields.Char(related='file_id.lc_display', string='LC')
    partner_id = fields.Many2one(related='file_id.partner_id', string='Supplier', store=True)
    transport_mode = fields.Selection([('sea', 'Sea'), ('air', 'Air'), ('road', 'Road'), ('rail', 'Rail')],
                                      default='sea', required=True)
    origin_country_id = fields.Many2one('res.country', string='Origin')
    port_loading = fields.Char(string='Port / Airport of Loading')
    destination = fields.Char()
    vessel = fields.Char(string='Vessel / Flight')
    container_no = fields.Char(string='Container No.')
    transport_doc_no = fields.Char(string='B/L or AWB No.', tracking=True)
    shipment_date = fields.Date(tracking=True)
    eta_date = fields.Date(string='Estimated Arrival', tracking=True)
    arrival_date = fields.Date(string='Actual Arrival', tracking=True)
    is_partial = fields.Boolean(string='Partial Shipment')
    partial_no = fields.Integer(string='Partial No.', default=1)
    state = fields.Selection([('planned', 'Planned'), ('in_transit', 'In Transit'),
                              ('arrived', 'Arrived'), ('cancel', 'Cancelled')],
                             default='planned', required=True, tracking=True, copy=False)
    picking_ids = fields.Many2many('stock.picking', 'nelsis_commercial_shipment_picking_rel',
                                   'shipment_id', 'picking_id', string='Warehouse Receipts')
    document_ids = fields.One2many('nelsis.commercial.document', 'shipment_id')
    boe_ids = fields.One2many('nelsis.commercial.boe', 'shipment_id')
    line_ids = fields.One2many('nelsis.commercial.line', 'shipment_id')
    receipt_state = fields.Selection(
        [('none', 'No Receipt Linked'), ('pending', 'Receipt Pending'), ('validated', 'Receipt Validated')],
        compute='_compute_receipt_state')

    @api.depends('picking_ids.state')
    def _compute_receipt_state(self):
        for rec in self:
            if not rec.picking_ids:
                rec.receipt_state = 'none'
            elif all(p.state == 'done' for p in rec.picking_ids):
                rec.receipt_state = 'validated'
            else:
                rec.receipt_state = 'pending'

    @api.constrains('shipment_date', 'arrival_date')
    def _check_dates(self):
        for rec in self:
            if rec.shipment_date and rec.arrival_date and rec.arrival_date < rec.shipment_date:
                raise ValidationError(_("Arrival date cannot be earlier than shipment date."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.pop('state', None)
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('nelsis.commercial.shipment') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals:
            require_group(self.env, G_OFFICER)
        return super().write(vals)

    def unlink(self):
        if any(rec.state != 'planned' for rec in self):
            raise UserError(_("Only planned shipments can be deleted. Cancel the shipment instead."))
        return super().unlink()

    def action_in_transit(self):
        require_group(self.env, G_OFFICER)
        if any(r.state != 'planned' for r in self):
            raise UserError(_("Only planned shipments can be marked in transit."))
        self.write({'state': 'in_transit'})

    def action_arrived(self):
        require_group(self.env, G_OFFICER)
        if any(r.state not in ('planned', 'in_transit') for r in self):
            raise UserError(_("This shipment cannot be marked as arrived."))
        for rec in self:
            rec.write({'state': 'arrived', 'arrival_date': rec.arrival_date or fields.Date.context_today(self)})

    def action_cancel(self):
        require_group(self.env, G_OFFICER)
        if any(r.state == 'arrived' for r in self):
            raise UserError(_("An arrived shipment cannot be cancelled."))
        self.write({'state': 'cancel'})
