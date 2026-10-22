# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with AI Workforce
Analytics (SRS sections 56-58): employee retention/attrition risk,
skill-gap training recommendations, and productivity trend analysis.
Rule-based, transparent, degrades gracefully.
"""
import logging
from datetime import date, timedelta

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineHrExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Employee Retention Risk (SRS section 57)
    # ------------------------------------------------------------------
    def predict_employee_retention_risk(self, employee):
        score = 0
        reasons = []
        today = date.today()

        recent_attendance = employee.attendance_ids.filtered(
            lambda a: a.attendance_date and a.attendance_date >= today - timedelta(days=60))
        if recent_attendance:
            absences = recent_attendance.filtered(lambda a: a.status == 'absent')
            absence_rate = len(absences) / len(recent_attendance) * 100.0
            if absence_rate > 15:
                score += 25
                reasons.append('Absence rate over the last 60 days is high (%.0f%%).' % absence_rate)

        open_discipline = employee.discipline_ids.filtered(lambda d: d.status == 'open')
        if open_discipline:
            score += min(25, len(open_discipline) * 10)
            reasons.append('%d open disciplinary record(s).' % len(open_discipline))

        recent_performance = employee.performance_ids.sorted('review_date', reverse=True)[:1]
        if recent_performance and recent_performance.rating in ('below_average', 'poor'):
            score += 20
            reasons.append('Most recent performance rating: %s.' % recent_performance.rating)

        if employee.employment_type == 'probation' and employee.joining_date and \
                (today - employee.joining_date).days > 180:
            score += 15
            reasons.append('Still on probation after 180+ days since joining — review confirmation status.')

        pending_advance = sum(employee.payroll_ids.mapped('advance_balance'))
        pending_advance += sum(employee.loan_ids.filtered(lambda l: l.status == 'disbursed').mapped('outstanding_balance'))
        if pending_advance and pending_advance > 0:
            score += 10
            reasons.append('Outstanding advance/loan balance of %.2f — financial stress indicator.' % pending_advance)

        open_complaints = employee.complaint_ids.filtered(lambda c: c.status not in ('resolved', 'closed'))
        if open_complaints:
            score += min(15, len(open_complaints) * 8)
            reasons.append('%d unresolved complaint(s) on file.' % len(open_complaints))

        score = max(0, min(100, score))
        level = 'HIGH' if score >= 50 else 'MEDIUM' if score >= 25 else 'LOW'
        note = 'Retention Risk: %s (score %d/100).' % (level, score)
        if reasons:
            note += '\n' + '\n'.join('- %s' % r for r in reasons)
        else:
            note += '\nNo significant retention risk factors detected.'
        return note

    # ------------------------------------------------------------------
    # AI Skill Gap / Training Recommendation (SRS section 58)
    # ------------------------------------------------------------------
    def suggest_skill_gap_training(self, employee):
        low_skills = employee.skill_matrix_ids.filtered(lambda s: s.proficiency_level in ('1', '2'))
        if not low_skills:
            return 'No low-proficiency skills on file — no training gap detected.'
        ops = ', '.join(dict(low_skills[0]._fields['operation'].selection).get(s.operation, s.operation)
                         for s in low_skills)
        return 'Suggested training focus areas (proficiency level 1-2): %s.' % ops

    # ------------------------------------------------------------------
    # AI Productivity Trend Analysis (SRS section 56 - Workforce Analytics)
    # ------------------------------------------------------------------
    def analyze_department_productivity(self, department):
        employees = self.env['garment.hr.employee'].search([('department_id', '=', department.id)])
        if not employees:
            return 'No employees in this department.'

        reviews = employees.mapped('performance_ids').filtered(lambda p: p.overall_score)
        if not reviews:
            return 'No performance reviews on file yet for this department.'

        avg_score = sum(reviews.mapped('overall_score')) / len(reviews)
        note = 'Average performance score across %d review(s) in this department: %.1f%%.' % (
            len(reviews), avg_score)
        if avg_score < 60:
            note += ' Below the "average" threshold — review training and supervision support.'
        return note
