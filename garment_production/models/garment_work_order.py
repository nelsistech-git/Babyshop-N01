# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentWorkOrder(models.Model):
    """Work Order — operation-level manufacturing job under a Production
    Order. See Planning & MES SRS s.13 (Work Order Management)."""
    _name = 'garment.work.order'
    _description = 'Garment Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'production_order_id, sequence'
    _rec_name = 'name'

    name = fields.Char(string='Work Order Number', copy=False, readonly=True, default=lambda s: _('New'))
    sequence = fields.Integer(default=10)
    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, ondelete='cascade')
    routing_line_id = fields.Many2one('garment.operation.routing.line', string='Routing Operation')
    operation_name = fields.Char(string='Operation', required=True)
    work_center_id = fields.Many2one('garment.work.center', string='Work Center')
    line_id = fields.Many2one('garment.production.line', string='Production Line')

    quantity = fields.Float(string='Quantity (PCS)', required=True)
    actual_qty = fields.Float(string='Actual Quantity (PCS)')
    planned_duration = fields.Float(string='Planned Duration (Hours)')
    actual_duration = fields.Float(string='Actual Duration (Hours)')

    date_start = fields.Datetime(string='Start Date/Time')
    date_end = fields.Datetime(string='End Date/Time')

    status = fields.Selection([
        ('planned', 'Planned'), ('released', 'Released'), ('running', 'Running'),
        ('hold', 'Hold'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='planned', tracking=True, group_expand='_expand_states')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.work.order') or _('New')
        return super().create(vals_list)

    def action_start(self):
        self.write({'status': 'running', 'date_start': fields.Datetime.now()})

    def action_complete(self):
        self.write({'status': 'completed', 'date_end': fields.Datetime.now()})

    def action_hold(self):
        self.write({'status': 'hold'})
