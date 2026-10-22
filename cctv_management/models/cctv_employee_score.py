# -*- coding: utf-8 -*-
from odoo import models, fields, api

STARTING_SCORE = 100


class CctvEmployeeMonthlyScore(models.Model):
    _name = 'cctv.employee.monthly.score'
    _description = 'Employee Monthly Discipline/Safety/Attendance/Compliance Score'
    _order = 'year desc, month desc, compliance_score desc'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', required=True, index=True)
    year = fields.Integer(required=True)
    month = fields.Integer(required=True)   # 1-12
    period_label = fields.Char(compute='_compute_period_label', store=True)

    discipline_score = fields.Integer(default=STARTING_SCORE)
    safety_score = fields.Integer(default=STARTING_SCORE)
    attendance_score = fields.Integer(default=STARTING_SCORE)
    compliance_score = fields.Integer(default=STARTING_SCORE)
    total_violations = fields.Integer()

    _sql_constraints = [
        ('employee_period_uniq', 'unique(employee_id, year, month)', 'Only one score row per employee per month.'),
    ]

    @api.depends('year', 'month')
    def _compute_period_label(self):
        for rec in self:
            rec.period_label = f"{rec.year}-{rec.month:02d}" if rec.year and rec.month else ''

    @api.model
    def cron_build_monthly_scores(self):
        """Recomputes this month's scores from approved/processed violations
        (not merely 'new'/rejected ones - a violation only affects score once
        it's been through at least manager review, matching the module's
        human-in-the-loop philosophy)."""
        now = fields.Datetime.now()
        year, month = now.year, now.month
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month == 12:
            month_end = month_start.replace(year=year + 1, month=1)
        else:
            month_end = month_start.replace(month=month + 1)

        Violation = self.env['cctv.violation']
        violations = Violation.search([
            ('occurred_at', '>=', month_start), ('occurred_at', '<', month_end),
            ('state', 'not in', ('new', 'manager_review', 'manager_rejected', 'hr_rejected')),
        ])

        by_employee = {}
        for v in violations:
            by_employee.setdefault(v.employee_id.id, []).append(v)

        for employee_id, vlist in by_employee.items():
            scores = {'discipline': STARTING_SCORE, 'safety': STARTING_SCORE,
                      'attendance': STARTING_SCORE, 'compliance': STARTING_SCORE}
            for v in vlist:
                cat = v.rule_id.score_category
                pts = v.rule_id.score_points
                if cat in scores:
                    scores[cat] = max(0, scores[cat] - pts)

            vals = {
                'employee_id': employee_id, 'year': year, 'month': month,
                'discipline_score': scores['discipline'], 'safety_score': scores['safety'],
                'attendance_score': scores['attendance'], 'compliance_score': scores['compliance'],
                'total_violations': len(vlist),
            }
            existing = self.search([('employee_id', '=', employee_id), ('year', '=', year), ('month', '=', month)],
                                    limit=1)
            if existing:
                existing.write(vals)
            else:
                self.create(vals)
