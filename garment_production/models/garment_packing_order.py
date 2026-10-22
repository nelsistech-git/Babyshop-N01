# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentPackingOrder(models.Model):
    """Packing Order — Folding -> Poly Packing -> Carton Packing -> Carton
    Label -> Finished Goods Store. See Production Management SRS s.49-51,
    Planning & MES SRS s.42-43."""
    _name = 'garment.packing.order'
    _description = 'Garment Packing Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Packing Number', copy=False, readonly=True, default=lambda s: _('New'))
    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, tracking=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='production_order_id.buyer_id', store=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True)
    carton_size = fields.Char(string='Carton Size')
    quantity = fields.Float(string='Quantity (PCS)', required=True)
    packed_qty = fields.Float(string='Packed Quantity (PCS)', compute='_compute_packed', store=True)
    destination = fields.Char(string='Destination')
    warehouse_id = fields.Many2one('garment.warehouse', string='Finished Goods Warehouse')
    shipment_date = fields.Date(string='Shipment Date')

    carton_ids = fields.One2many('garment.packing.carton', 'packing_order_id', string='Cartons')
    carton_count = fields.Integer(compute='_compute_counts')

    status = fields.Selection([
        ('draft', 'Draft'), ('folding', 'Folding'), ('poly_packing', 'Poly Packing'),
        ('carton_packing', 'Carton Packing'), ('labeled', 'Carton Labeled'), ('completed', 'Finished Goods Store'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('carton_ids.quantity')
    def _compute_packed(self):
        for rec in self:
            rec.packed_qty = sum(rec.carton_ids.mapped('quantity'))

    def _compute_counts(self):
        for rec in self:
            rec.carton_count = len(rec.carton_ids)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.packing.order') or _('New')
        return super().create(vals_list)

    def action_view_cartons(self):
        self.ensure_one()
        return {
            'name': _('Cartons'), 'type': 'ir.actions.act_window', 'res_model': 'garment.packing.carton',
            'view_mode': 'tree,form', 'domain': [('packing_order_id', '=', self.id)],
            'context': {'default_packing_order_id': self.id},
        }


class GarmentPackingCarton(models.Model):
    """Carton tracking. See Production Management SRS s.51, Planning & MES
    SRS s.43 (Carton Tracking System)."""
    _name = 'garment.packing.carton'
    _description = 'Garment Packing Carton'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Carton Number', copy=False, readonly=True, default=lambda s: _('New'))
    packing_order_id = fields.Many2one('garment.packing.order', string='Packing Order',
                                       required=True, ondelete='cascade')
    style_id = fields.Many2one('garment.style', related='packing_order_id.style_id', string='Style', store=True)
    size_ratio = fields.Char(string='Size Ratio')
    color = fields.Char(string='Color')
    quantity = fields.Float(string='Quantity (PCS)', required=True)
    weight = fields.Float(string='Weight (KG)')
    destination = fields.Char(string='Destination')
    barcode = fields.Char(string='Barcode')
    status = fields.Selection([
        ('ready', 'Ready'), ('shipped', 'Shipped'),
    ], string='Status', default='ready')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.packing.carton') or _('New')
            if not vals.get('barcode'):
                vals['barcode'] = vals.get('name')
        return super().create(vals_list)
