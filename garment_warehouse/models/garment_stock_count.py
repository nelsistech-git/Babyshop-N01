# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Cycle Counting / Physical Inventory Count (SRS "Cycle Counting" /
"Inventory Counting System" — Daily/Weekly/Monthly/Annual counts, ABC
Classification) and Inventory Adjustment (SRS "Inventory Adjustment" —
Adjustment Request -> Manager Approval -> Stock Update -> Audit Record) —
garment.stock.count / garment.stock.count.line. Approving a count posts one
garment.stock.move (adjustment_in/adjustment_out) per line with a variance,
so the stock ledger stays the single source of truth for on-hand quantity.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentStockCount(models.Model):
    _name = 'garment.stock.count'
    _description = 'Garment Stock Count (Cycle Count / Physical Inventory)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'count_date desc'

    name = fields.Char(string='Count Reference', copy=False, readonly=True, default=lambda s: _('New'))
    count_type = fields.Selection([
        ('daily', 'Daily Count'), ('weekly', 'Weekly Count'), ('monthly', 'Monthly Count'),
        ('cycle', 'Cycle Count'), ('random', 'Random Count'), ('annual', 'Annual Stock Audit'),
    ], string='Count Type', default='cycle', required=True, tracking=True)
    warehouse_id = fields.Many2one('garment.warehouse', string='Warehouse', required=True, tracking=True)
    location_id = fields.Many2one('garment.location', string='Location',
                                   domain="[('warehouse_id', '=', warehouse_id)]")
    count_date = fields.Date(string='Count Date', default=fields.Date.context_today, required=True)
    responsible_id = fields.Many2one('res.users', string='Counted By', default=lambda s: s.env.user)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)

    state = fields.Selection([
        ('draft', 'Draft'), ('in_progress', 'In Progress'), ('submitted', 'Submitted for Approval'),
        ('approved', 'Approved (Adjustments Posted)'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many('garment.stock.count.line', 'count_id', string='Count Lines')
    line_count = fields.Integer(string='Lines', compute='_compute_stats', store=True)
    variance_line_count = fields.Integer(string='Lines With Variance', compute='_compute_stats', store=True)
    total_variance_qty = fields.Float(string='Total Absolute Variance', compute='_compute_stats', store=True)
    accuracy_percent = fields.Float(string='Count Accuracy %', compute='_compute_stats', store=True)
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_ids.system_qty', 'line_ids.counted_qty', 'line_ids.variance_qty')
    def _compute_stats(self):
        for rec in self:
            lines = rec.line_ids
            rec.line_count = len(lines)
            rec.variance_line_count = len(lines.filtered(lambda l: l.variance_qty))
            rec.total_variance_qty = sum(abs(l.variance_qty) for l in lines)
            total_system = sum(abs(l.system_qty) for l in lines)
            if total_system:
                rec.accuracy_percent = max(0.0, 100.0 - (rec.total_variance_qty / total_system * 100.0))
            else:
                rec.accuracy_percent = 100.0 if lines else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.stock.count') or _('New')
        return super().create(vals_list)

    def action_start(self):
        """Snapshots the current stock-ledger quantity onto every line so
        the physical count can be compared against it (Cycle Counting)."""
        for rec in self:
            for line in rec.line_ids:
                line.system_qty = line._get_system_qty()
            rec.state = 'in_progress'

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_('Add at least one count line before submitting.'))
        self.write({'state': 'submitted'})

    def action_approve(self):
        """Manager approval posts one adjustment stock move per variance
        line (SRS "Inventory Adjustment": Manager Approval -> Stock Update
        -> Audit Record)."""
        if not self.env.user.has_group('garment_warehouse.group_warehouse_manager'):
            raise UserError(_('Only a Warehouse Manager can approve a stock count.'))
        Move = self.env['garment.stock.move']
        for rec in self:
            for line in rec.line_ids.filtered(lambda l: l.variance_qty):
                move_type = 'adjustment_in' if line.variance_qty > 0 else 'adjustment_out'
                Move.with_context(skip_adjustment_approval=True).create({
                    'material_id': line.material_id.id,
                    'warehouse_id': rec.warehouse_id.id,
                    'location_id': (line.location_id or rec.location_id).id,
                    'move_type': move_type,
                    'quantity': abs(line.variance_qty),
                    'move_date': fields.Date.context_today(rec),
                    'reference': rec.name,
                    'adjustment_reason': 'counting_error',
                    'state': 'done',
                    'approved_by_id': self.env.user.id,
                })
            rec.write({'state': 'approved', 'approved_by_id': self.env.user.id})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
