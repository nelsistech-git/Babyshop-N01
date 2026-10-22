# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentLineBalancing(models.Model):
    """Line Balancing — Industrial Engineering feature to reduce bottleneck
    and balance workload across operations. See Production Management SRS
    s.35, Planning & MES SRS s.24, MES SRS s.16, Shop Floor SRS s.25-26."""
    _name = 'garment.line.balancing'
    _description = 'Garment Line Balancing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    line_id = fields.Many2one('garment.production.line', string='Production Line', required=True)
    production_order_id = fields.Many2one('garment.production.order', string='Production Order')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)

    operation_line_ids = fields.One2many('garment.line.balancing.line', 'balancing_id', string='Operation Load')
    bottleneck_operation = fields.Char(string='Bottleneck Operation', compute='_compute_bottleneck', store=True)
    bottleneck_reason = fields.Char(string='Bottleneck Reason')
    suggestion = fields.Text(string='Suggestion')
    expected_gain_pct = fields.Float(string='Expected Efficiency Gain (%)')

    status = fields.Selection([
        ('draft', 'Draft'), ('analyzed', 'Analyzed'), ('actioned', 'Action Taken'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_name(self):
        for rec in self:
            rec.name = '%s - %s' % (rec.line_id.line_number or '', rec.date or '')

    @api.depends('operation_line_ids.output_qty', 'operation_line_ids.operation_name')
    def _compute_bottleneck(self):
        for rec in self:
            lines = rec.operation_line_ids
            if not lines:
                rec.bottleneck_operation = False
                continue
            lowest = min(lines, key=lambda l: l.output_qty or 0.0)
            rec.bottleneck_operation = lowest.operation_name

    def action_analyze(self):
        self.write({'status': 'analyzed'})


class GarmentLineBalancingLine(models.Model):
    """Per-operation workload row used to detect bottlenecks."""
    _name = 'garment.line.balancing.line'
    _description = 'Garment Line Balancing Operation Load'
    _order = 'sequence'

    balancing_id = fields.Many2one('garment.line.balancing', string='Line Balancing',
                                   required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    operation_name = fields.Char(string='Operation', required=True)
    operator_count = fields.Integer(string='Operators')
    smv = fields.Float(string='SMV (Minutes)', digits=(6, 3))
    target_output = fields.Float(string='Target Output (PCS)')
    output_qty = fields.Float(string='Actual Output (PCS)')
    is_bottleneck = fields.Boolean(string='Is Bottleneck', compute='_compute_bottleneck_flag', store=True)

    @api.depends('output_qty', 'target_output')
    def _compute_bottleneck_flag(self):
        for rec in self:
            rec.is_bottleneck = bool(rec.target_output) and rec.output_qty < rec.target_output * 0.85
