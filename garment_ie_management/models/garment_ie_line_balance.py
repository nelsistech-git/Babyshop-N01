# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Line Balancing Management System (SRS s.21-25) — the IE engineering study
that distributes operations across operators to balance workload, detect
bottlenecks and recommend a fix, before a line is set up.

Note: ``garment_production`` already carries a lighter execution-time
``garment.line.balancing`` record (per-line/date bottleneck snapshot from
shop-floor output). This model is the upstream IE *study* — it works from
SMV and operator skill (not yet-collected shop floor output), assigns named
operators per operation, and drives the final line setup; it does not
replace the production-side execution record.
"""
from odoo import api, fields, models, _


class GarmentIeLineBalance(models.Model):
    _name = 'garment.ie.line.balance'
    _description = 'Garment IE Line Balancing Study'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'
    _rec_name = 'balance_number'

    balance_number = fields.Char(string='Study Reference', copy=False, readonly=True, default=lambda s: _('New'))
    line_id = fields.Many2one('garment.production.line', string='Production Line', required=True, tracking=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    production_order_id = fields.Many2one('garment.production.order', string='Production Order')
    routing_id = fields.Many2one('garment.operation.routing', string='Operation Routing')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)

    target_qty = fields.Float(string='Target Quantity (PCS/Day)', required=True)
    working_hours = fields.Float(string='Working Hours', default=8.0)
    efficiency_target = fields.Float(string='Efficiency Target (%)', default=70.0)

    allocation_line_ids = fields.One2many('garment.ie.line.balance.line', 'balance_id', string='Operation Allocation')
    total_operators = fields.Integer(string='Total Operators', compute='_compute_totals', store=True)
    required_smv = fields.Float(string='Required SMV', digits=(6, 3), compute='_compute_totals', store=True)
    line_capacity_per_hour = fields.Float(string='Line Capacity (PCS/Hour)', compute='_compute_totals', store=True,
                                           help='Capacity of the slowest (bottleneck) operation, which caps '
                                                'the whole line output.')
    estimated_output_per_day = fields.Float(string='Estimated Output (PCS/Day)', compute='_compute_totals',
                                             store=True)
    projected_efficiency_pct = fields.Float(string='Projected Efficiency (%)', compute='_compute_totals', store=True)

    bottleneck_line_id = fields.Many2one('garment.ie.line.balance.line', string='Bottleneck Operation',
                                          compute='_compute_totals', store=True)
    ai_recommendation = fields.Text(string='Recommendation')
    expected_improvement_pct = fields.Float(string='Expected Improvement (%)')

    status = fields.Selection([
        ('draft', 'Draft'), ('analyzing', 'Analyzing'),
        ('simulated', 'Simulated'), ('confirmed', 'Final Line Setup'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('allocation_line_ids.allocated_operators', 'allocation_line_ids.smv',
                 'allocation_line_ids.capacity_per_hour', 'working_hours', 'target_qty')
    def _compute_totals(self):
        for rec in self:
            lines = rec.allocation_line_ids
            rec.total_operators = int(sum(lines.mapped('allocated_operators')))
            rec.required_smv = sum(lines.mapped('smv'))
            if lines:
                bottleneck = min(lines, key=lambda l: l.capacity_per_hour or 0.0)
                rec.bottleneck_line_id = bottleneck.id
                rec.line_capacity_per_hour = bottleneck.capacity_per_hour
            else:
                rec.bottleneck_line_id = False
                rec.line_capacity_per_hour = 0.0
            rec.estimated_output_per_day = rec.line_capacity_per_hour * rec.working_hours
            rec.projected_efficiency_pct = (rec.estimated_output_per_day / rec.target_qty * 100.0
                                             if rec.target_qty else 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('balance_number', _('New')) == _('New'):
                vals['balance_number'] = self.env['ir.sequence'].next_by_code('garment.ie.line.balance') or _('New')
        return super().create(vals_list)

    def action_analyze(self):
        self.write({'status': 'analyzing'})

    def action_simulate(self):
        self.write({'status': 'simulated'})

    def action_confirm(self):
        self.write({'status': 'confirmed'})


class GarmentIeLineBalanceLine(models.Model):
    """Operation Allocation line (SRS s.23-25): one operation, its assigned
    operator(s), SMV, required vs. actual capacity and bottleneck flag."""
    _name = 'garment.ie.line.balance.line'
    _description = 'Garment IE Line Balancing Operation Allocation'
    _order = 'balance_id, sequence'

    balance_id = fields.Many2one('garment.ie.line.balance', string='Line Balancing Study', required=True,
                                  ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    operation_id = fields.Many2one('garment.ie.operation', string='Operation', required=True)
    routing_line_id = fields.Many2one('garment.operation.routing.line', string='Routing Operation Reference')
    operator_id = fields.Many2one('garment.hr.employee', string='Assigned Operator')
    operator_efficiency_pct = fields.Float(string="Operator's Efficiency on Operation (%)",
                                            compute='_compute_operator_efficiency')
    smv = fields.Float(string='SMV (Minutes)', digits=(6, 3), required=True)
    allocated_operators = fields.Integer(string='Operators Allocated', default=1)
    required_output_per_hour = fields.Float(string='Required Output (PCS/Hour)')
    capacity_per_hour = fields.Float(string='Capacity (PCS/Hour)', compute='_compute_capacity', store=True)
    is_bottleneck = fields.Boolean(string='Is Bottleneck', compute='_compute_capacity', store=True)
    recommendation = fields.Selection([
        ('add_operator', 'Add Operator'),
        ('change_sequence', 'Change Operation Sequence'),
        ('skilled_operator', 'Use Skilled Operator'),
        ('improve_method', 'Improve Method'),
        ('change_machine', 'Change Machine'),
    ], string='Recommended Action')

    @api.depends('operator_id', 'operation_id')
    def _compute_operator_efficiency(self):
        SkillLine = self.env['garment.ie.skill.matrix.line']
        for rec in self:
            eff = 0.0
            if rec.operator_id and rec.operation_id:
                skill_line = SkillLine.search([
                    ('matrix_id.employee_id', '=', rec.operator_id.id),
                    ('operation_id', '=', rec.operation_id.id),
                ], limit=1)
                eff = skill_line.efficiency_pct if skill_line else 0.0
            rec.operator_efficiency_pct = eff

    @api.depends('smv', 'allocated_operators', 'required_output_per_hour')
    def _compute_capacity(self):
        for rec in self:
            rec.capacity_per_hour = (60.0 / rec.smv) * rec.allocated_operators if rec.smv else 0.0
            rec.is_bottleneck = bool(rec.required_output_per_hour) and rec.capacity_per_hour < rec.required_output_per_hour
