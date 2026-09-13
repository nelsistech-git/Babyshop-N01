# -*- coding: utf-8 -*-
"""Common behaviour shared by every Grameen Cybernet ERM document.

The mixin centralises the parts of the SRS that are identical for all
documents so that they cannot drift apart between models:

* SRS 6.10  -- unique sequence per document
* SRS 6.6   -- important status changes must be logged
* SRS 6.9   -- chatter and activities on every important document
* SRS 62    -- audit trail fields (submitted / approved / rejected by-date)
* SRS 67    -- server side workflow security, no direct state jumping
* SRS 69    -- multi company
* SRS 81    -- SLA / aging
"""

import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


#: Presentation colours recommended by SRS 53.  Visual only -- the workflow
#: security is always enforced separately in Python.
GC_STATE_COLOURS = {
    'draft': 'muted',
    'new': 'info',
    'submitted': 'info',
    'pending': 'warning',
    'hod_approval': 'warning',
    'hod_review': 'warning',
    'in_progress': 'info',
    'material_pending': 'warning',
    'approved': 'success',
    'completed': 'success',
    'done': 'success',
    'rejected': 'danger',
    'cancelled': 'danger',
    'overdue': 'danger',
}

GC_SLA_SELECTION = [
    ('on_time', 'Within SLA'),
    ('at_risk', 'At Risk'),
    ('overdue', 'Overdue'),
]


