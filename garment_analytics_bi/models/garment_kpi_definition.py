# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
KPI Management Framework (SRS sections 21-25, 40-41) — garment.kpi.definition.

A KPI Definition never stores business data of its own: it names a real
target model + measure field already owned by another module (see
MODEL_MAP.md / __manifest__.py 'depends').
"""
import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

SOURCE_MODEL_SELECTION = [
    ('garment.order', 'Order Management: Orders (garment.order)'),
    ('garment.order.shipment', 'Order Management: Shipments (garment.order.shipment)'),
    ('garment.production.entry', 'Production: Production Entries (garment.production.entry)'),
    ('garment.production.oee', 'Production: OEE Records (garment.production.oee)'),
    ('garment.machine.downtime', 'Production: Machine Downtime (garment.machine.downtime)'),
    ('garment.quality.inspection', 'Quality: Inspections (garment.quality.inspection)'),
    ('garment.quality.defect', 'Quality: Defects (garment.quality.defect)'),
    ('garment.costing', 'Costing: Cost Sheets (garment.costing)'),
    ('garment.expense', 'Finance: Expenses (garment.expense)'),
    ('garment.receivable', 'Finance: Buyer Receivables (garment.receivable)'),
    ('garment.hr.attendance', 'HR: Attendance (garment.hr.attendance)'),
]

AGGREGATION_SELECTION = [
    ('sum', 'Sum'),
    ('avg', 'Average'),
    ('count', 'Count of Records'),
    ('min', 'Minimum'),
    ('max', 'Maximum'),
]

FREQUENCY_SELECTION = [
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly'),
]

CATEGORY_SELECTION = [
    ('executive', 'Executive'),
    ('production', 'Production'),
    ('quality', 'Quality'),
    ('inventory', 'Inventory'),
    ('finance', 'Finance'),
    ('sales', 'Sales / Orders'),
    ('hr', 'HR'),
]


class GarmentKpiDefinition(models.Model):
    """KPI Definition (SRS section 41) — garment.kpi.definition."""
    _name = 'garment.kpi.definition'
    _description = 'Garment KPI Definition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'category, name'
    _rec_name = 'name'

    name = fields.Char(string='KPI Name', required=True, tracking=True)
    category = fields.Selection(CATEGORY_SELECTION, string='Category', required=True, default='production',
                                tracking=True)
    department_id = fields.Many2one('garment.hr.department', string='Department')
    description = fields.Text(string='Description')

    source_model = fields.Selection(SOURCE_MODEL_SELECTION, string='Source Model', required=True,
                                    help='The real operational model this KPI is aggregated from.')
    measure_field = fields.Char(string='Measure Field', required=True,
                                help='Technical field name on the Source Model to aggregate.')
    aggregation = fields.Selection(AGGREGATION_SELECTION, string='Aggregation', required=True, default='sum')
    group_by_field = fields.Char(string='Group By Field (optional)',
                                 help='Technical field name to group the read_group by.')
    date_field = fields.Char(string='Date Field (optional)',
                             help='Technical Date/Datetime field used to restrict the aggregation.')
    domain_filter = fields.Char(string='Extra Domain (optional)', help='Optional additional Odoo domain.')

    frequency = fields.Selection(FREQUENCY_SELECTION, string='Frequency', required=True, default='daily', tracking=True)
    target_value = fields.Float(string='Target Value', tracking=True,
                                help='0 means this KPI is monitored without a fixed target.')
    unit = fields.Char(string='Unit', help='Display unit, e.g. "%", "PCS", "BDT".')
    higher_is_better = fields.Boolean(string='Higher Is Better', default=True,
                                      help='Unchecked for KPIs where going above target is bad.')
    warning_threshold_pct = fields.Float(string='Warning Threshold (%)', default=90.0,
                                         help='% of target that still counts as On Target.')
    critical_threshold_pct = fields.Float(string='Critical Threshold (%)', default=75.0,
                                          help='% of target below which the KPI is Critical.')

    responsible_user_id = fields.Many2one('res.users', string='Responsible User', tracking=True,
                                          default=lambda s: s.env.user)

    snapshot_ids = fields.One2many('garment.kpi.snapshot', 'kpi_id', string='Snapshots')

    # FIXED: Added store=True to match last_value and last_status
    snapshot_count = fields.Integer(string='Snapshot Count', compute='_compute_snapshot_stats', store=True)
    last_snapshot_id = fields.Many2one('garment.kpi.snapshot', string='Latest Snapshot',
                                       compute='_compute_snapshot_stats', store=True)

    last_value = fields.Float(string='Latest Value', compute='_compute_snapshot_stats', store=True)
    last_status = fields.Selection([
        ('on_target', 'On Target'), ('warning', 'Warning'), ('critical', 'Critical'), ('no_data', 'No Data'),
    ], string='Latest Status', compute='_compute_snapshot_stats', store=True)

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('kpi_name_uniq', 'unique(name, company_id)', 'A KPI with this name already exists!'),
    ]

    @api.depends('snapshot_ids.computed_value', 'snapshot_ids.period_date', 'snapshot_ids.status')
    def _compute_snapshot_stats(self):
        for rec in self:
            rec.snapshot_count = len(rec.snapshot_ids)
            last = rec.snapshot_ids.filtered(lambda s: not s.group_label)[:1] or rec.snapshot_ids[:1]
            if last:
                rec.last_snapshot_id = last
                rec.last_value = last.computed_value
                rec.last_status = last.status
            else:
                rec.last_snapshot_id = False
                rec.last_value = 0.0
                rec.last_status = 'no_data'

    @api.model
    def _compute_measure(self, source_model, measure_field, aggregation, group_by_field=None, date_field=None,
                         domain_filter=None, date_from=None, date_to=None):
        result = []
        if not source_model or source_model not in self.env:
            _logger.warning('garment_analytics_bi: unknown source model "%s"', source_model)
            return result
        Model = self.env[source_model].sudo()

        domain = []
        if domain_filter:
            try:
                extra = safe_eval(domain_filter) or []
                if isinstance(extra, list):
                    domain += extra
            except Exception:
                _logger.warning('garment_analytics_bi: could not evaluate domain "%s"', domain_filter)
        if date_field and date_from and date_to:
            domain += [(date_field, '>=', date_from), (date_field, '<=', date_to)]

        groupby = [group_by_field] if group_by_field else []
        aggregation = aggregation or 'sum'
        measure_field = measure_field or 'id'

        if aggregation == 'count' or measure_field not in Model._fields:
            fields_arg = []
        else:
            fields_arg = ['%s:%s' % (measure_field, aggregation)]

        try:
            rows = Model.read_group(domain, fields_arg, groupby, lazy=False)
        except Exception:
            _logger.exception('garment_analytics_bi: read_group failed on %s', source_model)
            return result

        if not rows:
            return [{'value': 0.0, 'count': 0, 'group_label': False, 'group_res_id': False}]

        for row in rows:
            count = row.get('__count', 0)
            if aggregation == 'count' or measure_field not in Model._fields:
                value = count
            else:
                value = row.get(measure_field)
                if value is None:
                    value = row.get('%s:%s' % (measure_field, aggregation), 0.0)
                value = value or 0.0

            group_label = False
            group_res_id = False
            if group_by_field:
                raw_group = row.get(group_by_field)
                if isinstance(raw_group, (list, tuple)) and len(raw_group) == 2:
                    group_res_id, group_label = raw_group[0], raw_group[1]
                elif raw_group not in (False, None):
                    group_label = str(raw_group)

            result.append({'value': value, 'count': count, 'group_label': group_label, 'group_res_id': group_res_id})
        return result

    def _run_read_group(self, date_from=None, date_to=None):
        self.ensure_one()
        return self._compute_measure(self.source_model, self.measure_field, self.aggregation, self.group_by_field,
                                     self.date_field, self.domain_filter, date_from, date_to)

    def _is_due(self, on_date):
        self.ensure_one()
        if self.frequency == 'daily': return True
        if self.frequency == 'weekly': return on_date.weekday() == 0
        if self.frequency == 'monthly': return on_date.day == 1
        if self.frequency == 'yearly': return on_date.month == 1 and on_date.day == 1
        return False

    def _get_period_window(self, on_date):
        self.ensure_one()
        date_to = on_date - relativedelta(days=1)
        if self.frequency == 'daily':
            date_from = date_to
        elif self.frequency == 'weekly':
            date_from = date_to - relativedelta(days=6)
        elif self.frequency == 'monthly':
            month_end = on_date - relativedelta(days=1)
            date_from = month_end.replace(day=1)
            date_to = month_end
        elif self.frequency == 'yearly':
            year_end = on_date - relativedelta(days=1)
            date_from = year_end.replace(month=1, day=1)
            date_to = year_end
        else:
            date_from = date_to
        return date_from, date_to

    def _generate_snapshot(self, period_date, date_from=None, date_to=None):
        self.ensure_one()
        Snapshot = self.env['garment.kpi.snapshot']
        rows = self._run_read_group(date_from, date_to)
        created = Snapshot
        for row in rows:
            created |= Snapshot.create({
                'kpi_id': self.id, 'period_date': period_date, 'period_type': self.frequency,
                'date_from': date_from, 'date_to': date_to, 'group_label': row.get('group_label') or False,
                'group_res_id': row.get('group_res_id') or False, 'computed_value': row.get('value', 0.0),
                'record_count': row.get('count', 0), 'target_value': self.target_value,
            })
        breached = created.filtered(lambda s: s.status == 'critical')
        if breached:
            self.message_post(
                body=_('KPI "%s" is Critical for period %s: %s (target %s %s).') % (self.name, period_date,
                                                                                    breached[0].computed_value,
                                                                                    self.target_value, self.unit or ''))
        return created

    def action_compute_now(self):
        today = fields.Date.context_today(self)
        for rec in self:
            date_from, date_to = rec._get_period_window(today)
            rec._generate_snapshot(today, date_from, date_to)
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('KPI Snapshot Computed'), 'type': 'success', 'sticky': False}}

    def action_view_snapshots(self):
        self.ensure_one()
        return {'name': _('Snapshots'), 'type': 'ir.actions.act_window', 'res_model': 'garment.kpi.snapshot',
                'view_mode': 'tree,form,graph,pivot', 'domain': [('kpi_id', '=', self.id)],
                'context': {'default_kpi_id': self.id}}

    @api.model
    def _cron_generate_kpi_snapshots(self):
        today = fields.Date.context_today(self)
        kpis = self.search([('active', '=', True)])
        for kpi in kpis:
            if not kpi._is_due(today): continue
            date_from, date_to = kpi._get_period_window(today)
            try:
                kpi._generate_snapshot(today, date_from, date_to)
            except Exception:
                _logger.exception('garment_analytics_bi: snapshot generation failed for KPI %s', kpi.name)
        return True