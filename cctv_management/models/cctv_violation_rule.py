# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CctvViolationRule(models.Model):
    _name = 'cctv.violation.rule'
    _description = 'Employee Violation Rule (fine/discipline matrix)'
    _order = 'category, violation_type'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    category = fields.Selection([
        ('attendance', 'Attendance Violation'),
        ('discipline', 'Workplace Discipline'),
        ('safety', 'Safety Violation'),
        ('security', 'Security Violation'),
        ('production', 'Production Violation'),
    ], required=True)

    # Matches cctv.event.behavior_type values so AI detections can drive this
    # automatically. Add more mappings here as you extend behavior_type.
    violation_type = fields.Selection([
        ('late_arrival', 'Late Arrival'),
        ('early_departure', 'Early Departure'),
        ('unauthorized_break', 'Unauthorized Absence / Extended Break'),
        ('left_station', 'Leaving Workstation'),
        ('sleeping', 'Sleeping During Duty'),
        ('phone_usage', 'Excessive Mobile Phone Use'),
        ('smoking', 'Smoking in Prohibited Area'),
        ('personal_visitor', 'Unauthorized Visitor'),
        ('argument', 'Unauthorized Meeting / Gossiping / Conflict'),
        ('idle', 'Repeated Idle Time'),
        ('no_helmet', 'No Safety Helmet'),
        ('no_vest', 'No Safety Vest'),
        ('no_mask', 'No Mask'),
        ('no_uniform', 'No Uniform / Safety Shoes'),
        ('restricted_entry', 'Restricted Area Entry'),
        ('unauthorized_entry', 'Unauthorized Warehouse Access'),
        ('trespassing', 'Tailgating / Security Gate Violation'),
        ('task_delay', 'Task Abandonment / Production Delay'),
        ('unprofessional_conduct', 'Quality Negligence / Process Non-Compliance'),
    ], required=True)

    # Scope - leave any blank to apply company/branch/department/role-wide
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    office_id = fields.Many2one('cctv.office', string='Branch/Site (optional scope)')
    department_id = fields.Many2one('cctv.department', string='Department/Zone (optional scope)')
    job_id = fields.Many2one('hr.job', string='Designation (optional scope)')

    reset_period_months = fields.Integer(
        default=12, help='Offense count resets after this many months with no repeat of the same violation type')
    score_category = fields.Selection([
        ('discipline', 'Discipline Score'), ('safety', 'Safety Score'),
        ('attendance', 'Attendance Score'), ('compliance', 'Compliance Score'),
    ], required=True, default='compliance')
    score_points = fields.Integer(default=5, help='Points deducted from the employee\'s score per occurrence')

    tier_ids = fields.One2many('cctv.violation.rule.tier', 'rule_id', string='Offense Tiers')

    def get_tier_for_offense(self, offense_number):
        """Returns the tier line to apply for the Nth offense (1-indexed),
        capping at the highest configured tier for repeat/4th+ offenses."""
        self.ensure_one()
        tiers = self.tier_ids.sorted('sequence')
        if not tiers:
            return None
        idx = min(offense_number, len(tiers)) - 1
        return tiers[idx]


class CctvViolationRuleTier(models.Model):
    _name = 'cctv.violation.rule.tier'
    _description = 'Violation Rule Offense Tier'
    _order = 'sequence'

    rule_id = fields.Many2one('cctv.violation.rule', required=True, ondelete='cascade')
    sequence = fields.Integer(required=True, help='1 = first offense, 2 = second offense, etc. '
                                                    'The highest sequence covers that offense and all beyond it.')
    action_type = fields.Selection([
        ('warning', 'Warning'),
        ('written_warning', 'Written Warning'),
        ('fine', 'Fine'),
        ('hr_meeting', 'HR Meeting'),
        ('suspension_review', 'Suspension Review'),
        ('disciplinary_review', 'Disciplinary Review'),
        ('investigation', 'Investigation'),
        ('hr_action', 'HR Action'),
        ('termination_review', 'Termination Review'),
    ], required=True, default='warning')
    fine_amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    notes = fields.Char()