class GcErmDocumentMixin(models.AbstractModel):
    """Abstract parent of every ERM document."""

    _name = 'gc.erm.document.mixin'
    _description = 'Grameen Cybernet ERM Document Mixin'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    # ------------------------------------------------------------------
    # Hooks that concrete models are expected to override
    # ------------------------------------------------------------------

    #: ``ir.sequence`` code used to build :attr:`name`.
    _gc_sequence_code = None
    #: Name of the state field. Kept configurable for safety.
    _gc_state_field = 'state'
    #: ``ir.config_parameter`` key holding the SLA duration, in days.
    _gc_sla_parameter = None
    #: States that are considered "closed" and therefore never overdue.
    _gc_closed_states = ('approved', 'completed', 'done', 'rejected', 'cancelled')

    # ------------------------------------------------------------------
    # Common fields
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        index=True, default=lambda self: _('New'),
        help='Unique document number generated from the configured sequence.')
    active = fields.Boolean(
        default=True,
        help='Uncheck to archive the document without deleting its history.')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, index=True,
        default=lambda self: self.env.company,
        help='Company owning this document. Records are filtered by company.')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
        help='Currency used for all monetary amounts of this document.')
    color = fields.Integer(string='Colour Index', default=0)

    # ---- Audit trail (SRS 62) ----------------------------------------
    submitted_by_id = fields.Many2one(
        'res.users', string='Submitted By', readonly=True, copy=False)
    submitted_date = fields.Datetime(
        string='Submitted On', readonly=True, copy=False)
    approved_by_id = fields.Many2one(
        'res.users', string='Approved By', readonly=True, copy=False)
    approved_date = fields.Datetime(
        string='Approved On', readonly=True, copy=False)
    rejected_by_id = fields.Many2one(
        'res.users', string='Rejected By', readonly=True, copy=False)
    rejected_date = fields.Datetime(
        string='Rejected On', readonly=True, copy=False)
    rejection_reason = fields.Text(
        string='Rejection Reason', readonly=True, copy=False,
        help='Mandatory explanation captured when the document was rejected.')
    revision_reason = fields.Text(
        string='Revision Comment', readonly=True, copy=False,
        help='Mandatory explanation captured when a revision was requested.')

    status_history_ids = fields.One2many(
        'gc.erm.status.history', string='Status History',
        compute='_compute_status_history_ids',
        help='Chronological log of every controlled state change.')
    status_history_count = fields.Integer(
        string='History Entries', compute='_compute_status_history_ids')

    # ---- SLA / aging (SRS 81) ----------------------------------------
    sla_deadline = fields.Datetime(
        string='SLA Deadline', readonly=True, copy=False,
        help='Deadline computed from the configured SLA for the current stage.')
    sla_state = fields.Selection(
        GC_SLA_SELECTION, string='SLA Status',
        compute='_compute_sla_state', store=True,
        help='Within SLA, At Risk (last 25% of the window) or Overdue.')
    days_open = fields.Integer(
        string='Age (days)', compute='_compute_days_open',
        help='Number of days since the document was created.')

    _sql_constraints = [
        ('gc_name_company_uniq', 'unique(name, company_id)',
         'The document reference must be unique per company.'),
    ]

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('name')
    def _compute_status_history_ids(self):
        History = self.env['gc.erm.status.history']
        for record in self:
            history = History.sudo().search([
                ('model_name', '=', record._name),
                ('res_id', '=', record.id or 0),
            ], order='create_date asc, id asc')
            record.status_history_ids = history
            record.status_history_count = len(history)

    @api.depends('sla_deadline')
    def _compute_sla_state(self):
        now = fields.Datetime.now()
        for record in self:
            state = record._gc_state()
            if not record.sla_deadline or state in record._gc_closed_states:
                record.sla_state = 'on_time'
                continue
            if now > record.sla_deadline:
                record.sla_state = 'overdue'
                continue
            create_date = record.create_date or now
            total = (record.sla_deadline - create_date).total_seconds()
            elapsed = (now - create_date).total_seconds()
            record.sla_state = 'at_risk' if total > 0 and elapsed / total >= 0.75 else 'on_time'

    def _compute_days_open(self):
        now = fields.Datetime.now()
        for record in self:
            record.days_open = (now - record.create_date).days if record.create_date else 0

    # ------------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) in (_('New'), '/', '', False) and self._gc_sequence_code:
                company_id = vals.get('company_id') or self.env.company.id
                sequence = self.env['ir.sequence'].with_company(company_id)
                vals['name'] = sequence.next_by_code(self._gc_sequence_code) or _('New')
        records = super().create(vals_list)
        for record in records:
            record._gc_apply_sla()
            record._gc_log_state(False, record._gc_state(), _('Document created.'))
        return records

    def unlink(self):
        """Only draft/cancelled documents may be deleted (SRS 62 auditability)."""
        for record in self:
            state = record._gc_state()
            if state and state not in ('draft', 'cancelled'):
                raise UserError(_(
                    "You cannot delete %(doc)s because it is in the '%(state)s' "
                    "stage. Cancel it instead so the audit trail is preserved.",
                    doc=record.display_name,
                    state=record._gc_state_label(state)))
        History = self.env['gc.erm.status.history'].sudo()
        History.search([
            ('model_name', '=', self._name), ('res_id', 'in', self.ids)]).unlink()
        return super().unlink()

    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault('name', _('New'))
        for field in ('submitted_by_id', 'submitted_date', 'approved_by_id',
                      'approved_date', 'rejected_by_id', 'rejected_date',
                      'rejection_reason', 'revision_reason', 'sla_deadline'):
            default.setdefault(field, False)
        return super().copy(default)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def _gc_state(self):
        self.ensure_one()
        return self[self._gc_state_field] if self._gc_state_field in self._fields else False

    def _gc_state_label(self, value):
        field = self._fields.get(self._gc_state_field)
        if not field:
            return value
        return dict(field._description_selection(self.env)).get(value, value)

    def _gc_log_state(self, old_state, new_state, comment=False):
        """Persist a controlled state change (SRS 6.6 / SRS 62)."""
        self.ensure_one()
        if old_state == new_state and old_state is not False:
            return self.env['gc.erm.status.history']
        return self.env['gc.erm.status.history'].sudo().create({
            'model_name': self._name,
            'res_id': self.id,
            'document_ref': self.name,
            'old_state': old_state or '',
            'new_state': new_state or '',
            'old_state_label': self._gc_state_label(old_state) if old_state else '',
            'new_state_label': self._gc_state_label(new_state) if new_state else '',
            'user_id': self.env.user.id,
            'change_date': fields.Datetime.now(),
            'comment': comment or '',
            'company_id': self.company_id.id if 'company_id' in self._fields else False,
        })

    def _gc_transition(self, new_state, comment=False, allowed_from=None, extra_vals=None):
        """Single controlled entry point for every state change.

        Direct writes to the state field from the UI are blocked by the views;
        this method is the only supported server-side transition so that the
        guard, the audit log and the SLA stay consistent (SRS 67).
        """
        self.ensure_one()
        old_state = self._gc_state()
        if allowed_from is not None and old_state not in allowed_from:
            raise UserError(_(
                "Invalid workflow transition for %(doc)s: a document in "
                "'%(current)s' cannot move to '%(target)s'.",
                doc=self.display_name,
                current=self._gc_state_label(old_state),
                target=self._gc_state_label(new_state)))
        vals = dict(extra_vals or {})
        vals[self._gc_state_field] = new_state
        self.write(vals)
        self._gc_log_state(old_state, new_state, comment)
        self._gc_apply_sla()
        return True

    # ------------------------------------------------------------------
    # Approval guards
    # ------------------------------------------------------------------
    def _gc_segregation_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'gc_erm.segregation_of_duties', 'True') in ('True', 'true', '1', True)

    def _gc_check_not_self_approval(self, owner_user):
        """SRS 7.1 / 67 -- a user may not approve their own document."""
        self.ensure_one()
        if not self._gc_segregation_enabled():
            return True
        owners = owner_user | self.create_uid | self.submitted_by_id
        if self.env.user in owners and not self.env.user.has_group(
                'gc_erm_lead_to_billing.group_gc_erm_admin'):
            raise AccessError(_(
                "Segregation of duties: you submitted or own %(doc)s, so you "
                "cannot approve it yourself. Please ask another authorised "
                "approver.", doc=self.display_name))
        return True

    def _gc_require_group(self, group_xmlid, action_label):
        if not self.env.user.has_group(group_xmlid):
            raise AccessError(_(
                "You are not allowed to %(action)s. This action requires a "
                "different security group.", action=action_label))
        return True

    # ------------------------------------------------------------------
    # Activities and notifications (SRS 54 / 55)
    # ------------------------------------------------------------------
    def _gc_schedule_activity(self, user, summary, note=False, days=1,
                              activity_xmlid='mail.mail_activity_data_todo'):
        self.ensure_one()
        if not user:
            return False
        activity_type = self.env.ref(activity_xmlid, raise_if_not_found=False)
        if not activity_type:
            return False
        return self.activity_schedule(
            act_type_xmlid=activity_xmlid,
            date_deadline=fields.Date.context_today(self) + timedelta(days=days),
            summary=summary,
            note=note or summary,
            user_id=user.id,
        )

    def _gc_notify(self, template_xmlid, force_send=False):
        """Send a configured mail template, silently skipping if removed."""
        self.ensure_one()
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            _logger.info('GC ERM: mail template %s not found, skipped.', template_xmlid)
            return False
        try:
            template.send_mail(self.id, force_send=force_send)
        except Exception as exc:  # pragma: no cover - never block the workflow
            _logger.warning('GC ERM: could not send %s for %s: %s',
                            template_xmlid, self.display_name, exc)
            return False
        return True

    def _gc_post_state_message(self, body):
        self.ensure_one()
        return self.message_post(body=body, message_type='notification',
                                 subtype_xmlid='mail.mt_note')

    # ------------------------------------------------------------------
    # SLA (SRS 81)
    # ------------------------------------------------------------------
    def _gc_sla_days(self):
        if not self._gc_sla_parameter:
            return 0
        raw = self.env['ir.config_parameter'].sudo().get_param(self._gc_sla_parameter, '0')
        try:
            return float(raw or 0)
        except (TypeError, ValueError):
            return 0

    def _gc_apply_sla(self):
        for record in self:
            days = record._gc_sla_days()
            if not days:
                continue
            if record._gc_state() in record._gc_closed_states:
                record.sla_deadline = False
            else:
                record.sla_deadline = fields.Datetime.now() + timedelta(days=days)
        return True

    # ------------------------------------------------------------------
    # Generic UI actions
    # ------------------------------------------------------------------
    def action_gc_open_reason_wizard(self, mode):
        """Open the shared reason wizard for reject / revision (SRS 11)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Document') if mode == 'reject' else _('Request Revision'),
            'res_model': 'gc.erm.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_mode': mode,
                'default_res_model': self._name,
                'default_res_id': self.id,
                'default_document_name': self.display_name,
            },
        }

    def action_gc_reject(self):
        return self.action_gc_open_reason_wizard('reject')

    def action_gc_request_revision(self):
        return self.action_gc_open_reason_wizard('revision')

    def action_gc_view_status_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Status History - %s', self.display_name),
            'res_model': 'gc.erm.status.history',
            'view_mode': 'tree,form',
            'domain': [('model_name', '=', self._name), ('res_id', '=', self.id)],
            'context': {'create': False, 'edit': False},
        }

    # ------------------------------------------------------------------
    # Helpers used by the concrete models
    # ------------------------------------------------------------------
    def _gc_users_in_group(self, group_xmlid):
        group = self.env.ref(group_xmlid, raise_if_not_found=False)
        if not group:
            return self.env['res.users']
        return group.users.filtered(
            lambda u: u.active and (
                not u.company_ids or self.company_id in u.company_ids))

    def _gc_first_user_in_group(self, group_xmlid):
        users = self._gc_users_in_group(group_xmlid)
        return users[0] if users else self.env['res.users']

    def _gc_group_partner_ids(self, group_xmlid):
        """Comma separated partner ids, for the ``partner_to`` of a template."""
        self.ensure_one()
        users = self._gc_users_in_group(group_xmlid)
        return ','.join(str(user.partner_id.id)
                        for user in users if user.partner_id)
