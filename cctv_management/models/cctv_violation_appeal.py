# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class CctvViolationAppeal(models.Model):
    _name = 'cctv.violation.appeal'
    _description = 'Employee Violation Appeal'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    violation_id = fields.Many2one('cctv.violation', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='violation_id.employee_id', store=True)
    employee_explanation = fields.Text(required=True)
    supporting_document = fields.Binary(attachment=True, string='Supporting Document')
    supporting_document_name = fields.Char()

    state = fields.Selection([
        ('submitted', 'Submitted'),
        ('supervisor_review', 'Supervisor Review'),
        ('hr_decision', 'HR Decision'),
        ('closed', 'Closed'),
    ], default='submitted', required=True, tracking=True)

    supervisor_id = fields.Many2one('res.users', string='Reviewing Supervisor')
    supervisor_notes = fields.Text()
    hr_decision_maker_id = fields.Many2one('res.users', string='HR Decision Maker')
    decision = fields.Selection([
        ('upheld', 'Violation Upheld'),
        ('overturned', 'Violation Overturned'),
        ('reduced', 'Fine/Action Reduced'),
    ])
    decision_notes = fields.Text()

    def action_move_to_supervisor_review(self):
        self.write({'state': 'supervisor_review', 'supervisor_id': self.env.user.id})

    def action_move_to_hr_decision(self):
        self.write({'state': 'hr_decision'})

    def action_close(self, decision, decision_notes=None):
        self.ensure_one()
        if self.state != 'hr_decision':
            raise UserError('Move the appeal to HR Decision before closing it.')
        self.write({'state': 'closed', 'decision': decision, 'decision_notes': decision_notes,
                     'hr_decision_maker_id': self.env.user.id})
        violation = self.violation_id
        if decision == 'overturned':
            violation.state = 'closed'
        elif decision == 'reduced':
            violation.state = 'hr_review'   # send back for HR to set the reduced fine/action
        else:   # upheld
            violation.state = 'approved'
