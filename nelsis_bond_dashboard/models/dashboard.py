# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from .tools import has_dashboard_role, is_dashboard_admin

SECTION_ICONS = {
    'license': 'fa-id-card-o', 'documents': 'fa-files-o', 'inventory': 'fa-cubes',
    'compliance': 'fa-balance-scale', 'audit': 'fa-search',
}


class BondDashboard(models.AbstractModel):
    """Data provider for the OWL dashboard. Holds no data of its own."""
    _name = 'bond.dashboard'
    _description = 'Bond Dashboard Data Provider'

    @api.model
    def get_dashboard_data(self):
        if not has_dashboard_role(self.env):
            raise AccessError(_('You are not allowed to open the bonded warehouse dashboard.'))
        admin = is_dashboard_admin(self.env)
        Kpi = self.env['bond.dashboard.kpi']
        labels = dict(Kpi._fields['section']._description_selection(self.env))
        grouped = {}
        for kpi in Kpi.search([]):
            if not Kpi._visible_for_current_user(kpi):
                continue
            card = kpi._evaluate()
            if card['status'] == 'no_access':
                continue
            if card['status'] in ('unavailable', 'error') and not admin:
                continue
            grouped.setdefault(kpi.section, []).append(card)
        sections = [
            {'key': key, 'label': labels[key], 'icon': SECTION_ICONS.get(key, 'fa-th-large'), 'cards': grouped[key]}
            for key in labels if key in grouped
        ]

        Alert = self.env['bond.dashboard.alert']
        open_domain = [('state', '!=', 'resolved')]
        type_labels = dict(Alert._fields['alert_type']._description_selection(self.env))
        rank = {'critical': 0, 'warning': 1, 'info': 2}
        found = Alert.search(open_domain, order='create_date desc', limit=50)
        found = found.sorted(key=lambda a: rank.get(a.severity, 3))[:6]
        alerts = [{
            'id': a.id, 'name': a.name, 'severity': a.severity,
            'type': type_labels.get(a.alert_type, ''), 'state': a.state,
            'deadline': fields.Date.to_string(a.deadline) if a.deadline else '',
        } for a in found]
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        return {
            'generated': now.strftime('%Y-%m-%d %H:%M'),
            'is_admin': admin,
            'sections': sections,
            'alerts': alerts,
            'alert_total': Alert.search_count(open_domain),
        }
