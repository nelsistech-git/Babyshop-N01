# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
PLM Stage Gate (SRS sections 4, 12, 18, 46) — garment.plm.stage.gate.

One line per stage of the journey: Concept -> Design -> Sourcing ->
Sampling -> Costing -> Approval -> Production Handover. Tracks planned vs.
actual dates (SLA / target-date tracking) and holds the gate sign-off
approvals (garment.plm.gate.approval) required to pass the gate.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentPlmStageGate(models.Model):
    _name = 'garment.plm.stage.gate'
    _description = 'Garment PLM Stage Gate'
    _inherit = ['mail.thread']
    _order = 'project_id, sequence, id'

    project_id = fields.Many2one('garment.plm.project', string='PLM Project', required=True, ondelete='cascade')
    style_id = fields.Many2one(related='project_id.style_id', string='Style', store=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)

    stage = fields.Selection([
        ('concept', 'Concept'),
        ('design', 'Design'),
        ('sourcing', 'Sourcing'),
        ('sampling', 'Sampling'),
        ('costing', 'Costing'),
        ('approval', 'Approval'),
        ('production_handover', 'Production Handover'),
    ], string='Stage', required=True)

    responsible_id = fields.Many2one('res.users', string='Responsible')
    team_role = fields.Selection([
        ('merchandiser', 'Merchandiser'),
        ('designer', 'Designer'),
        ('pattern_maker', 'Pattern Maker'),
        ('sample_coordinator', 'Sample Coordinator'),
        ('ie_engineer', 'IE Engineer'),
        ('quality_team', 'Quality Team'),
        ('production_team', 'Production Team'),
    ], string='Owning Role')

    planned_start_date = fields.Date(string='Planned Start')
    planned_end_date = fields.Date(string='Planned End (SLA Target)')
    actual_start_date = fields.Date(string='Actual Start')
    actual_end_date = fields.Date(string='Actual End')
    sla_days = fields.Integer(string='SLA (Days)', help='Target number of days allotted to this stage.')

    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
        ('skipped', 'Skipped'),
    ], string='Status', default='pending', tracking=True)

    delay_days = fields.Integer(string='Delay (Days)', compute='_compute_delay', store=True)
    is_delayed = fields.Boolean(string='Delayed', compute='_compute_delay', store=True)

    gate_approval_ids = fields.One2many('garment.plm.gate.approval', 'gate_id', string='Gate Sign-Offs')

    # FIXED: Added store=True to match all_approved field
    approval_count = fields.Integer(string='Sign-Offs', compute='_compute_approval_state', store=True)
    all_approved = fields.Boolean(string='All Sign-Offs Complete', compute='_compute_approval_state', store=True)

    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', related='project_id.company_id', store=True, readonly=True)

    @api.depends('planned_end_date', 'actual_end_date', 'status')
    def _compute_delay(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.planned_end_date and rec.actual_end_date:
                days = (rec.actual_end_date - rec.planned_end_date).days
            elif rec.planned_end_date and rec.status not in ('completed', 'skipped') and today > rec.planned_end_date:
                days = (today - rec.planned_end_date).days
            else:
                days = 0
            rec.delay_days = max(days, 0)
            rec.is_delayed = rec.delay_days > 0 and rec.status not in ('completed', 'skipped')

    @api.depends('gate_approval_ids.status')
    def _compute_approval_state(self):
        for rec in self:
            rec.approval_count = len(rec.gate_approval_ids)
            rec.all_approved = bool(rec.gate_approval_ids) and all(
                a.status == 'approved' for a in rec.gate_approval_ids)

    def action_start(self):
        self.write({'status': 'in_progress', 'actual_start_date': fields.Date.context_today(self)})

    def action_complete(self):
        for rec in self:
            if rec.gate_approval_ids and not rec.all_approved:
                raise UserError(_(
                    'Stage "%s" still has pending sign-offs. All gate approvals must be Approved '
                    'before this stage can be marked Completed.') % dict(rec._fields['stage'].selection).get(
                    rec.stage))
            rec.write({'status': 'completed', 'actual_end_date': fields.Date.context_today(rec)})