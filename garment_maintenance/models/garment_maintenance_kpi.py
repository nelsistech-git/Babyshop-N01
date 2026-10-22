# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Maintenance KPI snapshot — MTTR, MTBF, Machine Availability, Breakdown
Rate and PM Compliance % (Maintenance & Asset Mgmt SRS sec. 32, 41,
CMMS SRS sec. 33, 40, 44). This is deliberately NOT the same thing as
``garment.production.oee`` (garment_production), which already computes
Availability x Performance x Quality per line/machine/shift for
production efficiency. This model complements it with maintenance
RELIABILITY metrics (MTBF/MTTR/breakdown rate/PM compliance) that OEE
does not carry, computed from this module's own Work Orders and the
downtime records they resolve. See IMPLEMENTATION_NOTES.md.

    MTBF = Total Operating Time / Number of Failures
    MTTR = Total Repair Time / Number of Repairs
    Availability = Available Time / Planned Production Time
"""
from odoo import api, fields, models, _


class GarmentMaintenanceKpi(models.Model):
    _name = 'garment.maintenance.kpi'
    _description = 'Garment Maintenance KPI Snapshot'
    _order = 'period_date desc'

    equipment_type = fields.Selection([
        ('machine', 'Production Machine'),
        ('asset', 'Other Asset'),
    ], string='Equipment Type', default='machine', required=True)
    machine_id = fields.Many2one('garment.production.machine', string='Machine')
    asset_id = fields.Many2one('garment.asset', string='Asset')
    equipment_name = fields.Char(string='Equipment', compute='_compute_equipment_name', store=True)

    period_date = fields.Date(string='Period', default=fields.Date.context_today, required=True)
    planned_hours = fields.Float(string='Planned Production Hours', default=720.0,
                                  help='Planned operating hours for the period (default: 30 days x 24h).')

    breakdown_count = fields.Integer(string='Breakdown Count', compute='_compute_kpis', store=True)
    total_downtime_hours = fields.Float(string='Total Downtime (Hours)', compute='_compute_kpis', store=True)
    total_repair_hours = fields.Float(string='Total Repair Time (Hours)', compute='_compute_kpis', store=True)
    mtbf_hours = fields.Float(string='MTBF (Hours)', compute='_compute_kpis', store=True,
                               help='Mean Time Between Failures = Operating Time / Number of Failures')
    mttr_hours = fields.Float(string='MTTR (Hours)', compute='_compute_kpis', store=True,
                               help='Mean Time To Repair = Total Repair Time / Number of Repairs')
    availability_pct = fields.Float(string='Availability (%)', compute='_compute_kpis', store=True)
    breakdown_rate_pct = fields.Float(string='Breakdown Rate (%)', compute='_compute_kpis', store=True)

    pm_due_count = fields.Integer(string='PM Jobs Due', compute='_compute_pm_compliance', store=True)
    pm_completed_count = fields.Integer(string='PM Jobs Completed', compute='_compute_pm_compliance', store=True)
    pm_compliance_pct = fields.Float(string='PM Compliance (%)', compute='_compute_pm_compliance', store=True)

    maintenance_cost = fields.Monetary(string='Maintenance Cost', compute='_compute_kpis', store=True,
                                        currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('machine_id.name', 'machine_id.machine_number', 'asset_id.name', 'asset_id.asset_code')
    def _compute_equipment_name(self):
        for rec in self:
            if rec.equipment_type == 'machine' and rec.machine_id:
                rec.equipment_name = rec.machine_id.name or rec.machine_id.machine_number
            elif rec.equipment_type == 'asset' and rec.asset_id:
                rec.equipment_name = '%s [%s]' % (rec.asset_id.name, rec.asset_id.asset_code)
            else:
                rec.equipment_name = False

    def _get_period_workorders(self, wo_type=None):
        self.ensure_one()
        Workorder = self.env['garment.maintenance.workorder']
        domain = [('state', 'in', ('completed', 'closed'))]
        if wo_type:
            domain.append(('wo_type', '=', wo_type))
        if self.equipment_type == 'machine' and self.machine_id:
            domain.append(('machine_id', '=', self.machine_id.id))
        elif self.equipment_type == 'asset' and self.asset_id:
            domain.append(('asset_id', '=', self.asset_id.id))
        else:
            return Workorder
        month_start = self.period_date.replace(day=1)
        domain += [('reported_date', '>=', month_start)]
        return Workorder.search(domain)

    @api.depends('machine_id', 'asset_id', 'equipment_type', 'period_date', 'planned_hours')
    def _compute_kpis(self):
        for rec in self:
            breakdowns = rec._get_period_workorders(wo_type='breakdown')
            all_workorders = rec._get_period_workorders()
            rec.breakdown_count = len(breakdowns)
            rec.total_downtime_hours = sum(breakdowns.mapped('downtime_hours'))
            rec.total_repair_hours = rec.total_downtime_hours
            rec.mtbf_hours = (rec.planned_hours / rec.breakdown_count) if rec.breakdown_count else rec.planned_hours
            rec.mttr_hours = (rec.total_repair_hours / rec.breakdown_count) if rec.breakdown_count else 0.0
            available_hours = max(rec.planned_hours - rec.total_downtime_hours, 0.0)
            rec.availability_pct = (available_hours / rec.planned_hours * 100.0) if rec.planned_hours else 0.0
            rec.breakdown_rate_pct = (rec.breakdown_count / (rec.planned_hours / 24.0) * 100.0) \
                if rec.planned_hours else 0.0
            rec.maintenance_cost = sum(all_workorders.mapped('total_cost'))

    @api.depends('machine_id', 'asset_id', 'equipment_type', 'period_date')
    def _compute_pm_compliance(self):
        Plan = self.env['garment.maintenance.plan']
        for rec in self:
            domain = [('maintenance_type', '!=', False)]
            if rec.equipment_type == 'machine' and rec.machine_id:
                domain.append(('machine_id', '=', rec.machine_id.id))
            elif rec.equipment_type == 'asset' and rec.asset_id:
                domain.append(('asset_id', '=', rec.asset_id.id))
            else:
                rec.pm_due_count = rec.pm_completed_count = 0
                rec.pm_compliance_pct = 0.0
                continue
            plans = Plan.search(domain)
            due_plans = plans.filtered(lambda p: p.next_due_date and p.next_due_date <= rec.period_date)
            rec.pm_due_count = len(due_plans)
            completed = due_plans.filtered(
                lambda p: p.last_done_date and p.last_done_date <= rec.period_date)
            rec.pm_completed_count = len(completed)
            rec.pm_compliance_pct = (len(completed) / len(due_plans) * 100.0) if due_plans else 100.0

    def action_recompute(self):
        self._compute_kpis()
        self._compute_pm_compliance()
