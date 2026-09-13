# -*- coding: utf-8 -*-
"""Lead management and HOD approval (SRS 9, 10, 11)."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

LEAD_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('hod_approval', 'HOD Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('cancelled', 'Cancelled'),
]

PRIORITY_SELECTION = [
    ('0', 'Low'),
    ('1', 'Normal'),
    ('2', 'High'),
    ('3', 'Urgent'),
]


class GcErmLead(models.Model):
    _name = 'gc.erm.lead'
    _description = 'GC ERM Sales Lead'
    _inherit = ['gc.erm.document.mixin']
    _order = 'priority desc, lead_date desc, id desc'

    _gc_sequence_code = 'gc.erm.lead'
    _gc_sla_parameter = 'gc_erm.sla_lead_days'
    _gc_closed_states = ('approved', 'rejected', 'cancelled')

    # ------------------------------------------------------------------
    # General (SRS 9.2)
    # ------------------------------------------------------------------
    state = fields.Selection(
        LEAD_STATE_SELECTION, string='Status', default='draft', required=True,
        copy=False, tracking=True, index=True, group_expand='_group_expand_state')
    lead_date = fields.Date(
        string='Lead Date', required=True, default=fields.Date.context_today,
        tracking=True)
    salesperson_id = fields.Many2one(
        'res.users', string='Salesperson', required=True, tracking=True,
        default=lambda self: self.env.user, index=True,
        domain="[('share', '=', False)]")
    team_id = fields.Many2one(
        'crm.team', string='Sales Team', tracking=True,
        help='Sales team owning the lead. Drives the HOD approval routing.')
    partner_id = fields.Many2one(
        'res.partner', string='Customer', tracking=True, index=True,
        domain="[('is_company', 'in', (True, False))]",
        help='Existing customer, or a new contact created from this lead.')
    contact_id = fields.Many2one(
        'res.partner', string='Contact', tracking=True,
        domain="['|', ('parent_id', '=', partner_id), ('id', '=', partner_id)]")
    crm_lead_id = fields.Many2one(
        'crm.lead', string='CRM Opportunity', copy=False,
        help='Optional link to a standard Odoo CRM opportunity.')
    source_id = fields.Many2one('utm.source', string='Lead Source', tracking=True)
    priority = fields.Selection(
        PRIORITY_SELECTION, string='Priority', default='1', index=True,
        tracking=True)
    expected_revenue = fields.Monetary(
        string='Expected Revenue', currency_field='currency_id', tracking=True)
    date_deadline = fields.Date(string='Expected Closing Date', tracking=True)
    description = fields.Html(
        string='Requirement / Description', sanitize=True,
        help='Business requirement captured from the customer.')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'gc_lead_attachment_rel', 'lead_id', 'attachment_id',
        string='Attachments')

    # ------------------------------------------------------------------
    # Contact block (SRS 9.2)
    # ------------------------------------------------------------------
    contact_person = fields.Char(string='Contact Person', tracking=True)
    contact_designation = fields.Char(string='Designation')
    contact_phone = fields.Char(string='Phone')
    contact_phone_alt = fields.Char(string='Alternative Phone')
    contact_email = fields.Char(string='Email')

    # ------------------------------------------------------------------
    # Location block (SRS 9.2)
    # ------------------------------------------------------------------
    street = fields.Char(string='Address')
    street2 = fields.Char(string='Address Line 2')
    city = fields.Char(string='City')
    district = fields.Char(string='District')
    area = fields.Char(string='Area')
    zip_code = fields.Char(string='ZIP')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one(
        'res.country', string='Country',
        default=lambda self: self.env.company.country_id)
    gps_latitude = fields.Float(string='GPS Latitude', digits=(10, 7))
    gps_longitude = fields.Float(string='GPS Longitude', digits=(10, 7))
    map_url = fields.Char(string='Map Link', compute='_compute_map_url')

    # ------------------------------------------------------------------
    # Service block (SRS 9.2)
    # ------------------------------------------------------------------
    service_line_ids = fields.One2many(
        'gc.erm.lead.line', 'lead_id', string='Required Services', copy=True)
    service_ids = fields.Many2many(
        'gc.erm.service.catalog', string='Services',
        compute='_compute_service_ids', store=True)
    service_location = fields.Char(string='Service Location')
    expected_golive_date = fields.Date(string='Expected Go-Live Date')
    contract_duration = fields.Integer(
        string='Contract Duration (months)', default=12)
    survey_required = fields.Boolean(
        string='Technical Survey Required', compute='_compute_survey_required',
        store=True, readonly=False,
        help='Derived from the service catalog, can be overridden.')

    # ------------------------------------------------------------------
    # Traceability (SRS 45 / 46)
    # ------------------------------------------------------------------
    survey_ids = fields.One2many('gc.erm.survey', 'lead_id', string='Surveys')
    proposal_ids = fields.One2many('gc.erm.proposal', 'lead_id', string='Proposals')
    survey_count = fields.Integer(compute='_compute_document_counts')
    proposal_count = fields.Integer(compute='_compute_document_counts')
    quotation_count = fields.Integer(compute='_compute_document_counts')
    sale_order_count = fields.Integer(compute='_compute_document_counts')
    work_order_count = fields.Integer(compute='_compute_document_counts')
    invoice_count = fields.Integer(compute='_compute_document_counts')

    # ------------------------------------------------------------------
    # Compute / onchange
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_state(self, states, domain, order=None):
        return [key for key, _label in LEAD_STATE_SELECTION]

    @api.depends('gps_latitude', 'gps_longitude')
    def _compute_map_url(self):
        for lead in self:
            if lead.gps_latitude or lead.gps_longitude:
                lead.map_url = (
                    'https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=17/%s/%s'
                    % (lead.gps_latitude, lead.gps_longitude,
                       lead.gps_latitude, lead.gps_longitude))
            else:
                lead.map_url = False

    @api.depends('service_line_ids.service_id')
    def _compute_service_ids(self):
        for lead in self:
            lead.service_ids = lead.service_line_ids.mapped('service_id')

    @api.depends('service_line_ids.service_id')
    def _compute_survey_required(self):
        for lead in self:
            services = lead.service_line_ids.mapped('service_id')
            lead.survey_required = any(services.mapped('survey_required')) \
                if services else True

    def _compute_document_counts(self):
        SaleOrder = self.env['sale.order']
        WorkOrder = self.env['gc.erm.work.order']
        Move = self.env['account.move']
        for lead in self:
            lead.survey_count = len(lead.survey_ids)
            lead.proposal_count = len(lead.proposal_ids)
            orders = SaleOrder.search([('gc_lead_id', '=', lead.id)])
            lead.quotation_count = len(orders.filtered(
                lambda o: o.state in ('draft', 'sent')))
            lead.sale_order_count = len(orders.filtered(
                lambda o: o.state == 'sale'))
            lead.work_order_count = WorkOrder.search_count(
                [('lead_id', '=', lead.id)])
            lead.invoice_count = Move.search_count([
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('gc_lead_id', '=', lead.id)])

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for lead in self:
            partner = lead.partner_id
            if not partner:
                continue
            lead.contact_person = partner.name if not partner.is_company else \
                (partner.child_ids[:1].name or partner.name)
            lead.contact_phone = partner.phone or partner.mobile
            lead.contact_email = partner.email
            lead.street = partner.street
            lead.street2 = partner.street2
            lead.city = partner.city
            lead.zip_code = partner.zip
            lead.state_id = partner.state_id
            lead.country_id = partner.country_id
            lead.district = partner.gc_district
            lead.area = partner.gc_area
            if partner.gc_latitude or partner.gc_longitude:
                lead.gps_latitude = partner.gc_latitude
                lead.gps_longitude = partner.gc_longitude
            if partner.is_company and partner.child_ids:
                lead.contact_id = partner.child_ids[0]

    @api.onchange('contact_id')
    def _onchange_contact_id(self):
        for lead in self:
            contact = lead.contact_id
            if not contact:
                continue
            lead.contact_person = contact.name
            lead.contact_designation = contact.function
            lead.contact_phone = contact.phone or contact.mobile
            lead.contact_email = contact.email

    @api.onchange('salesperson_id')
    def _onchange_salesperson_id(self):
        for lead in self:
            if lead.salesperson_id and not lead.team_id:
                team = self.env['crm.team'].search(
                    [('user_id', '=', lead.salesperson_id.id)], limit=1)
                lead.team_id = team

    # ------------------------------------------------------------------
    # Constraints (SRS 66)
    # ------------------------------------------------------------------
    @api.constrains('gps_latitude', 'gps_longitude')
    def _check_gps(self):
        for lead in self:
            if lead.gps_latitude and not -90.0 <= lead.gps_latitude <= 90.0:
                raise ValidationError(_(
                    'GPS latitude must be between -90 and 90 degrees.'))
            if lead.gps_longitude and not -180.0 <= lead.gps_longitude <= 180.0:
                raise ValidationError(_(
                    'GPS longitude must be between -180 and 180 degrees.'))

    @api.constrains('expected_revenue', 'contract_duration')
    def _check_positive_values(self):
        for lead in self:
            if lead.expected_revenue < 0:
                raise ValidationError(_('Expected revenue cannot be negative.'))
            if lead.contract_duration < 0:
                raise ValidationError(_('Contract duration cannot be negative.'))

    # ------------------------------------------------------------------
    # Write guard (SRS 67 -- approved documents are not silently edited)
    # ------------------------------------------------------------------
    LOCKED_FIELDS = (
        'partner_id', 'contact_id', 'service_line_ids', 'expected_revenue',
        'salesperson_id', 'lead_date', 'description', 'contract_duration',
    )

    def write(self, vals):
        protected = set(vals) & set(self.LOCKED_FIELDS)
        if protected and not self.env.context.get('gc_bypass_lock'):
            for lead in self:
                if lead.state in ('approved', 'rejected', 'cancelled') and \
                        not self.env.user.has_group(
                            'gc_erm_lead_to_billing.group_gc_erm_admin'):
                    raise UserError(_(
                        "Lead %(name)s is %(state)s and its commercial data is "
                        "locked. Ask an administrator, or use 'Request "
                        "Revision' to reopen it.",
                        name=lead.name, state=lead._gc_state_label(lead.state)))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Workflow (SRS 10 / 11)
    # ------------------------------------------------------------------
    def _check_submit_ready(self):
        """Preconditions listed in SRS 10.1."""
        self.ensure_one()
        missing = []
        if not self.partner_id:
            missing.append(_('Customer'))
        if not (self.contact_id or self.contact_person):
            missing.append(_('Contact person'))
        if not self.service_line_ids:
            missing.append(_('At least one required service'))
        if not self.salesperson_id:
            missing.append(_('Salesperson'))
        if not self.description or self.description in ('<p><br></p>', '<p></p>'):
            missing.append(_('Requirement / description'))
        if missing:
            raise UserError(_(
                'Required service information is missing. Please complete: '
                '%s.', ', '.join(missing)))
        return True

    def action_submit(self):
        for lead in self:
            if lead.state != 'draft':
                raise UserError(_(
                    'Only a draft lead can be submitted for approval.'))
            lead._check_submit_ready()
            lead._gc_transition(
                'hod_approval',
                comment=_('Submitted for HOD approval.'),
                allowed_from=('draft',),
                extra_vals={
                    'submitted_by_id': self.env.user.id,
                    'submitted_date': fields.Datetime.now(),
                    'rejection_reason': False,
                    'revision_reason': False,
                })
            hod = lead._gc_hod_user()
            if hod:
                lead._gc_schedule_activity(
                    hod,
                    summary=_('Approve Lead %s', lead.name),
                    note=_('Lead %(name)s submitted by %(user)s requires your '
                           'approval.', name=lead.name,
                           user=self.env.user.name),
                    days=int(lead._gc_sla_days() or 1))
            lead._gc_notify('gc_erm_lead_to_billing.mail_template_gc_lead_approval_request')
        return True

    def _gc_hod_user(self):
        """Resolve the approver: team leader first, then any Sales HOD."""
        self.ensure_one()
        leader = self.team_id.user_id
        if leader and leader.has_group(
                'gc_erm_lead_to_billing.group_gc_sales_hod'):
            return leader
        candidates = self._gc_users_in_group(
            'gc_erm_lead_to_billing.group_gc_sales_hod').filtered(
                lambda u: u != self.env.user)
        return candidates[0] if candidates else self.env['res.users']

    def action_approve(self):
        for lead in self:
            if lead.state != 'hod_approval':
                raise UserError(_(
                    'Only a lead pending HOD review can be approved.'))
            lead._gc_require_group(
                'gc_erm_lead_to_billing.group_gc_sales_hod', _('approve leads'))
            lead._gc_check_not_self_approval(lead.salesperson_id)
            allowed, rule = self.env['gc.erm.approval.matrix'].check_approver(
                'lead', lead.expected_revenue, company=lead.company_id)
            if not allowed:
                raise AccessError(_(
                    'The expected revenue of %(amount)s requires approval by '
                    '%(group)s.', amount=lead.expected_revenue,
                    group=rule.approver_group_id.name))
            lead._gc_transition(
                'approved', comment=_('Lead approved by HOD.'),
                allowed_from=('hod_approval',),
                extra_vals={
                    'approved_by_id': self.env.user.id,
                    'approved_date': fields.Datetime.now(),
                })
            lead._gc_schedule_activity(
                lead.salesperson_id,
                summary=_('Create Survey for %s', lead.name),
                note=_('The lead has been approved. You can now generate the '
                       'customer survey.'), days=1)
            lead._gc_notify('gc_erm_lead_to_billing.mail_template_gc_lead_approved')
            lead.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def _gc_apply_rejection(self, reason):
        self.ensure_one()
        self._gc_require_group(
            'gc_erm_lead_to_billing.group_gc_sales_hod', _('reject leads'))
        self._gc_transition(
            'rejected', comment=reason, allowed_from=('hod_approval', 'draft'),
            extra_vals={
                'rejected_by_id': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
                'rejection_reason': reason,
            })
        self._gc_notify('gc_erm_lead_to_billing.mail_template_gc_lead_rejected')
        self.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def _gc_apply_revision(self, reason):
        """SRS 11 -- revision sends the lead back to Sales as a draft."""
        self.ensure_one()
        self._gc_require_group(
            'gc_erm_lead_to_billing.group_gc_sales_hod', _('request revisions'))
        self._gc_transition(
            'draft', comment=_('Revision requested: %s', reason),
            allowed_from=('hod_approval',),
            extra_vals={'revision_reason': reason})
        self._gc_schedule_activity(
            self.salesperson_id,
            summary=_('Revise Lead %s', self.name), note=reason, days=1)
        self.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def action_reset_draft(self):
        for lead in self:
            if lead.state not in ('rejected', 'cancelled'):
                raise UserError(_(
                    'Only a rejected or cancelled lead can be reset to draft.'))
            lead.with_context(gc_bypass_lock=True)._gc_transition(
                'draft', comment=_('Reset to draft.'),
                allowed_from=('rejected', 'cancelled'),
                extra_vals={
                    'rejection_reason': False,
                    'rejected_by_id': False,
                    'rejected_date': False,
                })
        return True

    def action_cancel(self):
        for lead in self:
            if lead.survey_ids.filtered(lambda s: s.state != 'cancelled'):
                raise UserError(_(
                    'Cancel or delete the related surveys of %s first.',
                    lead.name))
            lead._gc_transition('cancelled', comment=_('Lead cancelled.'))
        return True

    # ------------------------------------------------------------------
    # Survey generation (SRS 12 / BR-001)
    # ------------------------------------------------------------------
    def action_create_survey(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_(
                'You cannot create a survey until the lead is approved.'))
        survey = self.env['gc.erm.survey'].create(self._prepare_survey_vals())
        self.message_post(body=_('Survey %s generated from this lead.',
                                 survey.name))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Survey'),
            'res_model': 'gc.erm.survey',
            'res_id': survey.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _prepare_survey_vals(self):
        """SRS 12 -- the survey inherits the lead data."""
        self.ensure_one()
        return {
            'lead_id': self.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'contact_id': self.contact_id.id,
            'salesperson_id': self.salesperson_id.id,
            'contact_person': self.contact_person,
            'contact_designation': self.contact_designation,
            'contact_phone': self.contact_phone,
            'contact_phone_alt': self.contact_phone_alt,
            'contact_email': self.contact_email,
            'street': self.street,
            'street2': self.street2,
            'city': self.city,
            'district': self.district,
            'area': self.area,
            'zip_code': self.zip_code,
            'state_id': self.state_id.id,
            'country_id': self.country_id.id,
            'gps_latitude': self.gps_latitude,
            'gps_longitude': self.gps_longitude,
            'service_location': self.service_location,
            'expected_golive_date': self.expected_golive_date,
            'contract_duration': self.contract_duration,
            'requirement_note': self.description,
            'service_line_ids': [
                (0, 0, {
                    'service_id': line.service_id.id,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'bandwidth': line.bandwidth,
                    'uom_id': line.uom_id.id,
                    'remarks': line.remarks,
                }) for line in self.service_line_ids],
        }

    # ------------------------------------------------------------------
    # Smart buttons (SRS 46)
    # ------------------------------------------------------------------
    def _gc_action_window(self, name, model, domain, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': 'tree,form',
            'domain': domain,
            'context': dict(context or {}),
        }

    def action_view_surveys(self):
        return self._gc_action_window(
            _('Surveys'), 'gc.erm.survey', [('lead_id', '=', self.id)],
            {'default_lead_id': self.id})

    def action_view_proposals(self):
        return self._gc_action_window(
            _('Proposals'), 'gc.erm.proposal', [('lead_id', '=', self.id)],
            {'default_lead_id': self.id})

    def action_view_quotations(self):
        return self._gc_action_window(
            _('Quotations'), 'sale.order',
            [('gc_lead_id', '=', self.id), ('state', 'in', ('draft', 'sent'))])

    def action_view_sale_orders(self):
        return self._gc_action_window(
            _('Sales Orders'), 'sale.order',
            [('gc_lead_id', '=', self.id), ('state', '=', 'sale')])

    def action_view_work_orders(self):
        return self._gc_action_window(
            _('Work Orders'), 'gc.erm.work.order', [('lead_id', '=', self.id)])

    def action_view_invoices(self):
        return self._gc_action_window(
            _('Invoices'), 'account.move',
            [('gc_lead_id', '=', self.id),
             ('move_type', 'in', ('out_invoice', 'out_refund'))])

    @api.depends('name', 'partner_id')
    def _compute_display_name(self):
        for lead in self:
            lead.display_name = '%s - %s' % (lead.name, lead.partner_id.name) \
                if lead.partner_id else lead.name


class GcErmLeadLine(models.Model):
    _name = 'gc.erm.lead.line'
    _description = 'GC ERM Lead Service Line'
    _order = 'sequence, id'

    lead_id = fields.Many2one(
        'gc.erm.lead', string='Lead', required=True, ondelete='cascade',
        index=True)
    sequence = fields.Integer(default=10)
    service_id = fields.Many2one(
        'gc.erm.service.catalog', string='Required Service', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(
        string='Quantity / Links', default=1.0, digits='Product Unit of Measure')
    bandwidth = fields.Char(
        string='Bandwidth / Capacity',
        help='Free text, for example "10 Mbps" or "1 Gbps dedicated".')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    remarks = fields.Char(string='Remarks')
    company_id = fields.Many2one(
        related='lead_id.company_id', store=True, index=True)

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
