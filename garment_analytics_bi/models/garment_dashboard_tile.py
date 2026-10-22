# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
BI Dashboard Tile — garment.dashboard.tile.

Each tile is either bound to a saved garment.kpi.definition (its value is
the latest garment.kpi.snapshot for that KPI — cheap, and consistent with
whatever the scheduled job last computed) or defined as its own raw
model/domain/measure ("custom" tile), computed live on display through the
exact same ``garment.kpi.definition._compute_measure`` read_group helper a
KPI Definition uses, over a rolling date window (Today / This Week / This
Month / This Year / All Time).
"""
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

from .garment_kpi_definition import AGGREGATION_SELECTION, SOURCE_MODEL_SELECTION

DATE_RANGE_SELECTION = [
    ('today', 'Today'),
    ('this_week', 'This Week'),
    ('this_month', 'This Month'),
    ('this_year', 'This Year'),
    ('all', 'All Time'),
]


class GarmentDashboardTile(models.Model):
    _name = 'garment.dashboard.tile'
    _description = 'Garment BI Dashboard Tile'
    _order = 'sequence, id'

    board_id = fields.Many2one('garment.dashboard.board', string='Dashboard', required=True,
                                ondelete='cascade', index=True)
    name = fields.Char(string='Tile Title', required=True)
    sequence = fields.Integer(default=10)
    size = fields.Selection([
        ('small', 'Small'), ('medium', 'Medium'), ('large', 'Large'),
    ], string='Tile Size', default='medium')
    color = fields.Integer(string='Color Index', default=0, help='Odoo kanban color index (0-11).')
    icon = fields.Char(string='Icon', default='fa-bar-chart',
                        help='Font Awesome class, e.g. "fa-industry", "fa-money".')

    tile_type = fields.Selection([
        ('kpi', 'Linked KPI'),
        ('custom', 'Custom Domain Measure'),
    ], string='Tile Type', required=True, default='kpi')

    # -- Linked KPI tile -------------------------------------------------
    kpi_id = fields.Many2one('garment.kpi.definition', string='KPI',
                              domain=[('active', '=', True)])

    # -- Custom tile -------------------------------------------------
    source_model = fields.Selection(SOURCE_MODEL_SELECTION, string='Source Model')
    measure_field = fields.Char(string='Measure Field')
    aggregation = fields.Selection(AGGREGATION_SELECTION, string='Aggregation', default='sum')
    domain_filter = fields.Char(string='Extra Domain (optional)')
    date_field = fields.Char(string='Date Field (optional)')
    date_range = fields.Selection(DATE_RANGE_SELECTION, string='Date Range', default='this_month')
    custom_target_value = fields.Float(string='Target Value')
    custom_unit = fields.Char(string='Unit')
    higher_is_better = fields.Boolean(string='Higher Is Better', default=True)
    warning_threshold_pct = fields.Float(string='Warning Threshold (%)', default=90.0)
    critical_threshold_pct = fields.Float(string='Critical Threshold (%)', default=75.0)

    # -- Display value (computed on read, not stored — always "live") ----
    current_value = fields.Float(string='Current Value', compute='_compute_current_value')
    target_value = fields.Float(string='Target Value', compute='_compute_current_value')
    unit = fields.Char(string='Unit', compute='_compute_current_value')
    status = fields.Selection([
        ('on_target', 'On Target'), ('warning', 'Warning'), ('critical', 'Critical'), ('no_data', 'No Data'),
    ], string='Status', compute='_compute_current_value')
    as_of = fields.Char(string='As Of', compute='_compute_current_value',
                         help='Human label of what period the current value reflects.')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _get_date_window(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.date_range == 'today':
            return today, today, 'Today'
        if self.date_range == 'this_week':
            return today - relativedelta(days=today.weekday()), today, 'This Week'
        if self.date_range == 'this_month':
            return today.replace(day=1), today, 'This Month'
        if self.date_range == 'this_year':
            return today.replace(month=1, day=1), today, 'This Year'
        return False, False, 'All Time'

    @api.depends('tile_type', 'kpi_id.last_value', 'kpi_id.last_status', 'kpi_id.target_value', 'kpi_id.unit',
                 'source_model', 'measure_field', 'aggregation', 'domain_filter', 'date_field', 'date_range',
                 'custom_target_value', 'custom_unit', 'higher_is_better', 'warning_threshold_pct',
                 'critical_threshold_pct')
    def _compute_current_value(self):
        Kpi = self.env['garment.kpi.definition']
        for rec in self:
            if rec.tile_type == 'kpi' and rec.kpi_id:
                kpi = rec.kpi_id
                rec.current_value = kpi.last_value
                rec.target_value = kpi.target_value
                rec.unit = kpi.unit
                rec.status = kpi.last_status
                rec.as_of = kpi.last_snapshot_id.period_date and str(kpi.last_snapshot_id.period_date) or 'No Data'
                continue

            if rec.tile_type == 'custom' and rec.source_model and rec.measure_field:
                date_from, date_to, label = rec._get_date_window()
                rows = Kpi._compute_measure(
                    rec.source_model, rec.measure_field, rec.aggregation, group_by_field=None,
                    date_field=rec.date_field, domain_filter=rec.domain_filter,
                    date_from=date_from, date_to=date_to)
                value = rows[0]['value'] if rows else 0.0
                rec.current_value = value
                rec.target_value = rec.custom_target_value
                rec.unit = rec.custom_unit
                rec.as_of = label
                if not rec.custom_target_value:
                    rec.status = 'on_target'
                else:
                    pct = value / rec.custom_target_value * 100.0
                    warning_pct = rec.warning_threshold_pct or 90.0
                    critical_pct = rec.critical_threshold_pct or 75.0
                    if rec.higher_is_better:
                        rec.status = 'on_target' if pct >= warning_pct else (
                            'warning' if pct >= critical_pct else 'critical')
                    else:
                        over_pct = 200.0 - pct if pct else 100.0
                        rec.status = 'on_target' if over_pct >= warning_pct else (
                            'warning' if over_pct >= critical_pct else 'critical')
                continue

            rec.current_value = 0.0
            rec.target_value = 0.0
            rec.unit = False
            rec.status = 'no_data'
            rec.as_of = 'No Data'

    @api.onchange('tile_type')
    def _onchange_tile_type(self):
        if self.tile_type == 'kpi':
            self.source_model = False
            self.measure_field = False
        else:
            self.kpi_id = False

    @api.onchange('kpi_id')
    def _onchange_kpi_id(self):
        if self.kpi_id and not self.name:
            self.name = self.kpi_id.name
