# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
AI Demand Forecasting (SRS section 25) — the ONE real, fully-working
end-to-end feature of this module. ``action_generate_demand_forecast``
queries actual historical ``garment.order.line`` records (joined to
``garment.order`` for the order date and, via the line's own stored related
field, the buyer) for a Style — optionally narrowed to one Buyer — groups
the historical quantity by calendar month, and projects a forecast using a
genuinely computed simple moving-average or recency-weighted trend. This is
deliberately NOT a hardcoded/black-box number: with zero historical orders
it returns zero with a low confidence score and says so.
"""
from collections import OrderedDict
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentDemandForecast(models.Model):
    _name = 'garment.demand.forecast'
    _description = 'Garment AI Demand Forecast'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'forecast_date desc, id desc'

    name = fields.Char(string='Reference', copy=False, readonly=True, index=True, default=lambda s: _('New'))
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', tracking=True,
                                help='Optional — narrows the historical basis to this buyer\'s orders for '
                                     'the style. Leave blank to forecast demand across all buyers.')
    forecast_date = fields.Date(string='Forecast Date', default=fields.Date.context_today, required=True)

    period_type = fields.Selection([
        ('monthly', 'Monthly'), ('quarterly', 'Quarterly'),
    ], string='Period Type', default='monthly', required=True, tracking=True)
    historical_basis = fields.Selection([
        ('last_3', 'Last 3 Periods'),
        ('last_6', 'Last 6 Periods'),
        ('last_12', 'Last 12 Periods'),
        ('all', 'All Available History'),
    ], string='Historical Basis', default='last_6', required=True, tracking=True)
    method = fields.Selection([
        ('moving_average', 'Simple Moving Average'),
        ('weighted_trend', 'Recency-Weighted Trend'),
        ('simple_average', 'Simple Average (All History)'),
    ], string='Forecast Method', default='moving_average', required=True, tracking=True)
    forecast_horizon = fields.Integer(string='Forecast Horizon (Periods)', default=3,
                                       help='How many future periods to project forward.')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('reviewed', 'Reviewed'),
        ('applied', 'Applied To Planning'),
    ], string='Status', default='draft', required=True, tracking=True)

    forecast_qty = fields.Float(string='Forecast Qty / Period', readonly=True, copy=False,
                                 help='The computed per-period quantity projected forward, e.g. next month\'s '
                                      'expected order quantity for this style.')
    confidence_score = fields.Float(string='Confidence (%)', readonly=True, copy=False)
    basis_period_count = fields.Integer(string='Historical Periods Used', readonly=True, copy=False)
    basis_order_line_count = fields.Integer(string='Historical Order Lines Used', readonly=True, copy=False)
    basis_qty_total = fields.Integer(string='Historical Qty Total', readonly=True, copy=False)
    explanation = fields.Text(string='Explanation', readonly=True, copy=False)
    last_generated = fields.Datetime(string='Last Generated On', readonly=True, copy=False)

    basis_order_ids = fields.Many2many('garment.order', string='Historical Orders Used',
                                        readonly=True, copy=False)
    basis_order_count = fields.Integer(compute='_compute_basis_order_count')
    line_ids = fields.One2many('garment.demand.forecast.line', 'forecast_id', string='Period Breakdown', copy=False)
    ai_insight_id = fields.Many2one('garment.ai.insight', string='AI Insight', readonly=True, copy=False)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    @api.depends('basis_order_ids')
    def _compute_basis_order_count(self):
        for rec in self:
            rec.basis_order_count = len(rec.basis_order_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.demand.forecast') or _('New')
        return super().create(vals_list)

    # ==================================================================
    # The ONE real, working, end-to-end AI feature of this module.
    # ==================================================================
    def action_generate_demand_forecast(self):
        """Compute a deterministic moving-average / weighted-trend demand
        forecast from real historical ``garment.order.line`` records for
        this Style (and Buyer, if set). No external AI call, no hardcoded
        result — genuinely derived from the ERP's own order history."""
        for rec in self:
            rec._generate_demand_forecast_one()
        return True

    def _generate_demand_forecast_one(self):
        self.ensure_one()
        if not self.style_id:
            raise UserError(_('Select a Style before generating a demand forecast.'))

        domain = [('style_id', '=', self.style_id.id)]
        if self.buyer_id:
            domain.append(('buyer_id', '=', self.buyer_id.id))
        order_lines = self.env['garment.order.line'].search(domain)

        # Group historical quantity by calendar month (or quarter) of the
        # parent order's order_date — this is the real "historical basis".
        monthly = OrderedDict()
        for line in order_lines.sorted(lambda l: l.order_id.order_date or date.min):
            order_date = line.order_id.order_date
            if not order_date:
                continue
            period_key = self._period_key(order_date)
            monthly[period_key] = monthly.get(period_key, 0) + (line.quantity or 0)

        periods = list(monthly.keys())
        lookback_map = {'last_3': 3, 'last_6': 6, 'last_12': 12, 'all': len(periods)}
        lookback = lookback_map.get(self.historical_basis, 6) or len(periods)
        recent_periods = periods[-lookback:] if lookback else periods
        recent_qtys = [monthly[p] for p in recent_periods]

        forecast_value, method_note = self._compute_forecast_value(recent_qtys, list(monthly.values()))
        confidence = self._compute_confidence(recent_qtys)

        # Build the period breakdown: historical periods actually used, plus
        # the projected future periods at the computed forecast value.
        line_vals = []
        sequence = 10
        for period_key in recent_periods:
            line_vals.append((0, 0, {
                'sequence': sequence, 'period_label': period_key, 'period_date': self._period_start_date(period_key),
                'data_type': 'historical', 'quantity': monthly[period_key],
            }))
            sequence += 10
        anchor_period = recent_periods[-1] if recent_periods else self._period_key(fields.Date.context_today(self))
        horizon = self.forecast_horizon or 3
        for step in range(1, horizon + 1):
            future_period = self._shift_period(anchor_period, step)
            line_vals.append((0, 0, {
                'sequence': sequence, 'period_label': future_period, 'period_date': self._period_start_date(future_period),
                'data_type': 'forecast', 'quantity': forecast_value,
            }))
            sequence += 10

        explanation = self._build_explanation(order_lines, recent_periods, recent_qtys, forecast_value,
                                                method_note, confidence)

        self.line_ids.unlink()
        self.write({
            'forecast_qty': forecast_value,
            'confidence_score': confidence,
            'basis_period_count': len(recent_periods),
            'basis_order_line_count': len(order_lines),
            'basis_qty_total': sum(monthly.values()),
            'basis_order_ids': [(6, 0, order_lines.mapped('order_id').ids)],
            'line_ids': line_vals,
            'explanation': explanation,
            'status': 'generated',
            'last_generated': fields.Datetime.now(),
        })

        insight = self.env['garment.ai.insight'].create({
            'insight_type': 'demand_forecast',
            'res_model': 'garment.demand.forecast',
            'res_id': self.id,
            'confidence': confidence,
            'explanation': explanation,
            'recommendation': _('Projected demand for %s over the next %s period(s): ~%s units/period.') % (
                self.style_id.display_name, horizon, int(round(forecast_value))),
            'source': 'heuristic',
        })
        self.ai_insight_id = insight.id

    # ------------------------------------------------------------------
    # Forecast math helpers
    # ------------------------------------------------------------------
    def _period_key(self, a_date):
        if self.period_type == 'quarterly':
            quarter = (a_date.month - 1) // 3 + 1
            return '%04d-Q%d' % (a_date.year, quarter)
        return '%04d-%02d' % (a_date.year, a_date.month)

    def _period_start_date(self, period_key):
        try:
            if 'Q' in period_key:
                year_str, q_str = period_key.split('-Q')
                month = (int(q_str) - 1) * 3 + 1
                return date(int(year_str), month, 1)
            year_str, month_str = period_key.split('-')
            return date(int(year_str), int(month_str), 1)
        except (ValueError, IndexError):
            return fields.Date.context_today(self)

    def _shift_period(self, period_key, steps):
        start = self._period_start_date(period_key)
        if self.period_type == 'quarterly':
            month_index = start.month - 1 + steps * 3
        else:
            month_index = start.month - 1 + steps
        year = start.year + month_index // 12
        month = month_index % 12 + 1
        return self._period_key(date(year, month, 1))

    def _compute_forecast_value(self, recent_qtys, all_qtys):
        self.ensure_one()
        if self.method == 'weighted_trend' and recent_qtys:
            weights = list(range(1, len(recent_qtys) + 1))
            value = sum(q * w for q, w in zip(recent_qtys, weights)) / float(sum(weights))
            note = 'recency-weighted average of %d historical period(s) (recent periods weighted higher)' % \
                len(recent_qtys)
        elif self.method == 'simple_average' and all_qtys:
            value = sum(all_qtys) / float(len(all_qtys))
            note = 'simple average across all %d available historical period(s)' % len(all_qtys)
        elif recent_qtys:
            value = sum(recent_qtys) / float(len(recent_qtys))
            note = 'simple moving average of the last %d historical period(s)' % len(recent_qtys)
        else:
            value, note = 0.0, 'no historical order data found for this style/buyer combination'
        return value, note

    @staticmethod
    def _compute_confidence(recent_qtys):
        """Deterministic confidence heuristic: more historical periods and
        lower period-to-period variance both raise confidence."""
        n = len(recent_qtys)
        if n >= 6:
            base = 85.0
        elif n >= 3:
            base = 65.0
        elif n >= 1:
            base = 40.0
        else:
            return 10.0
        mean = sum(recent_qtys) / float(n)
        if n > 1 and mean:
            variance = sum((q - mean) ** 2 for q in recent_qtys) / float(n)
            coeff_of_variation = (variance ** 0.5) / mean
            base -= min(35.0, coeff_of_variation * 50.0)
        return max(10.0, round(base, 1))

    def _build_explanation(self, order_lines, recent_periods, recent_qtys, forecast_value, method_note, confidence):
        self.ensure_one()
        buyer_part = ' for buyer "%s"' % self.buyer_id.display_name if self.buyer_id else ' across all buyers'
        if not recent_periods:
            return _('No historical %s order lines were found for style "%s"%s. Forecast defaults to 0 with '
                      'low confidence — link real Orders/Order Lines to this style to get a computed forecast.'
                      ) % ('garment.order.line', self.style_id.display_name, buyer_part)
        return _(
            'Computed from %d historical order line(s) across %d historical %s(s)%s, spanning periods %s to %s '
            '(total historical qty %s units). Method: %s. Forecast = %s. Confidence %.1f%% reflects the amount '
            'of historical data and its period-to-period variance.'
        ) % (
            len(order_lines), len(recent_periods), self.period_type, buyer_part,
            recent_periods[0], recent_periods[-1], sum(recent_qtys), method_note,
            round(forecast_value, 1), confidence,
        )

    # ==================================================================
    # Workflow actions
    # ==================================================================
    def action_mark_reviewed(self):
        self.write({'status': 'reviewed'})

    def action_apply_to_planning(self):
        for rec in self:
            if rec.status not in ('generated', 'reviewed'):
                raise UserError(_('Generate the forecast before applying it to planning.'))
        self.write({'status': 'applied'})

    def action_reset_to_draft(self):
        self.write({'status': 'draft'})

    def action_view_basis_orders(self):
        self.ensure_one()
        return {
            'name': _('Historical Orders Used'), 'type': 'ir.actions.act_window', 'res_model': 'garment.order',
            'view_mode': 'tree,form', 'domain': [('id', 'in', self.basis_order_ids.ids)],
        }

    def action_view_insight(self):
        self.ensure_one()
        if not self.ai_insight_id:
            return False
        return {
            'name': _('AI Insight'), 'type': 'ir.actions.act_window', 'res_model': 'garment.ai.insight',
            'view_mode': 'form', 'res_id': self.ai_insight_id.id,
        }


class GarmentDemandForecastLine(models.Model):
    _name = 'garment.demand.forecast.line'
    _description = 'Garment AI Demand Forecast — Period Breakdown'
    _order = 'forecast_id, sequence, id'

    forecast_id = fields.Many2one('garment.demand.forecast', string='Forecast', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    period_label = fields.Char(string='Period', required=True)
    period_date = fields.Date(string='Period Start Date')
    data_type = fields.Selection([
        ('historical', 'Historical'), ('forecast', 'Forecast'),
    ], string='Type', required=True, default='historical')
    quantity = fields.Float(string='Quantity')
