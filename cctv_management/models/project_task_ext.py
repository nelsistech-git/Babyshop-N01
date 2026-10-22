# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = 'project.task'

    cctv_zone_id = fields.Many2one('cctv.department', string='Expected Work Zone',
                                    help='If set, the assigned employee is expected to be detected in '
                                         'this zone while this task is open. Requires the employee to '
                                         'also have a cctv.employee.monitor assignment with a linked '
                                         'face-database entry - without that, presence can\'t be checked.')
    cctv_task_delay_flagged = fields.Boolean(
        default=False, help='True once a task_delay event has been raised for this task, to avoid duplicates')

    @api.model
    def cron_check_task_delay(self):
        """Flag tasks that are overdue and not done, where the assigned
        employee has no recorded camera presence in the task's expected
        zone in the last 3 days. This only runs for tasks that explicitly
        set cctv_zone_id - it does not scan every task in the system."""
        today = fields.Date.context_today(self)
        overdue_tasks = self.search([
            ('cctv_zone_id', '!=', False),
            ('date_deadline', '<', today),
            ('cctv_task_delay_flagged', '=', False),
            ('stage_id.is_closed', '=', False),
        ])
        Monitor = self.env['cctv.employee.monitor']
        Event = self.env['cctv.event']
        since = fields.Datetime.now() - timedelta(days=3)

        for task in overdue_tasks:
            employee = task.user_ids[:1].mapped('employee_ids')[:1] if task.user_ids else False
            if not employee:
                continue
            monitor = Monitor.search([('employee_id', '=', employee.id)], limit=1)
            if not monitor or not monitor.person_id:
                continue

            recent_presence = Event.search_count([
                ('person_id', '=', monitor.person_id.id),
                ('department_id', '=', task.cctv_zone_id.id),
                ('event_time', '>=', since),
                ('source_service', '!=', 'cctv_employee_monitor_cron'),   # ignore our own alerts
            ])
            if recent_presence == 0:
                monitor._create_compliance_alert(
                    'task_delay',
                    f'Task "{task.name}" overdue and no camera presence detected for '
                    f'{employee.name} in {task.cctv_zone_id.name} in the last 3 days',
                )
                task.cctv_task_delay_flagged = True
