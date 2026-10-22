# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentProductionPlan(models.Model):
    """Production Plan — converts a confirmed buyer order/handover into a
    production schedule. See Production Management SRS s.8-9, Planning & MES
    SRS s.6-7, Shop Floor SRS s.12."""
    _name = 'garment.production.plan'
    _description = 'Garment Production Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'
    _rec_name = 'plan_number'

    plan_number = fields.Char(string='Production Plan Number', copy=False, readonly=True,
                               default=lambda s: _('New'))
    plan_type = fields.Selection([
        ('long_term', 'Long Term (3-12 Months)'), ('medium_term', 'Medium Term (1-3 Months)'),
        ('short_term', 'Short Term (Daily/Weekly)'),
    ], string='Plan Type', default='short_term', required=True, tracking=True)

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    order_id = fields.Many2one('garment.order', string='Sales/Production Order')
    order_confirmation_id = fields.Many2one('garment.merch.order.confirmation', string='Order Confirmation')
    handover_id = fields.Many2one('garment.merch.handover', string='Merchandising Handover')
    tna_id = fields.Many2one('garment.tna', string='TNA')
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    bom_id = fields.Many2one('garment.bom', string='BOM')
    routing_id = fields.Many2one('garment.operation.routing', string='Routing',
                                  domain="[('style_id', '=', style_id)]")

    quantity = fields.Float(string='Quantity (PCS)', required=True, tracking=True)
    uom = fields.Char(string='UoM', default='PCS')
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    delivery_date = fields.Date(string='Delivery Date', tracking=True)
    production_line_id = fields.Many2one('garment.production.line', string='Production Line')
    priority = fields.Selection([
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent'),
    ], string='Priority', default='normal', tracking=True)

    # Capacity / material availability check (SRS s.10-11)
    available_capacity = fields.Float(string='Available Capacity (PCS)')
    material_available = fields.Boolean(string='Material Available')
    load_status = fields.Selection([
        ('available', 'Available Capacity'), ('over_capacity', 'Over Capacity'), ('delay_risk', 'Delay Risk'),
    ], string='Load Status', compute='_compute_load_status', store=True)
    shortage_qty = fields.Float(string='Capacity Shortage (PCS)', compute='_compute_load_status', store=True)

    status = fields.Selection([
        ('draft', 'Draft'), ('planned', 'Planned'), ('manager_approval', 'Pending Manager Approval'),
        ('approved', 'Approved'), ('released', 'Released to Production'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')

    capacity_plan_ids = fields.One2many('garment.capacity.plan', 'plan_id', string='Capacity Plans')
    allocation_ids = fields.One2many('garment.line.allocation', 'plan_id', string='Line Allocations')
    approval_ids = fields.One2many('garment.production.approval', 'plan_id', string='Approvals')
    production_order_ids = fields.One2many('garment.production.order', 'plan_id', string='Production Orders')
    production_order_count = fields.Integer(compute='_compute_counts')

    notes = fields.Text(string='Planning Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('plan_number_uniq', 'unique(plan_number, company_id)', 'Production Plan Number must be unique per company!'),
    ]

    @api.depends('quantity', 'available_capacity')
    def _compute_load_status(self):
        for rec in self:
            if not rec.available_capacity:
                rec.load_status = 'available'
                rec.shortage_qty = 0.0
                continue
            if rec.quantity <= rec.available_capacity:
                rec.load_status = 'available'
                rec.shortage_qty = 0.0
            else:
                rec.shortage_qty = rec.quantity - rec.available_capacity
                rec.load_status = 'delay_risk' if rec.shortage_qty > (rec.quantity * 0.1) else 'over_capacity'

    def _compute_counts(self):
        for rec in self:
            rec.production_order_count = len(rec.production_order_ids)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('plan_number', _('New')) == _('New'):
                vals['plan_number'] = self.env['ir.sequence'].next_by_code('garment.production.plan') or _('New')
        return super().create(vals_list)

    def action_submit_for_approval(self):
        self.write({'status': 'manager_approval'})

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_release(self):
        self.write({'status': 'released'})

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_reset_draft(self):
        self.write({'status': 'draft'})

    def action_view_production_orders(self):
        self.ensure_one()
        return {
            'name': _('Production Orders'), 'type': 'ir.actions.act_window', 'res_model': 'garment.production.order',
            'view_mode': 'tree,form', 'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }
