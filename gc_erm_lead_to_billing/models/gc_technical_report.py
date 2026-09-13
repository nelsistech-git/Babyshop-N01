# -*- coding: utf-8 -*-
"""Technical report and its hand-over to Sales (SRS 20 / 21)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .gc_survey import FEASIBILITY_SELECTION

TR_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('review', 'Technical Review'),
    ('submitted', 'Submitted to Sales'),
    ('rejected', 'Rejected'),
    ('cancelled', 'Cancelled'),
]


class GcErmTechnicalReport(models.Model):
    _name = 'gc.erm.technical.report'
    _description = 'GC ERM Technical Report'
    _inherit = ['gc.erm.document.mixin']
    _order = 'report_date desc, id desc'

    _gc_sequence_code = 'gc.erm.technical.report'
    _gc_sla_parameter = 'gc_erm.sla_technical_report_days'
    _gc_closed_states = ('submitted', 'rejected', 'cancelled')

    state = fields.Selection(
        TR_STATE_SELECTION, string='Status', default='draft', required=True,
        copy=False, tracking=True, index=True, group_expand='_group_expand_state')

    # ------------------------------------------------------------------
    # Header (SRS 20)
    # ------------------------------------------------------------------
    survey_id = fields.Many2one(
        'gc.erm.survey', string='Survey', required=True, ondelete='restrict',
        index=True, tracking=True)
    lead_id = fields.Many2one(
        'gc.erm.lead', string='Lead', related='survey_id.lead_id', store=True,
        index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, index=True)
    engineer_id = fields.Many2one(
        'res.users', string='Technical Engineer', required=True,
        default=lambda self: self.env.user, tracking=True, index=True)
    salesperson_id = fields.Many2one(
        'res.users', string='Salesperson', related='survey_id.salesperson_id',
        store=True)
    survey_date = fields.Date(
        string='Survey Date', related='survey_id.survey_date', store=True)
    report_date = fields.Date(
        string='Report Date', default=fields.Date.context_today, required=True)

    feasibility = fields.Selection(
        FEASIBILITY_SELECTION, string='Feasibility', required=True,
        tracking=True, index=True)
    technical_findings = fields.Html(string='Technical Findings', sanitize=True)
    boq_id = fields.Many2one(
        'gc.erm.boq', string='BOQ', tracking=True, index=True,
        domain="[('survey_id', '=', survey_id), ('state', '!=', 'cancelled')]")
    boq_state = fields.Selection(related='boq_id.state', string='BOQ Status')
    total_cost = fields.Monetary(
        string='Total Cost', related='boq_id.total_cost', store=True,
        currency_field='currency_id')
    amount_untaxed = fields.Monetary(
        string='Selling Price (untaxed)', related='boq_id.amount_untaxed',
        store=True, currency_field='currency_id')
    amount_total = fields.Monetary(
        string='Total Selling Price', related='boq_id.amount_total', store=True,
        currency_field='currency_id')
    margin_percentage = fields.Float(
        string='Margin (%)', related='boq_id.margin_percentage', store=True)

    implementation_timeline = fields.Char(
        string='Implementation Timeline',
        help='For example "10 working days from material availability".')
    implementation_days = fields.Integer(string='Estimated Duration (days)')
    required_equipment = fields.Text(string='Required Equipment')
    installation_scope = fields.Html(string='Installation Scope', sanitize=True)
    technical_risks = fields.Text(string='Technical Risks')
    recommendations = fields.Html(string='Recommendations', sanitize=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'gc_tr_attachment_rel', 'report_id', 'attachment_id',
        string='Attachments')

    review_required = fields.Boolean(
        string='Technical Manager Review Required',
        default=lambda self: self._default_review_required(),
        help='When enabled the report must be approved by a Technical Manager '
             'before it reaches Sales (SRS 59).')
    reviewed_by_id = fields.Many2one(
        'res.users', string='Reviewed By', readonly=True, copy=False)
    reviewed_date = fields.Datetime(string='Reviewed On', readonly=True, copy=False)

    proposal_ids = fields.One2many(
        'gc.erm.proposal', 'technical_report_id', string='Proposals')
    proposal_count = fields.Integer(compute='_compute_proposal_count')

    # ------------------------------------------------------------------
    # Defaults / compute
    # ------------------------------------------------------------------
    @api.model
    def _default_review_required(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'gc_erm.technical_review_required', 'False') in ('True', 'true', '1')

    @api.model
    def _group_expand_state(self, states, domain, order=None):
        return [key for key, _label in TR_STATE_SELECTION]

    @api.depends('proposal_ids')
    def _compute_proposal_count(self):
        for report in self:
            report.proposal_count = len(report.proposal_ids)

    @api.onchange('survey_id')
    def _onchange_survey_id(self):
        for report in self:
            survey = report.survey_id
            if not survey:
                continue
            report.partner_id = survey.partner_id
            report.engineer_id = survey.engineer_id or self.env.user
            report.feasibility = survey.feasibility
            report.technical_findings = survey.technical_remarks
            report.required_equipment = survey.equipment_requirement
            boq = survey.boq_ids.filtered(
                lambda b: b.state in ('draft', 'confirmed'))[:1]
            report.boq_id = boq

    # ------------------------------------------------------------------
    # Validation (SRS 66 / BR-004)
    # ------------------------------------------------------------------
    def _check_submit_ready(self):
        self.ensure_one()
        if not self.feasibility:
            raise UserError(_(
                'The feasibility is mandatory on technical report %s.', self.name))
        if self.feasibility == 'not_feasible':
            if not self.survey_id.feasibility_reason and not self.technical_risks:
                raise UserError(_(
                    'A "Not Feasible" report must explain the reason in the '
                    'technical risks or in the survey.'))
            return True
        if not self.boq_id:
            raise UserError(_(
                'Technical costing must be completed before the technical '
                'report %s can be submitted.', self.name))
        if not self.boq_id.line_ids:
            raise UserError(_(
                'BOQ %s has no lines. Technical costing must be completed '
                'before submission.', self.boq_id.name))
        if self.boq_id.state == 'draft':
            raise UserError(_(
                'Confirm BOQ %s before submitting the technical report.',
                self.boq_id.name))
        return True

    # ------------------------------------------------------------------
    # Workflow (SRS 20 / 21)
    # ------------------------------------------------------------------
    def action_submit(self):
        for report in self:
            if report.state not in ('draft', 'rejected'):
                raise UserError(_(
                    'Only a draft technical report can be submitted.'))
            report._gc_require_group(
                'gc_erm_lead_to_billing.group_gc_technical_user',
                _('submit technical reports'))
            report._check_submit_ready()
            if report.review_required:
                report._gc_transition(
                    'review', comment=_('Sent for technical manager review.'),
                    allowed_from=('draft', 'rejected'),
                    extra_vals={
                        'submitted_by_id': self.env.user.id,
                        'submitted_date': fields.Datetime.now(),
                    })
                manager = report._gc_first_user_in_group(
                    'gc_erm_lead_to_billing.group_gc_technical_manager')
                if manager:
                    report._gc_schedule_activity(
                        manager,
                        summary=_('Review Technical Report %s', report.name),
                        days=int(report._gc_sla_days() or 1))
            else:
                report._do_submit_to_sales()
        return True

    def action_approve(self):
        """Technical manager approval when review is enabled."""
        for report in self:
            if report.state != 'review':
                raise UserError(_(
                    'Only a report under technical review can be approved.'))
            report._gc_require_group(
                'gc_erm_lead_to_billing.group_gc_technical_manager',
                _('approve technical reports'))
            report._gc_check_not_self_approval(report.engineer_id)
            report.write({
                'reviewed_by_id': self.env.user.id,
                'reviewed_date': fields.Datetime.now(),
            })
            report._do_submit_to_sales()
        return True

    def _do_submit_to_sales(self):
        """SRS 21 -- the report becomes available in Sales."""
        self.ensure_one()
        self._gc_transition(
            'submitted', comment=_('Technical report submitted to Sales.'),
            extra_vals={
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
                'submitted_by_id': self.submitted_by_id.id or self.env.user.id,
                'submitted_date': self.submitted_date or fields.Datetime.now(),
            })
        # SRS 19 -- lock the costing once the report is submitted.
        if self.boq_id:
            self.boq_id.action_lock()
        self.survey_id.action_mark_submitted()
        if self.salesperson_id:
            self._gc_schedule_activity(
                self.salesperson_id,
                summary=_('Prepare proposal for %s', self.partner_id.display_name),
                note=_('Technical report %s has been submitted. You can now '
                       'prepare the commercial proposal.', self.name),
                days=1)
        self._gc_notify(
            'gc_erm_lead_to_billing.mail_template_gc_technical_report_submitted')
        self.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def _gc_apply_rejection(self, reason):
        self.ensure_one()
        self._gc_require_group(
            'gc_erm_lead_to_billing.group_gc_technical_manager',
            _('reject technical reports'))
        self._gc_transition(
            'rejected', comment=reason, allowed_from=('review', 'submitted'),
            extra_vals={
                'rejected_by_id': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
                'rejection_reason': reason,
            })
        self._gc_schedule_activity(
            self.engineer_id, summary=_('Rework Technical Report %s', self.name),
            note=reason, days=1)
        return True

    def _gc_apply_revision(self, reason):
        self.ensure_one()
        self._gc_transition(
            'draft', comment=_('Revision requested: %s', reason),
            allowed_from=('review', 'submitted'),
            extra_vals={'revision_reason': reason})
        self._gc_schedule_activity(
            self.engineer_id, summary=_('Revise Technical Report %s', self.name),
            note=reason, days=1)
        return True

    def action_reset_draft(self):
        for report in self:
            if report.state not in ('rejected', 'cancelled'):
                raise UserError(_(
                    'Only a rejected or cancelled report can be reset to draft.'))
            report._gc_transition('draft', comment=_('Reset to draft.'))
        return True

    def action_cancel(self):
        for report in self:
            if report.proposal_ids.filtered(
                    lambda p: p.state not in ('draft', 'cancelled')):
                raise UserError(_(
                    'Technical report %s is used by an active proposal.',
                    report.name))
            report._gc_transition('cancelled', comment=_('Report cancelled.'))
        return True

    # ------------------------------------------------------------------
    # Proposal creation (SRS 22)
    # ------------------------------------------------------------------
    def action_create_proposal(self):
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError(_(
                'The technical report must be submitted to Sales before a '
                'proposal can be prepared.'))
        if self.feasibility == 'not_feasible':
            raise UserError(_(
                'The site was declared "Not Feasible". A proposal cannot be '
                'prepared for %s.', self.partner_id.display_name))
        proposal = self.env['gc.erm.proposal'].create(self._prepare_proposal_vals())
        return {
            'type': 'ir.actions.act_window',
            'name': _('Proposal'),
            'res_model': 'gc.erm.proposal',
            'res_id': proposal.id,
            'view_mode': 'form',
        }

    def _prepare_proposal_vals(self):
        self.ensure_one()
        survey = self.survey_id
        lines = []
        for line in self.boq_id.line_ids:
            lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.quantity,
                'uom_id': line.uom_id.id,
                'price_unit': line.sales_price,
                'discount': line.discount,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
                'boq_line_id': line.id,
            }))
        return {
            'lead_id': self.lead_id.id,
            'survey_id': survey.id,
            'technical_report_id': self.id,
            'boq_id': self.boq_id.id,
            'partner_id': self.partner_id.id,
            'contact_id': survey.contact_id.id,
            'salesperson_id': self.salesperson_id.id or self.env.user.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'contract_duration': survey.contract_duration,
            'expected_golive_date': survey.expected_golive_date,
            'technical_scope': self.installation_scope,
            'global_discount': self.boq_id.global_discount,
            'line_ids': lines,
        }

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_boq(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gc.erm.boq',
            'res_id': self.boq_id.id,
            'view_mode': 'form',
        }

    def action_view_survey(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gc.erm.survey',
            'res_id': self.survey_id.id,
            'view_mode': 'form',
        }

    def action_view_proposals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Proposals'),
            'res_model': 'gc.erm.proposal',
            'view_mode': 'tree,form',
            'domain': [('technical_report_id', '=', self.id)],
        }

    @api.depends('name', 'partner_id')
    def _compute_display_name(self):
        for report in self:
            report.display_name = '%s - %s' % (
                report.name, report.partner_id.name) if report.partner_id \
                else report.name
