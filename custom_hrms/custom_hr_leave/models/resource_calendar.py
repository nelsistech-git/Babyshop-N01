from odoo import api, fields, models

# from odoo.addons.resource.models.resource import Intervals, HOURS_PER_DAY, float_to_time
from odoo.addons.resource.models.utils import Intervals, float_to_time

from pytz import timezone
from datetime import datetime, time
from dateutil import rrule


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    # active = fields.Boolean(string='Active', default=True)
    # hour_from_per_day_m = fields.Float(string='Morning Time From',
    #                                    help="Start and End time of working. A specific value of 24:00 is interpreted as 23:59:59.999999.")
    # hour_to_per_day_m = fields.Float(string='Morning Time To')
    # hour_from_per_day_e = fields.Float(string='Evening Time From',
    #                                    help="Start and End time of working. A specific value of 24:00 is interpreted as 23:59:59.999999.")
    # hour_to_per_day_e = fields.Float(string='Evening Time To')
    #
    # @api.onchange('hour_from_per_day', 'hour_to_per_day')
    # def _onchange_hours_from_to(self):
    #     # avoid negative or after midnight
    #     self.hour_from_per_day = min(self.hour_from_per_day, 23.99)
    #     self.hour_from_per_day = max(self.hour_from_per_day, 0.0)
    #     self.hour_to_per_day = min(self.hour_to_per_day, 23.99)
    #     self.hour_to_per_day = max(self.hour_to_per_day, 0.0)
    #
    #     # avoid wrong order
    #     self.hour_to_per_day = max(self.hour_to_per_day, self.hour_from_per_day)


    def _weekend_intervals(self, start_dt, end_dt, resource=None, tz=None):
        """ Return the weekend intervals in the given datetime range.
            The returned intervals are expressed in the resource's timezone.
        """
        tz = tz if tz else timezone((resource or self).tz)
        start_dt = start_dt.astimezone(tz)
        end_dt = end_dt.astimezone(tz)
        start = start_dt.date()
        until = end_dt.date()
        result = []

        weekdays = [int(attendance.dayofweek) for attendance in self.attendance_ids]
        weekends = [d for d in range(7) if d not in weekdays]
        for day in rrule.rrule(rrule.DAILY, start, until=until, byweekday=weekends):
            # weekend specified hour calculated
            hour_from_per_day_m = self.hour_from_per_day_m
            hour_to_per_day_m = self.hour_to_per_day_m
            hour_from_per_day_e = self.hour_from_per_day_e
            hour_to_per_day_e = self.hour_to_per_day_e
            result.append((datetime.combine(day, float_to_time(hour_from_per_day_m)).astimezone(tz),
                           datetime.combine(day, float_to_time(hour_to_per_day_m)).astimezone(tz), self
                           ),
                          )
            result.append((datetime.combine(day, float_to_time(hour_from_per_day_e)).astimezone(tz),
                           datetime.combine(day, float_to_time(hour_to_per_day_e)).astimezone(tz), self
                           ),
                          )
            # weekend full hour calculated
        #             result.append((datetime.combine(day,time.min).astimezone(tz),
        #                            datetime.combine(day,time.max).astimezone(tz),self
        #                            ),
        #                           )

        return Intervals(result)

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, tz=None, lunch=False):
        res = super()._attendance_intervals_batch(start_dt=start_dt,
                                            end_dt=end_dt,
                                            resources=resources, lunch=False)
        if self.env.context.get('from_leave_request', False) and not self.env.context.get('exclude_weekends', False):
            weekend = self._weekend_intervals(start_dt, end_dt, resources, tz=tz)
            res = res | weekend
        return res
