# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentCuttingOrder(models.Model):
    """Cutting Order — controls fabric cutting from fabric reservation
    through cut-panel delivery to sewing. See Production Management SRS
    s.21-27, Planning & MES SRS s.16-17, Shop Floor SRS s.14-15."""
    _name = 'garment.cutting.order'
    _description = 'Garment Cutting Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'cutting_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Cutting Number', copy=False, readonly=True, default=lambda s: _('New'))
    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, tracking=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True)
    fabric_material_id = fields.Many2one('garment.material', string='Fabric')
    color = fields.Char(string='Color')
    quantity = fields.Float(string='Quantity (PCS)', required=True)

    marker_id = fields.Many2one('garment.cutting.marker', string='Marker')
    cutting_date = fields.Date(string='Cutting Date', default=fields.Date.context_today)
    cutter_team = fields.Char(string='Cutter Team')
    line_id = fields.Many2one('garment.production.line', string='Cutting Line',
                               domain="[('department', '=', 'cutting')]")

    # Fabric issue verification (SRS s.22)
    required_fabric_qty = fields.Float(string='Required Fabric Quantity')
    issued_fabric_qty = fields.Float(string='Issued Fabric Quantity')
    fabric_ready = fields.Boolean(string='Ready For Cutting', compute='_compute_fabric_ready', store=True)

    relaxation_ids = fields.One2many('garment.fabric.relaxation', 'cutting_order_id', string='Fabric Relaxation')
    bundle_ids = fields.One2many('garment.cutting.bundle', 'cutting_order_id', string='Bundles')
    qc_ids = fields.One2many('garment.cutting.qc', 'cutting_order_id', string='Cutting QC')
    bundle_count = fields.Integer(compute='_compute_counts')

    cut_qty = fields.Float(string='Cut Quantity (PCS)', compute='_compute_cut_qty', store=True)

    status = fields.Selection([
        ('draft', 'Draft'), ('fabric_reserved', 'Fabric Reserved'), ('fabric_issued', 'Fabric Issued'),
        ('relaxation', 'Fabric Relaxation'), ('marker_ready', 'Marker Ready'), ('spreading', 'Spreading'),
        ('cutting', 'Cutting'), ('numbering', 'Numbering'), ('bundling', 'Bundling'),
        ('qc', 'QC Inspection'), ('completed', 'Completed / Sent to Sewing'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('required_fabric_qty', 'issued_fabric_qty')
    def _compute_fabric_ready(self):
        for rec in self:
            rec.fabric_ready = bool(rec.required_fabric_qty) and rec.issued_fabric_qty >= rec.required_fabric_qty

    @api.depends('bundle_ids.quantity')
    def _compute_cut_qty(self):
        for rec in self:
            rec.cut_qty = sum(rec.bundle_ids.mapped('quantity'))

    def _compute_counts(self):
        for rec in self:
            rec.bundle_count = len(rec.bundle_ids)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.cutting.order') or _('New')
        return super().create(vals_list)

    def action_send_to_sewing(self):
        self.write({'status': 'completed'})

    def action_view_bundles(self):
        self.ensure_one()
        return {
            'name': _('Cutting Bundles'), 'type': 'ir.actions.act_window', 'res_model': 'garment.cutting.bundle',
            'view_mode': 'tree,form', 'domain': [('cutting_order_id', '=', self.id)],
            'context': {'default_cutting_order_id': self.id},
        }
