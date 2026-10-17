# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .tools import eval_domain, is_dashboard_admin, jsonable

_logger = logging.getLogger(__name__)


class BondDashboardKpi(models.Model):
    """Definition of one dashboard card.

    Values are never stored: each card is computed live with the *current
    user's* access rights, so record rules always apply.
    """
    _name = 'bond.dashboard.kpi'
    _description = 'Bond Dashboard Card'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    section = fields.Selection([
        ('license', 'Licenses & Entitlements'),
        ('documents', 'Documents & Receipts'),
        ('inventory', 'Inventory'),
        ('compliance', 'Reconciliation & Compliance'),
        ('audit', 'Audit Access'),
    ], required=True, default='license')
    kpi_type = fields.Selection([
        ('count', 'Record count'),
        ('sum', 'Sum of a numeric field'),
        ('breakdown', 'Breakdown by a field'),
        ('ratio', 'Ratio (sum A / sum B, in %)'),
    ], string='Type', required=True, default='count')
    model_name = fields.Char(string='Model', required=True, help='Technical model name, e.g. stock.quant')
    domain = fields.Char(
        default='[]',
        help="Python domain. Available names: today, now, relativedelta, timedelta, alert_days.")
    measure_field = fields.Char(string='Measure field', help='Numeric field summed (sum / breakdown / ratio numerator).')
    denominator_field = fields.Char(help='Numeric field for the ratio denominator.')
    groupby_field = fields.Char(string='Group by field', help='Stored field used by breakdown cards.')
    icon = fields.Char(default='fa-bar-chart', help='Font Awesome class, e.g. fa-id-card')
    color = fields.Selection([
        ('primary', 'Blue'), ('success', 'Green'), ('warning', 'Amber'),
        ('danger', 'Red'), ('info', 'Teal'), ('secondary', 'Grey'),
    ], default='primary', required=True)
    danger_if_positive = fields.Boolean(
        string='Highlight red when above zero',
        help='Use for exception counters (expired, missing, unresolved).')
    group_ids = fields.Many2many(
        'res.groups', 'bond_dashboard_kpi_group_rel', 'kpi_id', 'group_id',
        string='Visible to groups',
        help='Empty = every dashboard user. Dashboard administrators always see every card.')
    description = fields.Text(help='Assumptions / notes about this card.')

    @api.constrains('kpi_type', 'measure_field', 'denominator_field', 'groupby_field')
    def _check_configuration(self):
        for kpi in self:
            if kpi.kpi_type == 'sum' and not kpi.measure_field:
                raise ValidationError(_('"%s": a sum card needs a measure field.', kpi.name))
            if kpi.kpi_type == 'breakdown' and not kpi.groupby_field:
                raise ValidationError(_('"%s": a breakdown card needs a group-by field.', kpi.name))
            if kpi.kpi_type == 'ratio' and not (kpi.measure_field and kpi.denominator_field):
                raise ValidationError(_('"%s": a ratio card needs both numerator and denominator fields.', kpi.name))

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def _group_label(self, field, key):
        if field.type == 'boolean':
            return _('Yes') if key else _('No')
        if isinstance(key, models.BaseModel):
            return key.display_name or _('Undefined')
        if key in (False, None):
            return _('Undefined')
        if field.type == 'selection':
            return dict(field._description_selection(self.env)).get(key, str(key))
        return str(key)

    def _sum(self, Model, domain, field_name):
        if field_name not in Model._fields:
            raise ValueError(_('Field "%(field)s" does not exist on %(model)s.', field=field_name, model=Model._name))
        return Model._read_group(domain, [], ['%s:sum' % field_name])[0][0] or 0.0

    def _evaluate(self):
        """Return the card payload for the current user."""
        self.ensure_one()
        card = {
            'id': self.id, 'name': self.name, 'icon': self.icon or 'fa-bar-chart',
            'color': self.color, 'type': self.kpi_type, 'model': self.model_name,
            'status': 'ok', 'message': '', 'value': 0, 'display': '0', 'rows': [],
            'domain': [], 'danger_if_positive': self.danger_if_positive,
        }
        if self.model_name not in self.env:
            card.update(status='unavailable', message=_('Model %s is not installed.', self.model_name))
            return card
        Model = self.env[self.model_name]
        if not Model.check_access_rights('read', raise_exception=False):
            card['status'] = 'no_access'
            return card
        try:
            with self.env.cr.savepoint():
                domain = eval_domain(self.env, self.domain)
                card['domain'] = jsonable(domain)
                if self.kpi_type == 'count':
                    value = Model.search_count(domain)
                    card['display'] = '{:,}'.format(value)
                elif self.kpi_type == 'sum':
                    value = self._sum(Model, domain, self.measure_field)
                    card['display'] = '{:,.2f}'.format(value)
                elif self.kpi_type == 'ratio':
                    num = self._sum(Model, domain, self.measure_field)
                    den = self._sum(Model, domain, self.denominator_field)
                    value = (num / den * 100.0) if den else 0.0
                    card['display'] = '{:.1f}%'.format(value)
                else:
                    value = self._evaluate_breakdown(Model, domain, card)
                card['value'] = value
        except Exception as exc:  # shown to administrators as a configuration hint
            _logger.warning('Dashboard card "%s" failed: %s', self.name, exc)
            card.update(status='error', message=str(exc)[:300], value=0, display='-', rows=[])
        return card

    def _evaluate_breakdown(self, Model, domain, card):
        group_name = self.groupby_field.split(':')[0]
        field = Model._fields.get(group_name)
        if field is None:
            raise ValueError(_('Field "%(field)s" does not exist on %(model)s.', field=group_name, model=Model._name))
        aggregates = ['__count']
        if self.measure_field:
            if self.measure_field not in Model._fields:
                raise ValueError(_('Field "%(field)s" does not exist on %(model)s.', field=self.measure_field, model=Model._name))
            aggregates.append('%s:sum' % self.measure_field)
        groups = Model._read_group(domain, [self.groupby_field], aggregates, limit=100)
        rows = []
        for group in groups:
            amount = group[2] if self.measure_field else group[1]
            rows.append({'label': self._group_label(field, group[0]), 'value': amount or 0.0})
        rows.sort(key=lambda r: r['value'], reverse=True)
        total = sum(r['value'] for r in rows)
        top = rows[0]['value'] if rows else 0
        for row in rows:
            row['pct'] = round(row['value'] / top * 100, 1) if top else 0
            row['display'] = '{:,.2f}'.format(row['value']) if self.measure_field else '{:,}'.format(int(row['value']))
        card['rows'] = rows[:8]
        card['display'] = '{:,.2f}'.format(total) if self.measure_field else '{:,}'.format(int(total))
        return total

    def action_test(self):
        """Admin helper: evaluate the card and report the outcome."""
        self.ensure_one()
        card = self._evaluate()
        ok = card['status'] == 'ok'
        message = _('Value: %s', card['display']) if ok else card['message'] or card['status']
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Card test'), 'message': message,
                       'type': 'success' if ok else 'danger', 'sticky': not ok},
        }

    @api.model
    def _visible_for_current_user(self, kpi):
        if is_dashboard_admin(self.env) or not kpi.group_ids:
            return True
        return bool(kpi.group_ids & self.env.user.groups_id)
