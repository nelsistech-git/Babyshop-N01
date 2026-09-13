# -*- coding: utf-8 -*-
"""Revisit management wizard (SRS 40)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class GcErmRevisitWizard(models.TransientModel):
    _name = 'gc.erm.revisit.wizard'
    _description = 'GC ERM Installation Revisit'

    installation_id = fields.Many2one(
        'gc.erm.installation', string='Installation', required=True,
        readonly=True)
    work_order_id = fields.Many2one(
        'gc.erm.work.order', string='Work Order',
        related='installation_id.work_order_id', readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        related='installation_id.partner_id', readonly=True)

    reason = fields.Text(string='Reason', required=True)
    required_action = fields.Text(string='Required Action', required=True)
    next_visit_date = fields.Date(
        string='Next Visit Date', required=True,
        default=lambda self: fields.Date.add(
            fields.Date.context_today(self), days=1))
    engineer_id = fields.Many2one(
        'res.users', string='Assigned Engineer', required=True,
        domain="[('share', '=', False)]")
    team_id = fields.Many2one(
        'gc.erm.team', string='Team',
        domain="[('team_type', 'in', ('implementation', 'both'))]")

    @api.onchange('installation_id')
    def _onchange_installation_id(self):
        for wizard in self:
            installation = wizard.installation_id
            if not installation:
                continue
            wizard.engineer_id = installation.next_engineer_id \
                or installation.engineer_id
            wizard.team_id = installation.team_id
            wizard.reason = installation.failure_reason
            wizard.required_action = installation.required_action
            if installation.next_visit_date:
                wizard.next_visit_date = installation.next_visit_date

    @api.constrains('next_visit_date')
    def _check_next_visit_date(self):
        for wizard in self:
            if wizard.next_visit_date < fields.Date.context_today(wizard):
                raise ValidationError(_(
                    'The next visit date cannot be in the past.'))

    def action_create_revisit(self):
        """Close the current visit and open a new installation record."""
        self.ensure_one()
        installation = self.installation_id
        if installation.state not in ('in_progress', 'submitted'):
            raise UserError(_(
                'A revisit can only be requested from an ongoing or reported '
                'installation.'))
        installation.write({
            'result': installation.result or 'revisit',
            'failure_reason': self.reason,
            'required_action': self.required_action,
            'next_visit_date': self.next_visit_date,
            'next_engineer_id': self.engineer_id.id,
            'end_time': installation.end_time or fields.Datetime.now(),
        })
        installation._gc_transition(
            'revisit',
            comment=_('Revisit required: %s', self.reason))
        # SRS 40 -- previous reports remain preserved; a new visit is created.
        revisit = self.env['gc.erm.installation'].create({
            'work_order_id': installation.work_order_id.id,
            'partner_id': installation.partner_id.id,
            'company_id': installation.company_id.id,
            'currency_id': installation.currency_id.id,
            'team_id': (self.team_id or installation.team_id).id,
            'engineer_id': self.engineer_id.id,
            'installation_date': self.next_visit_date,
            'revisit_of_id': installation.id,
            'visit_number': installation.visit_number + 1,
            'checklist_template_id': installation.checklist_template_id.id,
            'remarks': _('Revisit of %(name)s. Required action: %(action)s',
                         name=installation.name, action=self.required_action),
        })
        work_order = installation.work_order_id
        if work_order.state == 'install_done':
            work_order.with_context(gc_bypass_lock=True)._gc_transition(
                'installing', comment=_('Revisit scheduled.'))
        revisit._gc_schedule_activity(
            self.engineer_id,
            summary=_('Revisit installation %s', revisit.name),
            note=self.required_action,
            days=max((self.next_visit_date
                      - fields.Date.context_today(self)).days, 0))
        installation.message_post(body=_(
            'Revisit %(new)s scheduled on %(date)s for %(engineer)s.',
            new=revisit.name, date=self.next_visit_date,
            engineer=self.engineer_id.name))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Revisit'),
            'res_model': 'gc.erm.installation',
            'res_id': revisit.id,
            'view_mode': 'form',
        }
