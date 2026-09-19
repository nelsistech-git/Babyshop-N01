# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError


class FwKpiSnapshot(models.Model):
    _name = 'fw.kpi.snapshot'
    _description = 'Footwear Factory KPI Snapshot'
    _inherit = ['mail.thread']
    _order = 'period_end desc'

    name = fields.Char(string='Snapshot Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.kpi.snapshot') or 'New')
    factory_id = fields.Many2one('fw.factory', string='Factory', required=True, tracking=True)
    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)
    snapshot_date = fields.Date(string='Generated On', default=fields.Date.context_today,
                                 readonly=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    # Production
    total_production_qty = fields.Integer(string='Total Production Qty (Pairs)', readonly=True)
    total_orders_count = fields.Integer(string='Buyer Orders in Period', readonly=True)

    # Quality
    avg_dhu_percent = fields.Float(string='Avg. Inline DHU %', readonly=True)
    aql_pass_rate_percent = fields.Float(string='AQL Pass Rate %', readonly=True,
                                          help="Only counts AQL Inspections linked to a "
                                               "Production Order for this factory. "
                                               "Standalone shipment-level inspections without "
                                               "that link are not included.")

    # Industrial Engineering
    avg_line_efficiency_percent = fields.Float(string='Avg. Line Efficiency %', readonly=True)

    # Maintenance
    breakdown_count = fields.Integer(string='Breakdown Count', readonly=True)
    total_downtime_hours = fields.Float(string='Total Downtime (Hours)', readonly=True)

    # Finance
    total_sales_value = fields.Monetary(string='Total Sales Value (Confirmed Orders)',
                                         currency_field='currency_id', readonly=True)
    cost_per_pair = fields.Monetary(string='Cost per Pair (from Factory Costing)',
                                     currency_field='currency_id', readonly=True,
                                     help="Pulled from a matching FW Factory Costing record "
                                          "for the same factory and period, if one exists.")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.kpi.snapshot') or 'New'
        return super().create(vals_list)

    def action_generate_snapshot(self):
        for rec in self:
            if not rec.period_start or not rec.period_end:
                raise UserError("Please set both Period Start and Period End first.")
            if rec.period_start > rec.period_end:
                raise UserError("Period Start cannot be after Period End.")

            factory = rec.factory_id
            p_start, p_end = rec.period_start, rec.period_end

            # --- Production ---
            production_orders = self.env['fw.production.order'].search([
                ('factory_id', '=', factory.id),
                ('state', '=', 'completed'),
                ('date_planned_finish', '>=', p_start),
                ('date_planned_finish', '<=', p_end),
            ])
            total_production_qty = sum(production_orders.mapped('finished_qty'))

            buyer_orders = self.env['fw.buyer.order'].search([
                ('factory_id', '=', factory.id),
                ('order_date', '>=', p_start),
                ('order_date', '<=', p_end),
            ])
            confirmed_orders = buyer_orders.filtered(
                lambda o: o.state not in ('draft', 'cancelled'))

            # --- Quality ---
            inline_qc = self.env['fw.inline.qc'].search([
                ('production_order_id.factory_id', '=', factory.id),
                ('date', '>=', p_start),
                ('date', '<=', p_end),
                ('state', '=', 'done'),
            ])
            avg_dhu = (sum(inline_qc.mapped('dhu_percent')) / len(inline_qc)) \
                if inline_qc else 0.0

            aql_inspections = self.env['fw.aql.inspection'].search([
                ('production_order_id.factory_id', '=', factory.id),
                ('date', '>=', p_start),
                ('date', '<=', p_end),
                ('state', '=', 'completed'),
            ])
            aql_pass_rate = 0.0
            if aql_inspections:
                pass_count = len(aql_inspections.filtered(lambda a: a.result == 'pass'))
                aql_pass_rate = pass_count / len(aql_inspections) * 100.0

            # --- IE / Efficiency ---
            efficiency_reports = self.env['fw.efficiency.report'].search([
                ('factory_id', '=', factory.id),
                ('date', '>=', p_start),
                ('date', '<=', p_end),
            ])
            avg_efficiency = (sum(efficiency_reports.mapped('efficiency_percent'))
                               / len(efficiency_reports)) if efficiency_reports else 0.0

            # --- Maintenance ---
            breakdowns = self.env['fw.breakdown'].search([
                ('factory_id', '=', factory.id),
                ('reported_date', '>=', p_start),
                ('reported_date', '<=', p_end),
            ])

            # --- Finance ---
            factory_costing = self.env['fw.factory.costing'].search([
                ('factory_id', '=', factory.id),
                ('period_start', '=', p_start),
                ('period_end', '=', p_end),
            ], limit=1)

            rec.write({
                'total_production_qty': total_production_qty,
                'total_orders_count': len(buyer_orders),
                'avg_dhu_percent': avg_dhu,
                'aql_pass_rate_percent': aql_pass_rate,
                'avg_line_efficiency_percent': avg_efficiency,
                'breakdown_count': len(breakdowns),
                'total_downtime_hours': sum(breakdowns.mapped('downtime_hours')),
                'total_sales_value': sum(confirmed_orders.mapped('total_amount')),
                'cost_per_pair': factory_costing.cost_per_pair if factory_costing else 0.0,
                'state': 'generated',
            })

    def action_reset_draft(self):
        self.write({'state': 'draft'})
