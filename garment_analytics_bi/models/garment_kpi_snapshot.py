# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
KPI Value / Data Warehouse Fact (SRS sections 40, 48) — garment.kpi.snapshot.

Each record is one closed-period, read_group-computed data point for a
garment.kpi.definition, created by that model's ``_generate_snapshot`` —
either from the daily ir.cron (data/ir_cron_data.xml) or the "Compute Now"
button on the KPI Definition form. This is the module's data-warehouse fact
table: small, append-only, and cheap to chart/pivot/group over in the
standard Odoo graph and pivot views (SRS section 33 - Data Visualization
Engine: Bar/Line/Pie all come for free from the Odoo graph widget on this
model, no custom JS).
"""
from odoo import api, fields, models


class GarmentKpiSnapshot(models.Model):
    _name = 'garment.kpi.snapshot'
    _description = 'Garment KPI Snapshot'
    _order = 'period_date desc, id desc'
    _rec_name = 'kpi_id'

    kpi_id = fields.Many2one('garment.kpi.definition', string='KPI', required=True, ondelete='cascade',
                              index=True)
    category = fields.Selection(related='kpi_id.category', string='Category', store=True)
    department_id = fields.Many2one(related='kpi_id.department_id', string='Department', store=True)
    unit = fields.Char(related='kpi_id.unit', string='Unit')

    period_date = fields.Date(string='Period', required=True, default=fields.Date.context_today, index=True)
    period_type = fields.Selection([
        ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly'),
    ], string='Period Type', required=True, default='daily')
    date_from = fields.Date(string='Period Start')
    date_to = fields.Date(string='Period End')

    group_label = fields.Char(string='Group', help='Group-by dimension label, e.g. a Buyer or Line name, '
                                                     'when the KPI Definition has a Group By Field set.')
    group_res_id = fields.Integer(string='Group Record ID')

    computed_value = fields.Float(string='Computed Value', required=True)
    record_count = fields.Integer(string='Source Record Count')
    target_value = fields.Float(string='Target Value (at snapshot time)')
    variance = fields.Float(string='Variance', compute='_compute_variance', store=True)
    variance_pct = fields.Float(string='Variance (%)', compute='_compute_variance', store=True)

    status = fields.Selection([
        ('on_target', 'On Target'), ('warning', 'Warning'), ('critical', 'Critical'),
    ], string='Status', compute='_compute_variance', store=True)

    computation_datetime = fields.Datetime(string='Computed On', default=fields.Datetime.now, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('computed_value', 'target_value', 'kpi_id.higher_is_better',
                 'kpi_id.warning_threshold_pct', 'kpi_id.critical_threshold_pct')
    def _compute_variance(self):
        for rec in self:
            rec.variance = rec.computed_value - rec.target_value
            rec.variance_pct = (rec.variance / rec.target_value * 100.0) if rec.target_value else 0.0

            kpi = rec.kpi_id
            if not kpi or not rec.target_value:
                rec.status = 'on_target'
                continue
            pct_of_target = (rec.computed_value / rec.target_value * 100.0)
            warning_pct = kpi.warning_threshold_pct or 90.0
            critical_pct = kpi.critical_threshold_pct or 75.0
            if kpi.higher_is_better:
                if pct_of_target >= warning_pct:
                    rec.status = 'on_target'
                elif pct_of_target >= critical_pct:
                    rec.status = 'warning'
                else:
                    rec.status = 'critical'
            else:
                # Lower is better (e.g. Downtime, Defect Rate): thresholds represent
                # how far ABOVE target is still tolerated before Warning/Critical.
                over_pct = 200.0 - pct_of_target if pct_of_target else 100.0
                if over_pct >= warning_pct:
                    rec.status = 'on_target'
                elif over_pct >= critical_pct:
                    rec.status = 'warning'
                else:
                    rec.status = 'critical'

    def action_view_kpi(self):
        self.ensure_one()
        return {
            'name': self.kpi_id.name, 'type': 'ir.actions.act_window', 'res_model': 'garment.kpi.definition',
            'view_mode': 'form', 'res_id': self.kpi_id.id,
        }
