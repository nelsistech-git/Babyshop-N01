# -*- coding: utf-8 -*-
"""Survey assignment wizard (SRS 14)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class GcErmSurveyAssignWizard(models.TransientModel):
    _name = 'gc.erm.survey.assign.wizard'
    _description = 'GC ERM Survey Assignment'

    survey_id = fields.Many2one(
        'gc.erm.survey', string='Survey', required=True, readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Client', related='survey_id.partner_id',
        readonly=True)
    team_id = fields.Many2one(
        'gc.erm.team', string='Technical Team',
        domain="[('team_type', 'in', ('technical', 'both'))]")
    engineer_id = fields.Many2one(
        'res.users', string='Survey Engineer', required=True,
        domain="[('share', '=', False)]")
    survey_date = fields.Date(
        string='Survey Date', required=True,
        default=fields.Date.context_today)
    deadline = fields.Date(string='Deadline', required=True)
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1', required=True)
    note = fields.Text(string='Instructions')

    @api.onchange('team_id')
    def _onchange_team_id(self):
        for wizard in self:
            if wizard.team_id and not wizard.engineer_id:
                wizard.engineer_id = wizard.team_id.leader_id
            if wizard.team_id:
                return {'domain': {'engineer_id': [
                    ('id', 'in', (wizard.team_id.member_ids
                                  | wizard.team_id.leader_id).ids)]}}
            return {'domain': {'engineer_id': [('share', '=', False)]}}

    @api.onchange('survey_date')
    def _onchange_survey_date(self):
        for wizard in self:
            if wizard.survey_date and not wizard.deadline:
                days = self.env['ir.config_parameter'].sudo().get_param(
                    'gc_erm.sla_survey_days', '2')
                try:
                    days = int(float(days))
                except (TypeError, ValueError):
                    days = 2
                wizard.deadline = fields.Date.add(wizard.survey_date, days=days)

    @api.constrains('survey_date', 'deadline')
    def _check_dates(self):
        for wizard in self:
            if wizard.deadline < wizard.survey_date:
                raise ValidationError(_(
                    'The deadline cannot be earlier than the survey date.'))

    def action_assign(self):
        self.ensure_one()
        survey = self.survey_id
        if survey.state not in ('draft', 'assigned'):
            raise UserError(_(
                'Survey %s can no longer be assigned.', survey.name))
        survey.write({
            'team_id': self.team_id.id,
            'engineer_id': self.engineer_id.id,
            'survey_date': self.survey_date,
            'deadline': self.deadline,
            'priority': self.priority,
            'assigned_date': fields.Datetime.now(),
        })
        survey._gc_transition(
            'assigned',
            comment=_('Assigned to %(engineer)s, deadline %(deadline)s.',
                      engineer=self.engineer_id.name, deadline=self.deadline))
        survey._gc_schedule_activity(
            self.engineer_id,
            summary=_('Complete survey %s', survey.name),
            note=self.note or _('Client: %s', survey.partner_id.display_name),
            days=max((self.deadline - fields.Date.context_today(self)).days, 0))
        survey._gc_notify(
            'gc_erm_lead_to_billing.mail_template_gc_survey_assignment')
        if self.note:
            survey.message_post(body=self.note)
        return {'type': 'ir.actions.act_window_close'}
