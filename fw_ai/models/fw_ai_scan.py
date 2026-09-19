# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
"""
Rule-based risk detection.

Every _run_* method below implements one explicit, readable business rule.
There is no statistical model and no training data involved - each alert
can be traced directly back to the rule that produced it. This is an
intentional design choice: see the module manifest description.
"""
from datetime import timedelta

from odoo import api, fields, models


class FwAiScan(models.Model):
    _name = 'fw.ai.scan'
    _description = 'Footwear Risk Detection Scan Run'
    _inherit = ['mail.thread']
    _order = 'scan_datetime desc'

    name = fields.Char(string='Scan Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.ai.scan') or 'New')
    scan_datetime = fields.Datetime(string='Scan Run On', default=fields.Datetime.now,
                                     readonly=True)
    alert_ids = fields.One2many('fw.risk.alert', 'scan_id', string='Alerts Raised')
    alert_count = fields.Integer(string='Alerts Raised', compute='_compute_alert_count')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.ai.scan') or 'New'
        return super().create(vals_list)

    def _compute_alert_count(self):
        for rec in self:
            rec.alert_count = len(rec.alert_ids)

    def action_run_scan(self):
        for rec in self:
            alerts = []
            alerts += rec._run_order_delay_rule()
            alerts += rec._run_machine_breakdown_rule()
            alerts += rec._run_supplier_quality_rule()
            alerts += rec._run_spare_stock_rule()
            for vals in alerts:
                vals['scan_id'] = rec.id
            self.env['fw.risk.alert'].create(alerts)
            rec.write({'state': 'completed'})

    # ------------------------------------------------------------------
    # Rule 1: Order Delay Risk
    # An order is flagged if it has one or more TNA milestones that are
    # either explicitly marked 'delayed', or are still not done and their
    # planned date has already passed. Severity scales with how many
    # milestones are late.
    # ------------------------------------------------------------------
    def _run_order_delay_rule(self):
        today = fields.Date.context_today(self)
        orders = self.env['fw.buyer.order'].search([
            ('state', 'not in', ('draft', 'closed', 'cancelled')),
        ])
        vals_list = []
        for order in orders:
            late_lines = order.tna_line_ids.filtered(
                lambda t: t.status == 'delayed'
                or (t.status != 'done' and t.planned_date and t.planned_date < today))
            if not late_lines:
                continue
            severity = 'high' if len(late_lines) >= 3 else (
                'medium' if len(late_lines) >= 1 else 'low')
            milestone_names = ', '.join(late_lines.mapped('milestone'))
            vals_list.append({
                'risk_type': 'order_delay',
                'severity': severity,
                'buyer_order_id': order.id,
                'description': (
                    "Order %s has %d TNA milestone(s) that are late or overdue: %s. "
                    "Required Ship Date: %s."
                ) % (order.name, len(late_lines), milestone_names,
                     order.ship_date or 'not set'),
            })
        return vals_list

    # ------------------------------------------------------------------
    # Rule 2: Machine Reliability Risk
    # A machine is flagged if it has 3 or more breakdown records in the
    # trailing 90 days (repeated failure pattern), or if it currently has
    # any breakdown that is not yet resolved/closed.
    # ------------------------------------------------------------------
    def _run_machine_breakdown_rule(self):
        cutoff = fields.Datetime.now() - timedelta(days=90)
        machines = self.env['fw.machine'].search([('active', '=', True)])
        vals_list = []
        for machine in machines:
            recent_breakdowns = machine.breakdown_ids.filtered(
                lambda b: b.reported_date and b.reported_date >= cutoff)
            open_breakdowns = machine.breakdown_ids.filtered(
                lambda b: b.state not in ('resolved', 'closed'))
            if len(recent_breakdowns) >= 3:
                vals_list.append({
                    'risk_type': 'machine_breakdown',
                    'severity': 'high',
                    'machine_id': machine.id,
                    'description': (
                        "Machine %s has had %d breakdowns in the last 90 days - a repeated "
                        "failure pattern. Consider a preventive maintenance review."
                    ) % (machine.name, len(recent_breakdowns)),
                })
            elif open_breakdowns:
                vals_list.append({
                    'risk_type': 'machine_breakdown',
                    'severity': 'medium',
                    'machine_id': machine.id,
                    'description': (
                        "Machine %s currently has %d unresolved breakdown(s)."
                    ) % (machine.name, len(open_breakdowns)),
                })
        return vals_list

    # ------------------------------------------------------------------
    # Rule 3: Supplier Quality Risk
    # A supplier is flagged if their most recent CONFIRMED scorecard has
    # grade C or D.
    # ------------------------------------------------------------------
    def _run_supplier_quality_rule(self):
        scorecards = self.env['fw.supplier.scorecard'].search([
            ('state', '=', 'confirmed'),
        ], order='supplier_id, period_end desc')
        seen_suppliers = set()
        vals_list = []
        for sc in scorecards:
            if sc.supplier_id.id in seen_suppliers:
                continue
            seen_suppliers.add(sc.supplier_id.id)
            if sc.grade in ('c', 'd'):
                severity = 'high' if sc.grade == 'd' else 'medium'
                vals_list.append({
                    'risk_type': 'supplier_quality',
                    'severity': severity,
                    'supplier_id': sc.supplier_id.id,
                    'description': (
                        "Supplier %s's latest scorecard (%s, period %s to %s) is grade %s "
                        "(Quality %.1f%%, Delivery %.1f%%, Overall %.1f%%)."
                    ) % (sc.supplier_id.name, sc.name, sc.period_start, sc.period_end,
                         sc.grade.upper(), sc.quality_score, sc.delivery_score,
                         sc.overall_score),
                })
        return vals_list

    # ------------------------------------------------------------------
    # Rule 4: Spare Stock Risk
    # A spare part is flagged if current stock is below its reorder
    # level. Suggested reorder quantity is a simple buffer rule:
    # (2 x reorder level) - current stock. This is NOT a demand forecast,
    # just a "restore a safety buffer" heuristic.
    # ------------------------------------------------------------------
    def _run_spare_stock_rule(self):
        spares = self.env['fw.spare.part'].search([('active', '=', True)])
        vals_list = []
        for spare in spares:
            if not spare.below_reorder:
                continue
            suggested_qty = max((2 * spare.min_stock_level) - spare.current_stock, 0)
            ratio = (spare.current_stock / spare.min_stock_level) \
                if spare.min_stock_level else 0.0
            severity = 'high' if ratio < 0.5 else 'medium'
            vals_list.append({
                'risk_type': 'spare_stock',
                'severity': severity,
                'spare_part_id': spare.id,
                'description': (
                    "Spare part %s is below reorder level (Current: %.2f, Reorder Level: "
                    "%.2f). Suggested reorder quantity to restore a safety buffer: %.2f "
                    "%s."
                ) % (spare.name, spare.current_stock, spare.min_stock_level, suggested_qty,
                     spare.uom_id.name if spare.uom_id else 'units'),
            })
        return vals_list
