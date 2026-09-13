# -*- coding: utf-8 -*-
"""Installation, checklist, result, report and revisit (SRS 36 - 40)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

INSTALLATION_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('in_progress', 'In Progress'),
    ('submitted', 'Report Submitted'),
    ('done', 'Completed'),
    ('revisit', 'Revisit Required'),
    ('cancelled', 'Cancelled'),
]

INSTALLATION_RESULT_SELECTION = [
    ('success', 'Successful'),
    ('partial', 'Partially Successful'),
    ('failed', 'Failed'),
    ('revisit', 'Requires Revisit'),
]

CHECKLIST_ANSWER_SELECTION = [
    ('yes', 'Yes'),
    ('no', 'No'),
    ('na', 'N/A'),
]


class GcErmInstallation(models.Model):
    _name = 'gc.erm.installation'
    _description = 'GC ERM Installation'
    _inherit = ['gc.erm.document.mixin']
    _order = 'installation_date desc, id desc'

    _gc_sequence_code = 'gc.erm.installation'
    _gc_sla_parameter = 'gc_erm.sla_installation_days'
    _gc_closed_states = ('done', 'cancelled')

    state = fields.Selection(
        INSTALLATION_STATE_SELECTION, string='Status', default='draft',
        required=True, copy=False, tracking=True, index=True,
        group_expand='_group_expand_state')

    # ------------------------------------------------------------------
    # References (SRS 36 / BR-008)
    # ------------------------------------------------------------------
    work_order_id = fields.Many2one(
        'gc.erm.work.order', string='Work Order', required=True,
        ondelete='restrict', index=True, tracking=True)
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order',
        related='work_order_id.sale_order_id', store=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, index=True)
    lead_id = fields.Many2one(
        'gc.erm.lead', string='Lead', related='work_order_id.lead_id', store=True)
    service_location = fields.Char(
        string='Location', related='work_order_id.service_location',
        readonly=False, store=True)
    gps_latitude = fields.Float(
        string='GPS Latitude', related='work_order_id.gps_latitude',
        readonly=False, store=True, digits=(10, 7))
    gps_longitude = fields.Float(
        string='GPS Longitude', related='work_order_id.gps_longitude',
        readonly=False, store=True, digits=(10, 7))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    team_id = fields.Many2one(
        'gc.erm.team', string='Team', tracking=True,
        domain="[('team_type', 'in', ('implementation', 'both'))]")
    engineer_id = fields.Many2one(
        'res.users', string='Engineer', required=True, tracking=True,
        default=lambda self: self.env.user, index=True)
    technician_ids = fields.Many2many(
        'res.users', 'gc_installation_technician_rel', 'installation_id',
        'user_id', string='Technicians')
    installation_date = fields.Date(
        string='Installation Date', required=True,
        default=fields.Date.context_today, tracking=True)
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')
    duration_hours = fields.Float(
        string='Duration (hours)', compute='_compute_duration', store=True)

    # ------------------------------------------------------------------
    # Technical details
    # ------------------------------------------------------------------
    line_ids = fields.One2many(
        'gc.erm.installation.line', 'installation_id',
        string='Products Installed', copy=True)
    ip_information = fields.Text(string='IP Information')
    configuration_details = fields.Html(
        string='Configuration Details', sanitize=True)
    testing_results = fields.Html(string='Testing Results', sanitize=True)
    bandwidth_tested = fields.Char(string='Bandwidth Tested')
    remarks = fields.Text(string='Engineer Remarks')

    # ------------------------------------------------------------------
    # Checklist (SRS 37)
    # ------------------------------------------------------------------
    checklist_template_id = fields.Many2one(
        'gc.erm.checklist.template', string='Checklist Template')
    checklist_line_ids = fields.One2many(
        'gc.erm.installation.checklist.line', 'installation_id',
        string='Checklist', copy=True)
    checklist_progress = fields.Float(
        string='Checklist Progress (%)', compute='_compute_checklist_progress',
        store=True)
    checklist_complete = fields.Boolean(
        string='Checklist Complete', compute='_compute_checklist_progress',
        store=True)

    # ------------------------------------------------------------------
    # Result (SRS 38)
    # ------------------------------------------------------------------
    result = fields.Selection(
        INSTALLATION_RESULT_SELECTION, string='Installation Result',
        tracking=True, index=True)
    failure_reason = fields.Text(
        string='Reason',
        help='Mandatory when the result is Failed or Requires Revisit.')
    required_action = fields.Text(
        string='Required Action',
        help='Mandatory when the result is Failed or Requires Revisit.')
    next_visit_date = fields.Date(string='Next Visit Date')
    next_engineer_id = fields.Many2one('res.users', string='Assigned Engineer')

    # ------------------------------------------------------------------
    # Customer confirmation (SRS 36 / 39)
    # ------------------------------------------------------------------
    customer_representative = fields.Char(string='Customer Representative')
    customer_designation = fields.Char(string='Designation')
    customer_signature = fields.Binary(string='Customer Signature', copy=False)
    customer_signed_on = fields.Date(string='Signed On')
    customer_accepted = fields.Boolean(string='Customer Acceptance Obtained')
    photo_ids = fields.Many2many(
        'ir.attachment', 'gc_installation_photo_rel', 'installation_id',
        'attachment_id', string='Installation Photos')

    # ------------------------------------------------------------------
    # Revisit (SRS 40)
    # ------------------------------------------------------------------
    revisit_of_id = fields.Many2one(
        'gc.erm.installation', string='Revisit Of', readonly=True, copy=False,
        ondelete='set null', index=True)
    revisit_ids = fields.One2many(
        'gc.erm.installation', 'revisit_of_id', string='Revisits')
    revisit_count = fields.Integer(compute='_compute_revisit_count')
    visit_number = fields.Integer(string='Visit Number', default=1, readonly=True)

    report_submitted_date = fields.Datetime(
        string='Report Submitted On', readonly=True, copy=False)
    invoice_count = fields.Integer(compute='_compute_invoice_count')

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.model
    def _group_expand_state(self, states, domain, order=None):
        return [key for key, _label in INSTALLATION_STATE_SELECTION]

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for installation in self:
            if installation.start_time and installation.end_time:
                delta = installation.end_time - installation.start_time
                installation.duration_hours = round(delta.total_seconds() / 3600.0, 2)
            else:
                installation.duration_hours = 0.0

    @api.depends('checklist_line_ids.answer', 'checklist_line_ids.mandatory')
    def _compute_checklist_progress(self):
        for installation in self:
            lines = installation.checklist_line_ids
            if not lines:
                installation.checklist_progress = 0.0
                installation.checklist_complete = False
                continue
            answered = lines.filtered(lambda l: l.answer)
            installation.checklist_progress = len(answered) / len(lines) * 100.0
            mandatory = lines.filtered(lambda l: l.mandatory)
            installation.checklist_complete = all(
                line.answer in ('yes', 'na') for line in mandatory)

    @api.depends('revisit_ids')
    def _compute_revisit_count(self):
        for installation in self:
            installation.revisit_count = len(installation.revisit_ids)

    def _compute_invoice_count(self):
        Move = self.env['account.move']
        for installation in self:
            installation.invoice_count = Move.search_count([
                ('gc_work_order_id', '=', installation.work_order_id.id),
                ('move_type', 'in', ('out_invoice', 'out_refund'))])

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        installations = super().create(vals_list)
        for installation in installations:
            if not installation.line_ids:
                installation._load_products_from_work_order()
            if not installation.checklist_line_ids:
                installation._load_checklist()
        return installations

    def _load_products_from_work_order(self):
        self.ensure_one()
        vals = []
        for line in self.work_order_id.line_ids:
            vals.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name or line.product_id.display_name,
                'quantity': line.required_qty,
                'uom_id': (line.uom_id or line.product_id.uom_id).id,
            }))
        if vals:
            self.line_ids = vals
        return True

    def _load_checklist(self):
        self.ensure_one()
        template = self.checklist_template_id or \
            self.env['gc.erm.checklist.template']._get_default_template(
                self.work_order_id.service_ids)
        if not template:
            return False
        self.checklist_template_id = template
        self.checklist_line_ids = [(0, 0, {
            'name': item.name,
            'category': item.category,
            'mandatory': item.mandatory,
            'sequence': item.sequence,
            'help_text': item.help_text,
        }) for item in template.item_ids]
        return True

    @api.onchange('checklist_template_id')
    def _onchange_checklist_template_id(self):
        for installation in self:
            if not installation.checklist_template_id:
                continue
            installation.checklist_line_ids = [(5, 0, 0)] + [(0, 0, {
                'name': item.name,
                'category': item.category,
                'mandatory': item.mandatory,
                'sequence': item.sequence,
                'help_text': item.help_text,
            }) for item in installation.checklist_template_id.item_ids]

    # ------------------------------------------------------------------
    # Constraints (SRS 38 / 66)
    # ------------------------------------------------------------------
    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for installation in self:
            if installation.start_time and installation.end_time and \
                    installation.end_time < installation.start_time:
                raise ValidationError(_(
                    'The end time cannot be earlier than the start time.'))

    @api.constrains('work_order_id')
    def _check_work_order(self):
        for installation in self:
            if not installation.work_order_id:
                raise ValidationError(_(
                    'An installation must reference a work order.'))
            if installation.work_order_id.state in ('draft',) and \
                    not self.env.context.get('gc_bypass_wo_check'):
                raise ValidationError(_(
                    'You cannot create an installation before the work order '
                    'is confirmed.'))

    def _check_report_ready(self):
        """SRS 38 / 39 -- validate before the report is submitted."""
        self.ensure_one()
        if not self.result:
            raise UserError(_(
                'The installation report of %s cannot be completed without an '
                'installation result.', self.name))
        if self.result in ('failed', 'revisit'):
            missing = []
            if not self.failure_reason:
                missing.append(_('Reason'))
            if not self.required_action:
                missing.append(_('Required action'))
            if not self.next_visit_date:
                missing.append(_('Next visit date'))
            if not self.next_engineer_id:
                missing.append(_('Assigned engineer'))
            if missing:
                raise UserError(_(
                    'A "%(result)s" result requires: %(fields)s.',
                    result=dict(INSTALLATION_RESULT_SELECTION)[self.result],
                    fields=', '.join(missing)))
        if not self.checklist_line_ids:
            raise UserError(_(
                'The installation checklist of %s is empty.', self.name))
        unanswered = self.checklist_line_ids.filtered(
            lambda l: l.mandatory and not l.answer)
        if unanswered:
            raise UserError(_(
                'Answer every mandatory checklist item first. Missing: %s.',
                ', '.join(unanswered.mapped('name')[:5])))
        if self.result == 'success' and not self.checklist_complete:
            raise UserError(_(
                'A successful installation requires every mandatory checklist '
                'item to be "Yes" or "N/A".'))
        return True

    # ------------------------------------------------------------------
    # Workflow (SRS 39)
    # ------------------------------------------------------------------
    def action_start(self):
        for installation in self:
            if installation.state != 'draft':
                raise UserError(_(
                    'Only a draft installation can be started.'))
            installation._gc_transition(
                'in_progress', comment=_('Installation started.'),
                allowed_from=('draft',),
                extra_vals={'start_time': fields.Datetime.now()})
            installation.work_order_id.filtered(
                lambda w: w.state == 'ready_install').action_start_installation()
        return True

    def action_submit_report(self):
        for installation in self:
            if installation.state != 'in_progress':
                raise UserError(_(
                    'Only an installation in progress can be reported.'))
            installation._check_report_ready()
            installation._gc_transition(
                'submitted',
                comment=_('Installation report submitted. Result: %s',
                          dict(INSTALLATION_RESULT_SELECTION)[installation.result]),
                allowed_from=('in_progress',),
                extra_vals={
                    'end_time': installation.end_time or fields.Datetime.now(),
                    'report_submitted_date': fields.Datetime.now(),
                    'submitted_by_id': self.env.user.id,
                    'submitted_date': fields.Datetime.now(),
                })
            manager = installation.work_order_id.manager_id or \
                installation._gc_first_user_in_group(
                    'gc_erm_lead_to_billing.group_gc_implementation_user')
            if manager:
                installation._gc_schedule_activity(
                    manager,
                    summary=_('Review installation report %s', installation.name),
                    days=1)
            installation._gc_notify(
                'gc_erm_lead_to_billing.mail_template_gc_installation_completed')
        return True

    def action_complete(self):
        """SRS 39 -- close the installation and open billing."""
        for installation in self:
            if installation.state != 'submitted':
                raise UserError(_(
                    'Submit the installation report of %s before completing it.',
                    installation.name))
            if installation.result in ('failed', 'revisit'):
                raise UserError(_(
                    'Installation %s cannot be completed because its result is '
                    '"%s". Please request a revisit instead.',
                    installation.name,
                    dict(INSTALLATION_RESULT_SELECTION)[installation.result]))
            installation._gc_transition(
                'done', comment=_('Installation completed.'),
                allowed_from=('submitted',),
                extra_vals={
                    'approved_by_id': self.env.user.id,
                    'approved_date': fields.Datetime.now(),
                })
            work_order = installation.work_order_id
            work_order.action_installation_done()
            work_order._compute_billing_ready()
            if work_order.billing_ready:
                accountant = installation._gc_first_user_in_group(
                    'gc_erm_lead_to_billing.group_gc_accounts_user')
                if accountant:
                    installation._gc_schedule_activity(
                        accountant,
                        summary=_('Generate invoice for %s', work_order.name),
                        days=int(self.env['ir.config_parameter'].sudo().get_param(
                            'gc_erm.sla_billing_days', '1') or 1))
                work_order._gc_notify(
                    'gc_erm_lead_to_billing.mail_template_gc_billing_ready')
            installation.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def action_open_revisit_wizard(self):
        self.ensure_one()
        if self.state not in ('in_progress', 'submitted'):
            raise UserError(_(
                'A revisit can only be requested from an ongoing or reported '
                'installation.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Revisit'),
            'res_model': 'gc.erm.revisit.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_installation_id': self.id},
        }

    def action_reset_draft(self):
        for installation in self:
            if installation.state not in ('cancelled', 'submitted'):
                raise UserError(_(
                    'Only a cancelled or submitted installation can be reset.'))
            if installation.state == 'submitted':
                installation._gc_require_group(
                    'gc_erm_lead_to_billing.group_gc_implementation_user',
                    _('reopen a submitted installation report'))
            installation._gc_transition(
                'in_progress', comment=_('Report reopened for correction.'))
        return True

    def action_cancel(self):
        for installation in self:
            if installation.state == 'done':
                raise UserError(_(
                    'A completed installation cannot be cancelled.'))
            installation._gc_transition(
                'cancelled', comment=_('Installation cancelled.'))
        return True

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_work_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gc.erm.work.order',
            'res_id': self.work_order_id.id, 'view_mode': 'form',
        }

    def action_view_deliveries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Deliveries'),
            'res_model': 'stock.picking', 'view_mode': 'tree,form',
            'domain': [('gc_work_order_id', '=', self.work_order_id.id)],
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Invoices'),
            'res_model': 'account.move', 'view_mode': 'tree,form',
            'domain': [('gc_work_order_id', '=', self.work_order_id.id),
                       ('move_type', 'in', ('out_invoice', 'out_refund'))],
        }

    def action_view_revisits(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Revisits'),
            'res_model': 'gc.erm.installation', 'view_mode': 'tree,form',
            'domain': ['|', ('revisit_of_id', '=', self.id),
                       ('id', '=', self.id)],
        }

    @api.depends('name', 'partner_id', 'visit_number')
    def _compute_display_name(self):
        for installation in self:
            suffix = _(' (visit %s)', installation.visit_number) \
                if installation.visit_number > 1 else ''
            installation.display_name = '%s%s' % (installation.name, suffix)

    # ------------------------------------------------------------------
    # Cron (SRS 80 -- installation aging)
    # ------------------------------------------------------------------
    @api.model
    def _cron_check_installation_aging(self):
        today = fields.Date.context_today(self)
        stale = self.search([
            ('state', 'in', ('draft', 'in_progress')),
            ('installation_date', '<', today),
        ])
        for installation in stale:
            if installation.engineer_id:
                installation._gc_schedule_activity(
                    installation.engineer_id,
                    summary=_('Pending installation %s', installation.name),
                    note=_('Planned on %s and still open.',
                           installation.installation_date),
                    days=0)
        return True


class GcErmInstallationLine(models.Model):
    _name = 'gc.erm.installation.line'
    _description = 'GC ERM Installed Product Line'
    _order = 'installation_id, sequence, id'

    installation_id = fields.Many2one(
        'gc.erm.installation', string='Installation', required=True,
        ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        related='installation_id.company_id', store=True, index=True)
    product_id = fields.Many2one(
        'product.product', string='Product', required=True)
    name = fields.Char(string='Description')
    quantity = fields.Float(
        string='Quantity', default=1.0, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    serial_number = fields.Char(string='Serial Number')
    lot_id = fields.Many2one(
        'stock.lot', string='Lot / Serial',
        domain="[('product_id', '=', product_id)]")
    mac_address = fields.Char(string='MAC Address')
    ip_address = fields.Char(string='IP Address')
    installed = fields.Boolean(string='Installed', default=True)
    remarks = fields.Char(string='Remarks')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.display_name
                line.uom_id = line.product_id.uom_id

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        for line in self:
            if line.lot_id and not line.serial_number:
                line.serial_number = line.lot_id.name

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if float_compare(line.quantity, 0.0, precision_digits=4) < 0:
                raise ValidationError(_(
                    'The installed quantity cannot be negative.'))


class GcErmInstallationChecklistLine(models.Model):
    _name = 'gc.erm.installation.checklist.line'
    _description = 'GC ERM Installation Checklist Line'
    _order = 'installation_id, sequence, id'

    installation_id = fields.Many2one(
        'gc.erm.installation', string='Installation', required=True,
        ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        related='installation_id.company_id', store=True, index=True)
    name = fields.Char(string='Checklist Item', required=True)
    category = fields.Selection([
        ('site', 'Site Readiness'),
        ('material', 'Material'),
        ('install', 'Installation'),
        ('test', 'Testing'),
        ('customer', 'Customer'),
    ], string='Category', default='install')
    mandatory = fields.Boolean(string='Mandatory', default=True)
    answer = fields.Selection(
        CHECKLIST_ANSWER_SELECTION, string='Answer')
    remarks = fields.Char(string='Remarks')
    help_text = fields.Char(string='Guidance')

    @api.constrains('answer', 'remarks', 'mandatory')
    def _check_negative_answer(self):
        for line in self:
            if line.answer == 'no' and line.mandatory and not line.remarks:
                raise ValidationError(_(
                    'Please explain in the remarks why the mandatory item '
                    '"%s" could not be completed.', line.name))
