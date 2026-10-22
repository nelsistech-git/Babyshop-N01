# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentDocument(models.Model):
    """Central, cross-module document register — SRS sections 7-19, 29-31,
    36-38.

    This is deliberately NOT a replacement for the Binary/attachment=True
    document fields already living on other modules' own models
    (garment.style.document, garment.supplier.document, garment.hr.document,
    garment.tech.attachment, garment.compliance.document, garment.order.
    document, garment.lc.document, garment.shipment.document ...). Those
    stay exactly as they are. This model is an OPTIONAL, generic central
    register that any record of any module can be listed into, through a
    generic ``res_model``/``res_id`` reference — the same pattern Odoo's
    own ``ir.attachment`` / Documents app uses — so a document controller
    gets one searchable place to see, route for approval and track expiry
    for documents that matter company-wide, without this module ever
    needing a hard dependency on the module that owns the underlying
    business record. See ``garment.document.mixin`` for the smart-button
    half of this pattern."""
    _name = 'garment.document'
    _description = 'Document'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'document_no desc'

    document_no = fields.Char(string='Document No.', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Document Name', required=True, tracking=True)
    category_id = fields.Many2one('garment.document.category', string='Category / Folder', tracking=True)
    department = fields.Selection([
        ('commercial', 'Commercial'),
        ('production', 'Production'),
        ('hr', 'HR'),
        ('compliance', 'Compliance'),
        ('finance', 'Finance'),
        ('quality', 'Quality'),
        ('logistics', 'Logistics'),
        ('general', 'General / Other'),
    ], string='Department', tracking=True)
    document_type = fields.Selection([
        ('contract', 'Contract'),
        ('invoice', 'Invoice'),
        ('certificate', 'Certificate'),
        ('report', 'Report'),
        ('policy', 'Policy'),
        ('drawing', 'Drawing'),
        ('technical', 'Technical Document'),
        ('other', 'Other'),
    ], string='Document Type', tracking=True,
        help='Classification hint (SRS section 10) — which document type this is, '
             'used to pick a matching category and retention policy.')
    tag_ids = fields.Many2many('garment.document.tag', string='Tags')
    keywords = fields.Char(string='Search Keywords',
                            help='Extra free-text keywords for full-text search — SRS section 11.')

    owner_id = fields.Many2one('res.users', string='Owner', default=lambda s: s.env.user, tracking=True)
    responsible_id = fields.Many2one('res.users', string='Responsible (Renewal)', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    # Generic cross-module link (SRS section 57 — Integration with ERP Modules).
    # This is the key design decision of the module: a garment.document can be
    # attached to ANY other model's record (a style, a PO, an LC, a compliance
    # certificate, ...) without this module ever depending on that module.
    res_model_id = fields.Many2one('ir.model', string='Related Model', ondelete='cascade',
                                    help='Optional link to the record this document belongs to in '
                                         'another module (e.g. a garment.style, garment.supplier, '
                                         'garment.order ...). Kept generic so this module never has '
                                         'to depend on the module that owns the record.')
    res_model = fields.Char(string='Related Model Name', related='res_model_id.model', store=True, readonly=True)
    res_id = fields.Integer(string='Related Record ID')
    res_name = fields.Char(string='Related Record', compute='_compute_res_name')

    # File
    file = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
    file_size = fields.Integer(string='File Size (bytes)', compute='_compute_file_size', store=True)

    # Version control (SRS section 12)
    version_ids = fields.One2many('garment.document.version', 'document_id', string='Versions')
    version_count = fields.Integer(compute='_compute_version_count')
    version = fields.Char(string='Current Version', default='1.0', copy=False, tracking=True)

    # Check-in / Check-out (SRS section 13)
    is_locked = fields.Boolean(string='Checked Out', default=False, copy=False, tracking=True)
    locked_by_id = fields.Many2one('res.users', string='Checked Out By', readonly=True, copy=False)
    locked_date = fields.Datetime(string='Checked Out On', readonly=True, copy=False)

    # Security / access control (SRS sections 6, 29-30, 56)
    security_level = fields.Selection([
        ('public', 'Public — All Employees'),
        ('internal', 'Internal — Company Employees'),
        ('confidential', 'Confidential — Department Restricted'),
        ('highly_confidential', 'Highly Confidential — Management Only'),
    ], string='Security Level', default='internal', required=True, tracking=True)
    allowed_group_ids = fields.Many2many(
        'res.groups', 'garment_document_allowed_group_rel', 'document_id', 'group_id',
        string='Additional Groups Allowed')
    allowed_user_ids = fields.Many2many(
        'res.users', 'garment_document_allowed_user_rel', 'document_id', 'user_id',
        string='Additional Users Allowed',
        help='Also used to grant portal users (buyers/suppliers) read access to a document '
             'through the portal share record rule.')
    is_password_protected = fields.Boolean(string='Password Protected')
    access_password = fields.Char(string='Access Password')

    # Lifecycle status (SRS sections 8, 14)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)

    # Expiry / retention (SRS sections 17, 44, 50, 55)
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    renewal_reminder_days = fields.Integer(string='Remind Before (Days)', default=30)
    expiry_status = fields.Selection([
        ('no_expiry', 'No Expiry'),
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Expiry Status', compute='_compute_expiry_status', store=True)
    retention_policy_id = fields.Many2one('garment.document.retention.policy', string='Retention Policy',
                                           tracking=True)

    # Configurable, generic multi-step approval workflow (SRS sections 14-16,
    # 27-28, 41-45). Deliberately modeled without a separate "approval
    # request" record: the running state (current step, completed steps)
    # lives directly on the document, and every step decision is written to
    # the access log for a full audit trail — see action_submit_for_approval
    # / action_approve_step / action_reject_step below.
    workflow_id = fields.Many2one('garment.document.approval.workflow', string='Approval Workflow', tracking=True)
    current_step_id = fields.Many2one('garment.document.approval.workflow.step', string='Current Step',
                                       readonly=True, copy=False,
                                       help='The step awaiting action. Only meaningful for a Sequential '
                                            'workflow — a Parallel workflow waits on every Pending Step '
                                            'at once.')
    completed_step_ids = fields.Many2many(
        'garment.document.approval.workflow.step', 'garment_document_completed_step_rel',
        'document_id', 'step_id', string='Completed Steps', readonly=True, copy=False)
    pending_step_ids = fields.Many2many(
        'garment.document.approval.workflow.step', string='Pending Steps',
        compute='_compute_pending_steps')

    # Audit trail (SRS section 31)
    access_log_ids = fields.One2many('garment.document.access.log', 'document_id', string='Access Log')
    view_count = fields.Integer(string='Views', compute='_compute_access_counts')
    download_count = fields.Integer(string='Downloads', compute='_compute_access_counts')

    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('document_no_uniq', 'unique(document_no, company_id)', 'Document Number must be unique per company!'),
    ]

    @api.onchange('retention_policy_id', 'issue_date')
    def _onchange_retention_policy(self):
        for rec in self:
            if rec.retention_policy_id and rec.issue_date and not rec.expiry_date:
                computed = rec.retention_policy_id.compute_expiry_date(rec.issue_date)
                if computed:
                    rec.expiry_date = computed

    @api.depends('res_model', 'res_id')
    def _compute_res_name(self):
        for rec in self:
            name = False
            if rec.res_model and rec.res_id and rec.res_model in self.env:
                target = self.env[rec.res_model].browse(rec.res_id).exists()
                if target:
                    name = target.display_name
            rec.res_name = name

    @api.depends('file')
    def _compute_file_size(self):
        for rec in self:
            rec.file_size = len(rec.file) if rec.file else 0

    def _compute_version_count(self):
        for rec in self:
            rec.version_count = len(rec.version_ids)

    @api.depends('workflow_id.step_ids', 'completed_step_ids')
    def _compute_pending_steps(self):
        for rec in self:
            rec.pending_step_ids = (rec.workflow_id.step_ids - rec.completed_step_ids) if rec.workflow_id \
                else self.env['garment.document.approval.workflow.step']

    def _compute_access_counts(self):
        for rec in self:
            rec.view_count = len(rec.access_log_ids.filtered(lambda l: l.action == 'view'))
            rec.download_count = len(rec.access_log_ids.filtered(lambda l: l.action == 'download'))

    @api.depends('expiry_date')
    def _compute_expiry_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.expiry_date:
                rec.expiry_status = 'no_expiry'
            elif rec.expiry_date < today:
                rec.expiry_status = 'expired'
            elif (rec.expiry_date - today).days <= (rec.renewal_reminder_days or 30):
                rec.expiry_status = 'expiring_soon'
            else:
                rec.expiry_status = 'valid'

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/my/documents/%s' % rec.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('document_no', _('New')) == _('New'):
                vals['document_no'] = self.env['ir.sequence'].next_by_code('garment.document') or _('New')
        records = super().create(vals_list)
        for rec in records:
            if rec.file:
                rec._create_version(note=_('Initial upload'))
        return records

    def write(self, vals):
        if 'file' in vals and not self.env.context.get('skip_lock_check'):
            for rec in self:
                if rec.is_locked and rec.locked_by_id and rec.locked_by_id != self.env.user \
                        and not self.env.user.has_group('garment_document_management.group_document_manager'):
                    raise UserError(_('%s is checked out by %s. It cannot be edited until it is checked in.')
                                     % (rec.name, rec.locked_by_id.name))
        res = super().write(vals)
        if 'file' in vals:
            for rec in self:
                if rec.file:
                    rec._create_version(note=_('File updated'))
        return res

    def _create_version(self, note=False):
        self.ensure_one()
        Version = self.env['garment.document.version']
        last = self.version_ids.sorted('sequence', reverse=True)[:1]
        next_seq = (last.sequence + 1) if last else 1
        label = '1.%d' % (next_seq - 1) if next_seq > 1 else '1.0'
        Version.create({
            'document_id': self.id,
            'sequence': next_seq,
            'version_label': label,
            'file': self.file,
            'file_name': self.file_name,
            'created_by_id': self.env.user.id,
            'note': note or '',
        })
        self.version = label
        self._log_access('edit', note=note)

    def _log_access(self, action, note=False):
        self.env['garment.document.access.log'].sudo().create([{
            'document_id': rec.id,
            'user_id': self.env.user.id,
            'action': action,
            'note': note or '',
        } for rec in self])

    def action_check_out(self):
        for rec in self:
            if rec.is_locked:
                raise UserError(_('%s is already checked out.') % rec.name)
            rec.write({'is_locked': True, 'locked_by_id': self.env.user.id,
                       'locked_date': fields.Datetime.now()})
            rec._log_access('checkout')

    def action_check_in(self):
        for rec in self:
            if not rec.is_locked:
                continue
            rec.with_context(skip_lock_check=True).write(
                {'is_locked': False, 'locked_by_id': False, 'locked_date': False})
            rec._log_access('checkin')

    def action_view(self):
        """Explicit 'preview' entry point so a view is logged (SRS section 31)."""
        self.ensure_one()
        self._log_access('view')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'garment.document',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_download(self):
        self.ensure_one()
        self._log_access('download')
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/garment.document/%s/file/%s?download=true' % (self.id, self.file_name or ''),
            'target': 'self',
        }

    def action_archive_document(self):
        self.write({'status': 'archived', 'active': False})

    def action_view_versions(self):
        self.ensure_one()
        return self._stat_button_action('garment.document.version', self.version_ids.ids, _('Versions'))

    def action_view_access_log(self):
        self.ensure_one()
        return self._stat_button_action('garment.document.access.log', self.access_log_ids.ids, _('Access Log'))

    def _stat_button_action(self, res_model, ids, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': res_model,
            'view_mode': 'tree,form',
            'domain': [('id', 'in', ids)],
        }

    # ------------------------------------------------------------------
    # Approval workflow (SRS sections 14-16, 27-28, 41-45)
    # ------------------------------------------------------------------
    def action_submit_for_approval(self):
        for rec in self:
            if not rec.workflow_id:
                raise UserError(_('Select an Approval Workflow before submitting %s for approval.') % rec.name)
            if not rec.workflow_id.step_ids:
                raise UserError(_('Workflow %s has no approval steps configured.') % rec.workflow_id.name)
            first_step = rec.workflow_id.step_ids.sorted('sequence')[:1]
            rec.write({
                'status': 'pending_approval',
                'completed_step_ids': [(5, 0, 0)],
                'current_step_id': first_step.id if rec.workflow_id.approval_type == 'sequential' else False,
            })
            rec._notify_pending_approvers()

    def _actionable_steps_for_user(self):
        """The subset of this document's currently pending workflow steps
        the current user is allowed to action (SRS section 15 — Single /
        Multi-Level / Sequential / Parallel Approval)."""
        self.ensure_one()
        if not self.workflow_id or self.status != 'pending_approval':
            return self.env['garment.document.approval.workflow.step']
        pending = self.pending_step_ids
        if self.workflow_id.approval_type == 'sequential':
            pending = pending.filtered(lambda s: s.id == self.current_step_id.id)
        user = self.env.user
        return pending.filtered(
            lambda s: (s.approver_user_id and s.approver_user_id == user)
            or (not s.approver_user_id and s.approver_group_id and user in s.approver_group_id.users)
            or (not s.approver_user_id and not s.approver_group_id))

    def action_approve_step(self, comment=False):
        for rec in self:
            steps = rec._actionable_steps_for_user()
            if not steps:
                raise UserError(_('You are not an approver for the current pending step(s) of %s.') % rec.name)
            for step in steps:
                if step.requires_signature and not comment:
                    raise UserError(_('Step "%s" requires an electronic sign-off comment (your typed '
                                       'name/confirmation) before it can be approved.') % step.name)
                rec._log_access('approve', note=comment or step.name)
            rec.completed_step_ids = [(4, s.id) for s in steps]
            rec._advance_or_complete()

    def action_reject_step(self, comment=False):
        for rec in self:
            steps = rec._actionable_steps_for_user()
            if not steps:
                raise UserError(_('You are not an approver for the current pending step(s) of %s.') % rec.name)
            for step in steps:
                rec._log_access('reject', note=comment or step.name)
            rec.status = 'rejected'

    def _advance_or_complete(self):
        self.ensure_one()
        mandatory = self.workflow_id.step_ids.filtered('is_mandatory')
        if mandatory and all(step in self.completed_step_ids for step in mandatory):
            self.write({'status': 'approved', 'current_step_id': False})
            return
        if self.workflow_id.approval_type == 'sequential':
            next_step = self.pending_step_ids.sorted('sequence')[:1]
            self.current_step_id = next_step.id if next_step else False
            self._notify_pending_approvers()

    def _notify_pending_approvers(self):
        self.ensure_one()
        steps = self.pending_step_ids if self.workflow_id.approval_type == 'parallel' \
            else self.current_step_id
        for step in steps:
            approver = step.approver_user_id or (step.approver_group_id.users[:1]
                                                   if step.approver_group_id else False)
            if approver:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Approval required: %s') % self.name,
                    note=_('Please review and approve/reject step "%s".') % step.name,
                    user_id=approver.id)

    @api.model
    def _cron_check_expiring_documents(self):
        """SRS sections 17-18, 44, 51 — expiry reminders and retention
        actions. Posts a chatter message and schedules an activity for the
        responsible/owner user of every document that just crossed into its
        reminder window or has expired, then applies the governing
        retention policy's configured action (notify / auto-archive /
        lock)."""
        docs = self.search([('expiry_date', '!=', False), ('status', 'not in', ('expired', 'archived'))])
        for doc in docs:
            if doc.expiry_status == 'expired' and doc.status != 'expired':
                doc.status = 'expired'
                doc.message_post(body=_('Document %s has expired on %s.') % (doc.name, doc.expiry_date))
                action = doc.retention_policy_id.action_on_expiry if doc.retention_policy_id else 'notify'
                if action == 'archive':
                    doc.action_archive_document()
                elif action == 'lock':
                    doc.write({'is_locked': True, 'locked_by_id': self.env.user.id,
                               'locked_date': fields.Datetime.now()})
            elif doc.expiry_status == 'expiring_soon':
                user = doc.responsible_id or doc.owner_id
                if user:
                    doc.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_('Renew document: %s') % doc.name,
                        note=_('%s expires on %s. Please renew before expiry.') % (doc.name, doc.expiry_date),
                        user_id=user.id)
        return True
