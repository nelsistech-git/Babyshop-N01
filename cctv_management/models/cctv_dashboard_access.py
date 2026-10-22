# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# One entry per dashboard in the CCTV > Dashboards menu.
#   menu / action : xml ids (without module prefix) that this record controls
#   models        : models the dashboard reads. Used to warn on the page itself when a
#                   user is in an allowed group but lacks read access to the data.
DASHBOARDS = {
    'command_center': {
        'menu': 'menu_cctv_dashboard_command_center',
        'action': 'action_cctv_command_center',
        'models': ['cctv.camera', 'cctv.alert', 'cctv.incident', 'cctv.event'],
    },
    'executive': {
        'menu': 'menu_cctv_dashboard_executive',
        'action': 'action_cctv_executive_dashboard',
        'models': ['cctv.alert'],
    },
    'operations': {
        'menu': 'menu_cctv_dashboard_operations',
        'action': 'action_cctv_operations_dashboard',
        'models': ['cctv.camera'],
    },
    'analytics': {
        'menu': 'menu_cctv_dashboard_analytics',
        'action': 'action_cctv_analytics_dashboard',
        'models': ['cctv.event'],
    },
    'facility_map': {
        'menu': 'menu_cctv_dashboard_facility_map',
        'action': 'action_cctv_facility_map',
        'models': ['cctv.office', 'cctv.camera', 'cctv.alert'],
    },
    'heat_map': {
        'menu': 'menu_cctv_dashboard_heat_map',
        'action': 'action_cctv_heat_map',
        'models': ['cctv.office', 'cctv.department', 'cctv.event'],
    },
    'hr': {
        'menu': 'menu_cctv_dashboard_hr',
        'action': 'action_cctv_hr_violation_dashboard',
        'models': ['cctv.violation'],
    },
    'factory': {
        'menu': 'menu_cctv_dashboard_factory',
        'action': 'action_cctv_factory_violation_dashboard',
        'models': ['cctv.violation'],
    },
    'management': {
        'menu': 'menu_cctv_dashboard_management',
        'action': 'action_cctv_management_violation_dashboard',
        'models': ['cctv.violation'],
    },
}
MAP_KEYS = ('command_center', 'facility_map', 'heat_map')
MIN_REFRESH_SECONDS = 10


class CctvDashboardAccess(models.Model):
    """Who may open which dashboard (CCTV > Configuration > Dashboard Access).

    Saving a record pushes its groups onto the dashboard's menu entry (and onto its
    window action), so the menu simply disappears for everybody else. Super
    Administrators are always allowed so nobody can lock the admins out.

    This controls visibility/entry, not data security: what a user can read inside a
    dashboard is still decided by the model access rights (security/ir.model.access.csv).
    """
    _name = 'cctv.dashboard.access'
    _description = 'CCTV Dashboard Access'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    key = fields.Selection(
        [(k, k) for k in DASHBOARDS], required=True, readonly=True, index=True,
        help='Technical identifier of the dashboard this record controls.')
    sequence = fields.Integer(default=10)
    group_ids = fields.Many2many(
        'res.groups', 'cctv_dashboard_access_group_rel', 'access_id', 'group_id',
        string='Allowed Groups',
        help='Users in any of these groups see the dashboard. Super Administrators always do. '
             'Leave empty to hide the dashboard from everybody except Super Administrators.')
    refresh_seconds = fields.Integer(
        string='Auto-refresh (s)', default=0,
        help='Command Center / Facility Map / Heat Map only: reload the data every N seconds while the page is '
             'open and visible. 0 turns auto-refresh off; otherwise at least %s.' % MIN_REFRESH_SECONDS)
    is_map = fields.Boolean(compute='_compute_is_map')
    required_data = fields.Char(string='Reads data from', compute='_compute_required_data')

    _sql_constraints = [
        ('key_uniq', 'unique(key)', 'There is already an access record for this dashboard.'),
    ]

    # ------------------------------------------------------------------ computes / checks
    @api.depends('key')
    def _compute_is_map(self):
        for rec in self:
            rec.is_map = rec.key in MAP_KEYS

    @api.depends('key')
    def _compute_required_data(self):
        ir_model = self.env['ir.model'].sudo()
        for rec in self:
            names = [ir_model._get(m).name or m for m in DASHBOARDS.get(rec.key, {}).get('models', [])]
            rec.required_data = ', '.join(names)

    @api.constrains('refresh_seconds')
    def _check_refresh_seconds(self):
        for rec in self:
            if rec.refresh_seconds and rec.refresh_seconds < MIN_REFRESH_SECONDS:
                raise ValidationError(_(
                    'Auto-refresh must be 0 (off) or at least %s seconds.', MIN_REFRESH_SECONDS))

    # ------------------------------------------------------------------ menu / action sync
    def _effective_groups(self):
        self.ensure_one()
        return self.group_ids | self.env.ref('cctv_management.group_cctv_admin')

    def _sync_access(self):
        """Push the allowed groups onto the dashboard's menu and window action."""
        for rec in self:
            meta = DASHBOARDS.get(rec.key)
            if not meta:
                continue
            groups = rec._effective_groups()
            menu = self.env.ref('cctv_management.' + meta['menu'], raise_if_not_found=False)
            if menu:
                menu.sudo().write({'groups_id': [(6, 0, groups.ids)]})
            action = self.env.ref('cctv_management.' + meta['action'], raise_if_not_found=False)
            # Only window actions carry groups; client actions (maps) are gated in the page itself.
            if action and action._name == 'ir.actions.act_window' and 'groups_id' in action._fields:
                action.sudo().write({'groups_id': [(6, 0, groups.ids)]})

    @api.model
    def _sync_all(self):
        """Re-apply every record. Called after each module update so the menu always matches settings."""
        self.sudo().search([])._sync_access()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_access()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'group_ids' in vals or 'key' in vals:
            self._sync_access()
        return res

    # ------------------------------------------------------------------ used by the map pages
    @api.model
    def get_dashboard_state(self, key):
        """For the client-side dashboards (Facility Map, Heat Map).

        Returns whether the current user may open it, which required models they cannot read,
        and the auto-refresh interval.
        """
        rec = self.sudo().search([('key', '=', key)], limit=1)
        admin = self.env.ref('cctv_management.group_cctv_admin')
        groups = rec._effective_groups() if rec else admin
        allowed = bool(groups & self.env.user.groups_id)
        ir_model = self.env['ir.model'].sudo()
        missing = []
        for model_name in DASHBOARDS.get(key, {}).get('models', []):
            if not self.env[model_name].check_access_rights('read', raise_exception=False):
                missing.append(ir_model._get(model_name).name or model_name)
        return {
            'allowed': allowed,
            'missing_models': missing,
            'refresh_seconds': rec.refresh_seconds if rec else 0,
        }
