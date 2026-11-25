import logging
from datetime import timedelta

from odoo import api, fields, models, _

from odoo.addons.nelsis_field_tracking.utils.geo import haversine_m

_logger = logging.getLogger(__name__)

ROAD_FACTOR = 1.35          # straight line -> road distance
TOLERANCE = 0.55            # employee must have travelled at least 55 % of what is claimed
MIN_KM_FOR_PAID_TRIP = 0.4  # a paid conveyance with (almost) no movement is suspicious
BAD_SHARE = 0.30            # >30 % non-genuine GPS points that day => suspicious


class ConveyanceSheetLine(models.Model):
    _inherit = 'conveyance.sheet.line'

    nl_employee_id = fields.Many2one(related='sheet_id.employee_id', store=True, string='Employee')
    nl_sheet_state = fields.Selection(related='sheet_id.state', store=True, string='Sheet Status')
    nl_claimed_km = fields.Float(string='Claimed Distance (km)')
    nl_from_lat = fields.Float(digits=(10, 7))
    nl_from_lng = fields.Float(digits=(10, 7))
    nl_to_lat = fields.Float(digits=(10, 7))
    nl_to_lng = fields.Float(digits=(10, 7))
    nl_captured_at = fields.Datetime(string='Entered on phone at')
    nl_geo_km = fields.Float(string='GPS Distance (km)', readonly=True, digits=(12, 2))
    nl_geo_points = fields.Integer(string='GPS Points', readonly=True)
    nl_geo_bad_points = fields.Integer(string='False GPS Points', readonly=True)
    nl_geo_status = fields.Selection([
        ('pending', 'Not checked'), ('no_data', 'No GPS data'), ('verified', 'Verified (True)'),
        ('mismatch', 'Mismatch (False)'), ('suspicious', 'Suspicious data'),
    ], string='Map Check', default='pending', readonly=True, index=True)
    nl_geo_ok = fields.Boolean(string='Matches Map', compute='_compute_nl_geo_ok', store=True)
    nl_geo_note = fields.Char(string='Map Note', readonly=True)
    nl_dup_bill = fields.Boolean(string='Duplicate Bill', readonly=True)

    @api.depends('nl_geo_status')
    def _compute_nl_geo_ok(self):
        for l in self:
            l.nl_geo_ok = l.nl_geo_status == 'verified'

    # ------------------------------------------------------------------ verification
    def _claimed_distance_km(self):
        self.ensure_one()
        if self.nl_claimed_km:
            return self.nl_claimed_km
        if self.nl_from_lat and self.nl_to_lat:
            return haversine_m(self.nl_from_lat, self.nl_from_lng, self.nl_to_lat, self.nl_to_lng) * ROAD_FACTOR / 1000.0
        return 0.0

    def action_geo_verify(self):
        Log = self.env['nelsis.location.log'].sudo()
        for l in self:
            emp = l.nl_employee_id
            vals = {'nl_geo_status': 'no_data', 'nl_geo_km': 0.0, 'nl_geo_points': 0, 'nl_geo_bad_points': 0,
                    'nl_geo_note': _('No GPS track for this employee on %s.') % (l.date or '')}
            logs = Log.search([('employee_id', '=', emp.id), ('log_date', '=', l.date)]) if emp and l.date else Log
            if logs:
                km = sum(logs.mapped('distance_m')) / 1000.0
                bad = len(logs.filtered(lambda x: not x.is_genuine))
                claimed = l._claimed_distance_km()
                vals.update(nl_geo_km=round(km, 2), nl_geo_points=len(logs), nl_geo_bad_points=bad)
                paid = (l.conveyance_amount or 0) > 0
                if bad / len(logs) > BAD_SHARE:
                    vals.update(nl_geo_status='suspicious', nl_geo_note=_(
                        '%(bad)s of %(n)s GPS points are fake / time-mismatched.', bad=bad, n=len(logs)))
                elif claimed and km < claimed * TOLERANCE:
                    vals.update(nl_geo_status='mismatch', nl_geo_note=_(
                        'Claimed %(c).1f km but GPS shows only %(g).1f km.', c=claimed, g=km))
                elif not claimed and paid and km < MIN_KM_FOR_PAID_TRIP:
                    vals.update(nl_geo_status='mismatch', nl_geo_note=_(
                        'Conveyance claimed but the employee barely moved (%.1f km).', km))
                else:
                    vals.update(nl_geo_status='verified', nl_geo_note=_('GPS track supports the claim (%.1f km).') % km)
            l.write(vals)
        return True

    @api.model
    def _cron_geo_verify(self):
        since = fields.Date.today() - timedelta(days=45)
        lines = self.search([('date', '>=', since), ('nl_sheet_state', 'not in', ('done', 'refused'))])
        lines.action_geo_verify()

    def action_open_map(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client', 'tag': 'nelsis_live_map', 'name': self.nl_employee_id.name,
            'context': {'focus_employee_id': self.nl_employee_id.id, 'focus_date': fields.Date.to_string(self.date)},
        }


class ConveyanceSheet(models.Model):
    _inherit = 'conveyance.sheet'

    nl_client_uuid = fields.Char(copy=False, index=True)
    nl_mismatch_count = fields.Integer(string='Map Mismatches', compute='_compute_nl_geo', store=True)
    nl_geo_ok = fields.Boolean(string='All Lines Match Map', compute='_compute_nl_geo', store=True)

    _sql_constraints = [('nl_uuid_uniq', 'unique(nl_client_uuid)', 'Duplicate mobile submission.')]

    @api.depends('line_ids.nl_geo_status')
    def _compute_nl_geo(self):
        for s in self:
            bad = s.line_ids.filtered(lambda l: l.nl_geo_status in ('mismatch', 'suspicious'))
            s.nl_mismatch_count = len(bad)
            s.nl_geo_ok = bool(s.line_ids) and all(l.nl_geo_status == 'verified' for l in s.line_ids)

    def action_geo_verify(self):
        self.mapped('line_ids').action_geo_verify()
        return True


class NelsisDashboardExtension(models.AbstractModel):
    _inherit = 'nelsis.dashboard.extension'

    @api.model
    def dashboard_extra(self, employees, date_from, date_to):
        res = super().dashboard_extra(employees, date_from, date_to)
        Line = self.env['conveyance.sheet.line']
        ldom = [('nl_employee_id', 'in', employees.ids), ('date', '>=', date_from), ('date', '<=', date_to)]
        claimed = Line._read_group(ldom, [], ['total_amount:sum'])
        by_state = Line._read_group(ldom, ['nl_sheet_state'], ['total_amount:sum'])
        labels = dict(self.env['conveyance.sheet']._fields['state'].selection)
        Adv = self.env['employee.advance']
        adv = Adv._read_group([('employee_id', 'in', employees.ids)], ['state'], ['amount:sum'])
        adv_labels = dict(Adv._fields['state'].selection)
        paid_adv = Adv.search([('employee_id', 'in', employees.ids), ('state', '=', 'paid')])
        outstanding = sum(a.amount for a in paid_adv)
        res.update({
            'expense_kpis': {
                'claimed': (claimed[0][0] if claimed else 0) or 0,
                'mismatch': Line.search_count(ldom + [('nl_geo_status', 'in', ('mismatch', 'suspicious'))]),
                'advance_outstanding': outstanding,
            },
            'expense_by_state': {labels.get(s, s or '-'): v or 0 for s, v in by_state},
            'advance_by_state': {adv_labels.get(s, s): v or 0 for s, v in adv},
        })
        return res
