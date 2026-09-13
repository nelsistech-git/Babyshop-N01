# -*- coding: utf-8 -*-
"""Survey generation, assignment and technical survey (SRS 12 - 16)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

SURVEY_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('assigned', 'Assigned'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('submitted', 'Submitted'),
    ('cancelled', 'Cancelled'),
]

FEASIBILITY_SELECTION = [
    ('feasible', 'Feasible'),
    ('conditional', 'Conditionally Feasible'),
    ('not_feasible', 'Not Feasible'),
    ('investigate', 'Further Investigation Required'),
]

AVAILABILITY_SELECTION = [
    ('yes', 'Available'),
    ('partial', 'Partially Available'),
    ('no', 'Not Available'),
]

COMPLEXITY_SELECTION = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
]


class GcErmSurvey(models.Model):
    _name = 'gc.erm.survey'
    _description = 'GC ERM Customer / Technical Survey'
    _inherit = ['gc.erm.document.mixin']
    _order = 'priority desc, survey_date desc, id desc'

    _gc_sequence_code = 'gc.erm.survey'
    _gc_sla_parameter = 'gc_erm.sla_survey_days'
    _gc_closed_states = ('completed', 'submitted', 'cancelled')

    state = fields.Selection(
        SURVEY_STATE_SELECTION, string='Status', default='draft', required=True,
        copy=False, tracking=True, index=True, group_expand='_group_expand_state')

    # ------------------------------------------------------------------
    # Origin (SRS 12)
    # ------------------------------------------------------------------
    lead_id = fields.Many2one(
        'gc.erm.lead', string='Lead', required=True, ondelete='restrict',
        index=True, tracking=True)
    lead_state = fields.Selection(related='lead_id.state', string='Lead Status')
    salesperson_id = fields.Many2one(
        'res.users', string='Salesperson', tracking=True, index=True)

    # ------------------------------------------------------------------
    # A. Client information (SRS 13.A)
    # ------------------------------------------------------------------
    partner_id = fields.Many2one(
        'res.partner', string='Client', required=True, tracking=True, index=True)
    contact_id = fields.Many2one('res.partner', string='Contact')
    street = fields.Char(string='Client Address')
    street2 = fields.Char(string='Address Line 2')
    city = fields.Char(string='City')
    district = fields.Char(string='District')
    area = fields.Char(string='Area')
    zip_code = fields.Char(string='ZIP')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    gps_latitude = fields.Float(string='GPS Latitude', digits=(10, 7))
    gps_longitude = fields.Float(string='GPS Longitude', digits=(10, 7))
    map_url = fields.Char(string='Map Link', compute='_compute_map_url')
    service_location = fields.Char(string='Service Location')

    # ------------------------------------------------------------------
    # B. Contact details (SRS 13.B)
    # ------------------------------------------------------------------
    contact_person = fields.Char(string='Contact Person Name')
    contact_designation = fields.Char(string='Designation')
    contact_phone = fields.Char(string='Phone Number')
    contact_phone_alt = fields.Char(string='Alternative Phone')
    contact_email = fields.Char(string='Mail ID')

    # ------------------------------------------------------------------
    # C / D. Required service and details (SRS 13.C / 13.D)
    # ------------------------------------------------------------------
    service_line_ids = fields.One2many(
        'gc.erm.survey.line', 'survey_id', string='Required Services', copy=True)
    service_ids = fields.Many2many(
        'gc.erm.service.catalog', string='Services',
        compute='_compute_service_ids', store=True)
    expected_golive_date = fields.Date(string='Expected Go-Live Date')
    contract_duration = fields.Integer(string='Contract Duration (months)')

    # ------------------------------------------------------------------
    # E. Additional information (SRS 13.E)
    # ------------------------------------------------------------------
    existing_isp = fields.Char(string='Existing ISP')
    special_requirements = fields.Text(string='Special Requirements')
    requirement_note = fields.Html(string='Requirement Note', sanitize=True)
    remarks = fields.Text(string='Remarks')
    note = fields.Text(string='Internal Notes')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'gc_survey_attachment_rel', 'survey_id', 'attachment_id',
        string='Attachments (LOI, Layout, Location Map)')

    # ------------------------------------------------------------------
    # Assignment (SRS 14)
    # ------------------------------------------------------------------
    team_id = fields.Many2one(
        'gc.erm.team', string='Technical Team', tracking=True,
        domain="[('team_type', 'in', ('technical', 'both'))]")
    engineer_id = fields.Many2one(
        'res.users', string='Survey Engineer', tracking=True, index=True,
        domain="[('share', '=', False)]")
    survey_date = fields.Date(string='Survey Date', tracking=True)
    deadline = fields.Date(string='Deadline', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1', index=True, tracking=True)
    assigned_date = fields.Datetime(string='Assigned On', readonly=True, copy=False)
    completed_date = fields.Datetime(string='Completed On', readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Technical survey (SRS 15)
    # ------------------------------------------------------------------
    existing_network = fields.Text(string='Existing Network')
    network_availability = fields.Selection(
        AVAILABILITY_SELECTION, string='Network Availability')
    bandwidth_availability = fields.Selection(
        AVAILABILITY_SELECTION, string='Bandwidth Availability')
    fiber_availability = fields.Selection(
        AVAILABILITY_SELECTION, string='Fiber Availability')
    power_availability = fields.Selection(
        AVAILABILITY_SELECTION, string='Power Availability')
    rack_availability = fields.Selection(
        AVAILABILITY_SELECTION, string='Rack Availability')
    nearest_pop = fields.Char(string='Nearest POP / Node')
    distance_from_pop = fields.Float(string='Distance from POP (m)')
    equipment_requirement = fields.Text(string='Equipment Requirement')
    installation_complexity = fields.Selection(
        COMPLEXITY_SELECTION, string='Installation Complexity', default='medium')
    technical_remarks = fields.Text(string='Technical Remarks')

    # ------------------------------------------------------------------
    # Feasibility (SRS 16)
    # ------------------------------------------------------------------
    feasibility = fields.Selection(
        FEASIBILITY_SELECTION, string='Feasibility', tracking=True, index=True)
    feasibility_reason = fields.Text(
        string='Not Feasible - Reason',
        help='Mandatory when the feasibility is "Not Feasible".')
    feasibility_conditions = fields.Text(
        string='Conditions',
        help='Mandatory when the feasibility is "Conditionally Feasible".')
    investigation_note = fields.Text(string='Investigation Required')

    # ------------------------------------------------------------------
    # Traceability
    # ------------------------------------------------------------------
    technical_report_ids = fields.One2many(
        'gc.erm.technical.report', 'survey_id', string='Technical Reports')
    boq_ids = fields.One2many('gc.erm.boq', 'survey_id', string='BOQs')
    proposal_ids = fields.One2many(
        'gc.erm.proposal', 'survey_id', string='Proposals')
    technical_report_count = fields.Integer(compute='_compute_document_counts')
    boq_count = fields.Integer(compute='_compute_document_counts')
    proposal_count = fields.Integer(compute='_compute_document_counts')
    is_overdue = fields.Boolean(
        string='Overdue', compute='_compute_is_overdue', store=True)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_state(self, states, domain, order=None):
        return [key for key, _label in SURVEY_STATE_SELECTION]

    @api.depends('gps_latitude', 'gps_longitude')
    def _compute_map_url(self):
        for survey in self:
            if survey.gps_latitude or survey.gps_longitude:
                survey.map_url = (
                    'https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=17/%s/%s'
                    % (survey.gps_latitude, survey.gps_longitude,
                       survey.gps_latitude, survey.gps_longitude))
            else:
                survey.map_url = False

    @api.depends('service_line_ids.service_id')
    def _compute_service_ids(self):
        for survey in self:
            survey.service_ids = survey.service_line_ids.mapped('service_id')

    def _compute_document_counts(self):
        for survey in self:
            survey.technical_report_count = len(survey.technical_report_ids)
            survey.boq_count = len(survey.boq_ids)
            survey.proposal_count = len(survey.proposal_ids)

    @api.depends('deadline', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for survey in self:
            survey.is_overdue = bool(
                survey.deadline and survey.deadline < today
                and survey.state in ('draft', 'assigned', 'in_progress'))

    # ------------------------------------------------------------------
    # Constraints (SRS 16 / 66 / BR-003)
    # ------------------------------------------------------------------
    @api.constrains('lead_id')
    def _check_lead_approved(self):
        for survey in self:
            if survey.lead_id.state not in ('approved',) and \
                    not self.env.context.get('gc_bypass_lead_check'):
                raise ValidationError(_(
                    'A survey must reference an approved lead. Lead %(lead)s '
                    'is currently %(state)s.',
                    lead=survey.lead_id.name,
                    state=survey.lead_id._gc_state_label(survey.lead_id.state)))

    @api.constrains('deadline', 'survey_date')
    def _check_dates(self):
        for survey in self:
            if survey.survey_date and survey.deadline and \
                    survey.deadline < survey.survey_date:
                raise ValidationError(_(
                    'The survey deadline cannot be earlier than the survey date.'))

    @api.constrains('gps_latitude', 'gps_longitude')
    def _check_gps(self):
        for survey in self:
            if survey.gps_latitude and not -90.0 <= survey.gps_latitude <= 90.0:
                raise ValidationError(_(
                    'GPS latitude must be between -90 and 90 degrees.'))
            if survey.gps_longitude and not -180.0 <= survey.gps_longitude <= 180.0:
                raise ValidationError(_(
                    'GPS longitude must be between -180 and 180 degrees.'))

    def _check_feasibility_complete(self):
        """SRS 16 -- conditional mandatory fields."""
        self.ensure_one()
        if not self.feasibility:
            raise UserError(_(
                'Please record the technical feasibility before completing '
                'survey %s.', self.name))
        if self.feasibility == 'not_feasible' and not self.feasibility_reason:
            raise UserError(_(
                'A reason is mandatory when the feasibility is "Not Feasible".'))
        if self.feasibility == 'conditional' and not self.feasibility_conditions:
            raise UserError(_(
                'The conditions are mandatory when the feasibility is '
                '"Conditionally Feasible".'))
        if self.feasibility == 'investigate' and not self.investigation_note:
            raise UserError(_(
                'Please describe what must be investigated further.'))
        return True

    # ------------------------------------------------------------------
    # Workflow (SRS 14)
    # ------------------------------------------------------------------
    def action_open_assign_wizard(self):
        self.ensure_one()
        if self.state not in ('draft', 'assigned'):
            raise UserError(_(
                'Only a draft or already assigned survey can be re-assigned.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Survey'),
            'res_model': 'gc.erm.survey.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_survey_id': self.id,
                'default_team_id': self.team_id.id,
                'default_engineer_id': self.engineer_id.id,
                'default_survey_date': self.survey_date,
                'default_deadline': self.deadline,
                'default_priority': self.priority,
            },
        }

    def action_start(self):
        for survey in self:
            if survey.state != 'assigned':
                raise UserError(_(
                    'Only an assigned survey can be started.'))
            if self.env.user != survey.engineer_id and not self.env.user.has_group(
                    'gc_erm_lead_to_billing.group_gc_technical_manager'):
                raise UserError(_(
                    'Survey %s is assigned to %s. Only the assigned engineer '
                    'or a Technical Manager can start it.',
                    survey.name, survey.engineer_id.name or _('nobody')))
            survey._gc_transition(
                'in_progress', comment=_('Technical survey started.'),
                allowed_from=('assigned',))
        return True

    def action_complete(self):
        for survey in self:
            if survey.state != 'in_progress':
                raise UserError(_(
                    'Only a survey in progress can be completed.'))
            survey._check_feasibility_complete()
            survey._gc_transition(
                'completed',
                comment=_('Technical survey completed. Feasibility: %s',
                          dict(FEASIBILITY_SELECTION).get(survey.feasibility, '')),
                allowed_from=('in_progress',),
                extra_vals={'completed_date': fields.Datetime.now()})
            survey._gc_schedule_activity(
                survey.salesperson_id,
                summary=_('Survey %s completed', survey.name),
                note=_('The technical survey has been completed. Feasibility: '
                       '%s.', dict(FEASIBILITY_SELECTION).get(survey.feasibility)),
                days=1)
            survey._gc_notify(
                'gc_erm_lead_to_billing.mail_template_gc_survey_completed')
            survey.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def action_mark_submitted(self):
        """Called when the related technical report is submitted."""
        for survey in self:
            if survey.state == 'completed':
                survey._gc_transition(
                    'submitted', comment=_('Technical report submitted.'),
                    allowed_from=('completed',))
        return True

    def action_reset_draft(self):
        for survey in self:
            if survey.state in ('submitted',):
                raise UserError(_(
                    'Survey %s has already been reported to Sales and cannot '
                    'be reset.', survey.name))
            survey._gc_transition('draft', comment=_('Reset to draft.'))
        return True

    def action_cancel(self):
        for survey in self:
            if survey.technical_report_ids.filtered(
                    lambda r: r.state not in ('draft', 'cancelled')):
                raise UserError(_(
                    'Cancel the submitted technical reports of %s first.',
                    survey.name))
            survey._gc_transition('cancelled', comment=_('Survey cancelled.'))
        return True

    # ------------------------------------------------------------------
    # Downstream document creation
    # ------------------------------------------------------------------
    def action_create_boq(self):
        self.ensure_one()
        if self.state not in ('in_progress', 'completed'):
            raise UserError(_(
                'A BOQ can only be prepared while the technical survey is in '
                'progress or completed.'))
        boq = self.env['gc.erm.boq'].create({
            'survey_id': self.id,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'prepared_by_id': self.env.user.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bill of Quantities'),
            'res_model': 'gc.erm.boq',
            'res_id': boq.id,
            'view_mode': 'form',
        }

    def action_create_technical_report(self):
        self.ensure_one()
        if self.state != 'completed':
            raise UserError(_(
                'Complete the technical survey before creating the technical '
                'report.'))
        existing = self.technical_report_ids.filtered(
            lambda r: r.state not in ('cancelled',))
        if existing:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Technical Report'),
                'res_model': 'gc.erm.technical.report',
                'res_id': existing[0].id,
                'view_mode': 'form',
            }
        boq = self.boq_ids.filtered(lambda b: b.state != 'cancelled')[:1]
        report = self.env['gc.erm.technical.report'].create({
            'survey_id': self.id,
            'partner_id': self.partner_id.id,
            'engineer_id': self.engineer_id.id or self.env.user.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'boq_id': boq.id if boq else False,
            'feasibility': self.feasibility,
            'technical_findings': self.technical_remarks,
            'required_equipment': self.equipment_requirement,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Technical Report'),
            'res_model': 'gc.erm.technical.report',
            'res_id': report.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_lead(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gc.erm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
        }

    def action_view_technical_reports(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Technical Reports'),
            'res_model': 'gc.erm.technical.report',
            'view_mode': 'tree,form',
            'domain': [('survey_id', '=', self.id)],
            'context': {'default_survey_id': self.id},
        }

    def action_view_boqs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bills of Quantities'),
            'res_model': 'gc.erm.boq',
            'view_mode': 'tree,form',
            'domain': [('survey_id', '=', self.id)],
            'context': {'default_survey_id': self.id},
        }

    def action_view_proposals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Proposals'),
            'res_model': 'gc.erm.proposal',
            'view_mode': 'tree,form',
            'domain': [('survey_id', '=', self.id)],
        }

    @api.depends('name', 'partner_id')
    def _compute_display_name(self):
        for survey in self:
            survey.display_name = '%s - %s' % (survey.name, survey.partner_id.name) \
                if survey.partner_id else survey.name

    # ------------------------------------------------------------------
    # Cron (SRS 80)
    # ------------------------------------------------------------------
    @api.model
    def _cron_check_survey_deadline(self):
        """Flag overdue surveys and notify the technical managers."""
        today = fields.Date.context_today(self)
        overdue = self.search([
            ('state', 'in', ('draft', 'assigned', 'in_progress')),
            ('deadline', '<', today),
        ])
        for survey in overdue:
            survey._compute_is_overdue()
            responsible = survey.engineer_id or survey.team_id.leader_id
            if responsible and not survey.activity_ids.filtered(
                    lambda a: a.user_id == responsible
                    and a.summary == _('Overdue survey %s', survey.name)):
                survey._gc_schedule_activity(
                    responsible,
                    summary=_('Overdue survey %s', survey.name),
                    note=_('The survey deadline (%s) has passed.',
                           survey.deadline),
                    days=0)
        return True


class GcErmSurveyLine(models.Model):
    _name = 'gc.erm.survey.line'
    _description = 'GC ERM Survey Service Line'
    _order = 'sequence, id'

    survey_id = fields.Many2one(
        'gc.erm.survey', string='Survey', required=True, ondelete='cascade',
        index=True)
    sequence = fields.Integer(default=10)
    service_id = fields.Many2one(
        'gc.erm.service.catalog', string='Required Service', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(
        string='Quantity / Links', default=1.0, digits='Product Unit of Measure')
    bandwidth = fields.Char(string='Required Bandwidth / Capacity')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    remarks = fields.Char(string='Remarks')
    company_id = fields.Many2one(
        related='survey_id.company_id', store=True, index=True)

    @api.onchange('service_id')
    def _onchange_service_id(self):
        for line in self:
            if line.service_id:
                line.product_id = line.service_id.product_id
                line.uom_id = line.service_id.uom_id

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_(
                    'The quantity of service "%s" must be greater than zero.',
                    line.service_id.display_name))
