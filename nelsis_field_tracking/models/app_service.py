from datetime import datetime, timedelta

from odoo import api, fields, models


class NelsisAppService(models.AbstractModel):
    """Payload builders for the mobile app. Other addons extend these with `super()`."""
    _name = 'nelsis.app.service'
    _description = 'Nelsis mobile app service'

    @api.model
    def att_dict(self, a):
        tz_in = fields.Datetime.context_timestamp(a, a.check_in) if a.check_in else None
        return {
            'id': a.id,
            'check_in': fields.Datetime.to_string(a.check_in).replace(' ', 'T') + 'Z' if a.check_in else None,
            'check_out': fields.Datetime.to_string(a.check_out).replace(' ', 'T') + 'Z' if a.check_out else None,
            'worked_hours': round(a.worked_hours or 0, 2),
            'in_lat': a.in_latitude, 'in_lng': a.in_longitude, 'out_lat': a.out_latitude, 'out_lng': a.out_longitude,
            'in_address': a.nl_in_address or '', 'out_address': a.nl_out_address or '',
            'geo_status': a.nl_geo_status, 'in_genuine': a.nl_in_genuine, 'out_genuine': a.nl_out_genuine,
            'offline': bool(a.nl_in_offline or a.nl_out_offline),
            'date': tz_in.strftime('%Y-%m-%d') if tz_in else None,
        }

    @api.model
    def profile(self, employee):
        user = employee.user_id
        return {
            'user_id': user.id, 'employee_id': employee.id, 'name': employee.name,
            'job': employee.job_title or '', 'department': employee.department_id.name or '',
            'email': employee.work_email or user.email or '', 'phone': employee.mobile_phone or employee.work_phone or '',
            'manager': employee.parent_id.name or '', 'company': employee.company_id.name,
            'is_manager': user.has_group('nelsis_field_tracking.group_nelsis_manager'),
            'field_staff': employee.nl_field_staff, 'tracking_enabled': employee.nl_tracking_enabled,
            'avatar': '/web/image/hr.employee/%s/avatar_128' % employee.id,
        }

    @api.model
    def dashboard(self, employee):
        Att = self.env['hr.attendance'].sudo()
        today = fields.Date.context_today(self)
        # cover the whole month AND the last 7 days (the week chart crosses the month boundary)
        first = min(today.replace(day=1), today - timedelta(days=6))
        start = datetime.combine(first, datetime.min.time()) - timedelta(hours=14)
        atts = Att.search([('employee_id', '=', employee.id), ('check_in', '>=', start)], order='check_in asc')
        days = {}
        hours = 0.0
        month_days = set()
        for a in atts:
            d = fields.Datetime.context_timestamp(a, a.check_in).date()
            days[d] = days.get(d, 0) + (a.worked_hours or 0)
            if d.month == today.month and d.year == today.year:
                hours += a.worked_hours or 0
                month_days.add(d)
        open_att = Att.search([('employee_id', '=', employee.id), ('check_out', '=', False)], limit=1)
        week = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            week.append({'date': d.isoformat(), 'label': d.strftime('%a'), 'hours': round(days.get(d, 0), 2)})
        dist = self.env['nelsis.location.log'].sudo()._read_group(
            [('employee_id', '=', employee.id), ('log_date', '=', today)], [], ['distance_m:sum'])
        return {
            'attendance': {
                'punched_in': bool(open_att), 'since': fields.Datetime.to_string(open_att.check_in).replace(' ', 'T') + 'Z' if open_att else None,
                'days_present': len(month_days), 'hours_month': round(hours, 1), 'week': week,
                'distance_today_km': round(((dist[0][0] if dist else 0) or 0) / 1000.0, 2),
            },
        }
