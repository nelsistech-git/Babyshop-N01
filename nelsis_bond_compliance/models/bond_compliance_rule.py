# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
from datetime import date, timedelta
from urllib.parse import urlparse

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .bond_compliance_common import (
    CODE_RE, G_APPROVER, G_OFFICER, G_REVIEWER, URL_RE, WORKFLOW_CTX,
    check_segregation, clear_activities, get_warning_days, normalize_code,
    require_any_group, schedule_group_activity, schedule_user_activity,
)

SUMMARY_REVIEW = 'Review compliance rule'
SUMMARY_APPROVE = 'Approve compliance rule'
SUMMARY_EXPIRING = 'Compliance rule expiring'
SUMMARY_EXPIRED = 'Compliance rule expired'
SUMMARY_REREVIEW = 'Compliance rule re-verification due'
SUMMARY_LEGAL = 'Legal interpretation pending verification'
SUMMARY_REVISE = 'Revise rejected compliance rule'

RULE_STATUS = [
    ('draft', 'Draft'),
    ('under_review', 'Under Review'),
    ('reviewed', 'Reviewed'),
    ('approved', 'Approved'),
    ('active', 'Active'),
    ('superseded', 'Superseded'),
    ('rejected', 'Rejected'),
]

# Fields that define the legal content of a rule: editable in draft only.
CONTENT_FIELDS = {
    'name', 'code', 'rule_category_id', 'official_reference', 'source_url',
    'publication_date', 'effective_from', 'applicability',
    'applicable_category_ids', 'description', 'parameter_ids',
    'required_document_type_ids',
}
# Professional-verification fields: editable until the rule is approved.
REVIEW_FIELDS = {
    'requires_professional_verification', 'professional_verification_note',
    'professional_verified_by', 'professional_verified_date',
}
# Fields only the workflow methods may change.
PROTECTED_FIELDS = {
    'verification_status', 'reviewed_by', 'reviewed_date', 'approved_by',
    'approved_date', 'submitted_by', 'submitted_date', 'previous_version_id',
    'version', 'rejection_reason',
}


class BondComplianceRule(models.Model):
    _name = 'bond.compliance.rule'
    _description = 'Bond Regulatory Compliance Rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code, version desc'
    _rec_names_search = ['name', 'code', 'official_reference']

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    name = fields.Char(string='Rule Title', required=True, tracking=True)
    code = fields.Char(
        string='Rule Code', required=True, index=True, tracking=True,
        help='Stable technical code shared by all versions of the same rule. '
             'Other modules evaluate rules by this code.')
    version = fields.Integer(default=1, readonly=True, copy=False, index=True)
    rule_category_id = fields.Many2one(
        'bond.compliance.rule.category', string='Rule Category', required=True,
        ondelete='restrict', tracking=True)
    official_reference = fields.Char(
        string='Official Rule / SRO Reference', tracking=True,
        help='Official reference as published, e.g. the SRO number and year. '
             'Must be copied from the official source.')
    source_url = fields.Char(string='Official Source URL', tracking=True)
    source_is_official_domain = fields.Boolean(compute='_compute_source_is_official_domain')
    publication_date = fields.Date(tracking=True)
    effective_from = fields.Date(tracking=True)
    effective_to = fields.Date(tracking=True)
    effective_state = fields.Selection(
        [('not_in_force', 'Not in Force'), ('scheduled', 'Scheduled'),
         ('in_force', 'In Force'), ('expired', 'Expired')],
        compute='_compute_effective_state', string='Effective State')
    applicability = fields.Text(
        string='Applicability Notes',
        help='Explain why and how the rule applies to the factory / license category.')
    applicable_category_ids = fields.Many2many(
        'bond.compliance.license.category', 'bond_compliance_rule_license_cat_rel',
        'rule_id', 'category_id', string='Applicable License / Factory Categories')
    description = fields.Text(string='Rule Description')
    parameter_ids = fields.One2many(
        'bond.compliance.rule.parameter', 'rule_id', string='Validation Parameters', copy=True)
    required_document_type_ids = fields.Many2many(
        'bond.compliance.document.type', 'bond_compliance_rule_doc_type_rel',
        'rule_id', 'document_type_id', string='Required Documents')

    verification_status = fields.Selection(
        RULE_STATUS, default='draft', required=True, readonly=True, copy=False,
        tracking=True, index=True)
    submitted_by = fields.Many2one('res.users', readonly=True, copy=False)
    submitted_date = fields.Datetime(readonly=True, copy=False)
    reviewed_by = fields.Many2one('res.users', readonly=True, copy=False, tracking=True)
    reviewed_date = fields.Datetime(readonly=True, copy=False)
    approved_by = fields.Many2one('res.users', readonly=True, copy=False, tracking=True)
    approved_date = fields.Datetime(readonly=True, copy=False)
    rejection_reason = fields.Text(readonly=True, copy=False)

    requires_professional_verification = fields.Boolean(
        string='Requires Professional Verification', tracking=True,
        help='Tick when the legal interpretation is uncertain and must be confirmed by a '
             'qualified Bangladesh customs professional before approval.')
    professional_verification_note = fields.Text(string='Interpretation Under Verification')
    professional_verified_by = fields.Char(string='Verified By (Professional)')
    professional_verified_date = fields.Date(string='Professional Verification Date')
    next_review_date = fields.Date(
        string='Next Re-verification Date', tracking=True,
        help='Date by which the rule must be re-checked against the latest official text.')

    previous_version_id = fields.Many2one(
        'bond.compliance.rule', string='Previous Version', readonly=True, copy=False,
        ondelete='restrict', index=True)
    next_version_ids = fields.One2many(
        'bond.compliance.rule', 'previous_version_id', string='Next Versions')
    active = fields.Boolean(default=True, tracking=True)

    evaluation_count = fields.Integer(compute='_compute_counts')
    exception_count = fields.Integer(compute='_compute_counts')
    version_count = fields.Integer(compute='_compute_counts')

    _sql_constraints = [
        ('code_version_unique', 'unique(code, version)',
         'A rule code can only have one record per version number.'),
    ]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('name', 'code', 'version')
    def _compute_display_name(self):
        for rule in self:
            rule.display_name = '[%s v%s] %s' % (rule.code or '-', rule.version, rule.name or '')

    @api.depends('source_url')
    def _compute_source_is_official_domain(self):
        for rule in self:
            host = ''
            if rule.source_url:
                host = (urlparse(rule.source_url.strip()).hostname or '').lower()
            rule.source_is_official_domain = host == 'gov.bd' or host.endswith('.gov.bd')

    @api.depends('verification_status', 'effective_from', 'effective_to')
    def _compute_effective_state(self):
        today = fields.Date.context_today(self)
        for rule in self:
            if rule.verification_status not in ('active', 'superseded'):
                rule.effective_state = 'not_in_force'
            elif rule.effective_from and rule.effective_from > today:
                rule.effective_state = 'scheduled'
            elif rule.effective_to and rule.effective_to < today:
                rule.effective_state = 'expired'
            else:
                rule.effective_state = 'in_force'

    @api.depends()
    def _compute_counts(self):
        Evaluation = self.env['bond.compliance.evaluation'].sudo()
        Exception_ = self.env['bond.compliance.exception']
        Rule = self.with_context(active_test=False)
        for rule in self:
            rule.evaluation_count = Evaluation.search_count([('rule_id', '=', rule.id)])
            rule.exception_count = Exception_.search_count([('rule_id', '=', rule.id)])
            rule.version_count = Rule.search_count([('code', '=', rule.code)])

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('code')
    def _check_code_format(self):
        for rule in self:
            if not CODE_RE.match(rule.code or ''):
                raise ValidationError(_(
                    'Rule code "%s" is invalid. Use upper-case letters, digits, "_", "-" or "." '
                    'and start with a letter or digit.', rule.code))

    @api.constrains('source_url')
    def _check_source_url(self):
        for rule in self:
            if rule.source_url and not URL_RE.match(rule.source_url.strip()):
                raise ValidationError(_(
                    'Source URL "%s" is not a valid http(s) address.', rule.source_url))

    @api.constrains('effective_from', 'effective_to')
    def _check_effective_dates(self):
        for rule in self:
            if rule.effective_from and rule.effective_to and rule.effective_to < rule.effective_from:
                raise ValidationError(_(
                    'Rule %s: "Effective To" cannot be earlier than "Effective From".',
                    rule.display_name))

    @api.constrains('effective_to')
    def _check_effective_to_vs_history(self):
        """Ending a rule must never change the result of a past evaluation."""
        Evaluation = self.env['bond.compliance.evaluation'].sudo()
        for rule in self.filtered('effective_to'):
            later = Evaluation.search([
                ('rule_id', '=', rule.id), ('evaluated_on', '>', rule.effective_to)], limit=1)
            if later:
                raise ValidationError(_(
                    'Rule %(rule)s was already used for an evaluation dated %(date)s, which is '
                    'after the requested end date. Historical results must not change; choose a '
                    'later end date.', rule=rule.display_name, date=later.evaluated_on))

    @api.constrains('previous_version_id', 'code', 'version')
    def _check_previous_version(self):
        for rule in self.filtered('previous_version_id'):
            prev = rule.previous_version_id
            if prev.code != rule.code:
                raise ValidationError(_('A rule version must share its code with the previous version.'))
            if prev.version >= rule.version:
                raise ValidationError(_('The version number must be higher than the previous version.'))

    @api.constrains('verification_status', 'effective_from', 'applicable_category_ids',
                    'approved_by', 'approved_date', 'reviewed_by')
    def _check_approved_data(self):
        for rule in self:
            if rule.verification_status in ('approved', 'active', 'superseded'):
                if not (rule.effective_from and rule.applicable_category_ids
                        and rule.approved_by and rule.approved_date and rule.reviewed_by):
                    raise ValidationError(_(
                        'Rule %s cannot be approved or active without effective-from date, '
                        'applicable categories, reviewer and approver.', rule.display_name))

    @api.constrains('verification_status', 'effective_from', 'effective_to',
                    'applicable_category_ids', 'code', 'active')
    def _check_no_overlapping_versions(self):
        for rule in self:
            if rule.verification_status not in ('active', 'superseded'):
                continue
            others = self.with_context(active_test=False).search([
                ('code', '=', rule.code), ('id', '!=', rule.id),
                ('verification_status', 'in', ('active', 'superseded'))])
            my_categories = set(rule.applicable_category_ids.ids)
            for other in others:
                if not my_categories & set(other.applicable_category_ids.ids):
                    continue
                if self._ranges_overlap(rule.effective_from, rule.effective_to,
                                        other.effective_from, other.effective_to):
                    raise ValidationError(_(
                        'Rule %(rule)s overlaps in effective dates and license category with '
                        '%(other)s. Create a new version of the rule instead.',
                        rule=rule.display_name, other=other.display_name))

    @staticmethod
    def _ranges_overlap(a_from, a_to, b_from, b_to):
        a_from, b_from = a_from or date.min, b_from or date.min
        a_to, b_to = a_to or date.max, b_to or date.max
        return a_from <= b_to and b_from <= a_to

    # ------------------------------------------------------------------
    # ORM overrides (immutability and workflow protection)
    # ------------------------------------------------------------------
    def _status_label(self, status):
        return dict(self._fields['verification_status'].selection).get(status, status)

    def _check_write_permissions(self, vals):
        keys = set(vals)
        protected = keys & PROTECTED_FIELDS
        if protected:
            raise UserError(_(
                'These fields are managed by the compliance workflow and cannot be edited '
                'directly: %s', ', '.join(sorted(protected))))
        is_officer = self.env.su or self.env.user.has_group(G_OFFICER)
        for rule in self:
            status = rule.verification_status
            if keys & CONTENT_FIELDS:
                if status != 'draft':
                    raise UserError(_(
                        'Rule %(rule)s is "%(status)s" and its content is locked. Return it to '
                        'draft (before approval) or create a new version.',
                        rule=rule.display_name, status=self._status_label(status)))
                if not is_officer:
                    raise UserError(_('Only Compliance Officers can edit the content of a rule.'))
            if keys & REVIEW_FIELDS and status in ('approved', 'active', 'superseded'):
                raise UserError(_(
                    'Professional verification details are locked once a rule is approved.'))
            if 'effective_to' in vals:
                if status in ('draft',):
                    if not is_officer:
                        raise UserError(_('Only Compliance Officers can edit draft rules.'))
                elif status in ('approved', 'active'):
                    require_any_group(self.env, (G_APPROVER,), _('change the end date of an approved rule'))
                else:
                    raise UserError(_(
                        'The end date of a rule in status "%s" cannot be changed.',
                        self._status_label(status)))
            if vals.get('active') is False and status in ('approved', 'active'):
                raise UserError(_(
                    'An approved or active rule cannot be archived. Set an end date or '
                    'create a superseding version instead.'))

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        workflow = self.env.context.get(WORKFLOW_CTX)
        for vals in vals_list:
            if vals.get('code'):
                vals['code'] = normalize_code(vals['code'])
            if not workflow:
                if vals.get('verification_status', 'draft') != 'draft' or (
                        set(vals) & (PROTECTED_FIELDS - {'verification_status'})):
                    raise UserError(_(
                        'Rules are always created as drafts. Review, approval and activation '
                        'must follow the workflow.'))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get(WORKFLOW_CTX):
            self._check_write_permissions(vals)
        if vals.get('code'):
            vals = dict(vals, code=normalize_code(vals['code']))
        return super().write(vals)

    def copy(self, default=None):
        if not self.env.context.get(WORKFLOW_CTX):
            raise UserError(_('Rules cannot be duplicated. Use "Create New Version" instead.'))
        return super().copy(default)

    def unlink(self):
        for rule in self:
            if rule.verification_status not in ('draft', 'rejected'):
                raise UserError(_(
                    'Rule %s has passed review and is part of the audit history; it cannot be '
                    'deleted.', rule.display_name))
        return super().unlink()

    def _wf_write(self, vals):
        return self.with_context(**{WORKFLOW_CTX: True}).write(vals)

    # ------------------------------------------------------------------
    # Configuration validation
    # ------------------------------------------------------------------
    def _get_configuration_errors(self):
        """Return a list of blocking configuration problems (empty when valid)."""
        self.ensure_one()
        errors = []
        if not self.official_reference:
            errors.append(_('Official rule / SRO reference is required.'))
        if not self.source_url:
            errors.append(_('Official source URL is required.'))
        elif not URL_RE.match(self.source_url.strip()):
            errors.append(_('Source URL is not a valid http(s) address.'))
        if not self.effective_from:
            errors.append(_('Effective-from date is required.'))
        if not self.description:
            errors.append(_('Rule description is required.'))
        if not self.applicable_category_ids:
            errors.append(_(
                'At least one applicable license / factory category must be selected explicitly. '
                'Rules are never assumed to apply to every category.'))
        if not self.rule_category_id.active:
            errors.append(_('The rule category is archived.'))
        if self.requires_professional_verification and not self.professional_verification_note:
            errors.append(_(
                'Describe the legal interpretation that requires professional verification.'))
        for param in self.parameter_ids:
            if param.operator != 'none' and not param.value_is_set:
                errors.append(_('Parameter "%s" is used for validation but has no confirmed value.', param.name))
            if param.is_statutory:
                if not param.value_is_set:
                    errors.append(_('Statutory parameter "%s" has no confirmed value.', param.name))
                elif not param.source_note:
                    errors.append(_('Statutory parameter "%s" needs a source note (official clause).', param.name))
        return errors

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit_review(self):
        require_any_group(self.env, (G_OFFICER,), _('submit compliance rules for review'))
        for rule in self:
            if rule.verification_status != 'draft':
                raise UserError(_('Only draft rules can be submitted for review.'))
            errors = rule._get_configuration_errors()
            if errors:
                raise UserError(_('Rule %(rule)s cannot be submitted:\n- %(errors)s',
                                  rule=rule.display_name, errors='\n- '.join(errors)))
            rule._wf_write({
                'verification_status': 'under_review',
                'submitted_by': self.env.user.id,
                'submitted_date': fields.Datetime.now(),
            })
            rule.message_post(body=_('Submitted for review.'))
            schedule_group_activity(
                rule, G_REVIEWER, SUMMARY_REVIEW,
                note=_('Please verify this rule against the official source.'))
        return True

    def action_mark_reviewed(self):
        require_any_group(self.env, (G_REVIEWER,), _('review compliance rules'))
        for rule in self:
            if rule.verification_status != 'under_review':
                raise UserError(_('Only rules under review can be marked as reviewed.'))
            check_segregation(self.env, rule.submitted_by, _(
                'The reviewer must be a different person from the one who submitted the rule.'))
            rule._wf_write({
                'verification_status': 'reviewed',
                'reviewed_by': self.env.user.id,
                'reviewed_date': fields.Datetime.now(),
            })
            rule.message_post(body=_('Review completed.'))
            clear_activities(rule, [SUMMARY_REVIEW, SUMMARY_LEGAL])
            schedule_group_activity(
                rule, G_APPROVER, SUMMARY_APPROVE,
                note=_('Reviewed rule is waiting for approval.'))
        return True

    def action_approve(self):
        require_any_group(self.env, (G_APPROVER,), _('approve compliance rules'))
        for rule in self:
            if rule.verification_status != 'reviewed':
                raise UserError(_('Only reviewed rules can be approved.'))
            check_segregation(self.env, rule.reviewed_by, _(
                'The approver must be a different person from the reviewer.'))
            check_segregation(self.env, rule.submitted_by, _(
                'The approver must be a different person from the one who submitted the rule.'))
            if rule.requires_professional_verification and not (
                    rule.professional_verified_by and rule.professional_verified_date):
                raise UserError(_(
                    'Rule %s has an unresolved legal interpretation. Record the professional '
                    'verifier and verification date before approval.', rule.display_name))
            errors = rule._get_configuration_errors()
            if errors:
                raise UserError(_('Rule %(rule)s cannot be approved:\n- %(errors)s',
                                  rule=rule.display_name, errors='\n- '.join(errors)))
            rule._wf_write({
                'verification_status': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
            rule.message_post(body=_('Rule approved.'))
            clear_activities(rule, [SUMMARY_APPROVE])
        return True

    def action_activate(self):
        require_any_group(self.env, (G_APPROVER,), _('activate compliance rules'))
        for rule in self:
            if rule.verification_status != 'approved':
                raise UserError(_('Only approved rules can be activated.'))
            errors = rule._get_configuration_errors()
            if errors:
                raise UserError(_('Rule %(rule)s cannot be activated:\n- %(errors)s',
                                  rule=rule.display_name, errors='\n- '.join(errors)))
            previous = rule.previous_version_id
            if previous and previous.verification_status == 'active':
                if previous.effective_from and rule.effective_from <= previous.effective_from:
                    raise UserError(_(
                        'The new version must take effect after the previous version '
                        '(%s).', previous.effective_from))
                new_end = rule.effective_from - timedelta(days=1)
                if previous.effective_to and previous.effective_to < new_end:
                    new_end = previous.effective_to
                previous._wf_write({'verification_status': 'superseded', 'effective_to': new_end})
                previous.message_post(body=_(
                    'Superseded by %(rule)s, effective %(date)s.',
                    rule=rule.display_name, date=rule.effective_from))
            rule._wf_write({'verification_status': 'active'})
            rule.message_post(body=_('Rule activated.'))
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Rule'),
            'res_model': 'bond.compliance.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def action_reject(self, reason=None):
        reason = (reason or '').strip()
        if not reason:
            raise UserError(_('A rejection reason is required.'))
        require_any_group(self.env, (G_REVIEWER, G_APPROVER), _('reject compliance rules'))
        for rule in self:
            if rule.verification_status not in ('under_review', 'reviewed'):
                raise UserError(_('Only rules under review or reviewed can be rejected.'))
            submitter = rule.submitted_by
            rule._wf_write({
                'verification_status': 'rejected',
                'rejection_reason': reason,
                'reviewed_by': False,
                'reviewed_date': False,
            })
            rule.message_post(body=Markup('%s %s') % (_('Rule rejected. Reason:'), reason))
            clear_activities(rule, [SUMMARY_REVIEW, SUMMARY_APPROVE, SUMMARY_LEGAL])
            schedule_user_activity(rule, submitter, SUMMARY_REVISE, note=reason)
        return True

    def action_return_to_draft(self):
        require_any_group(self.env, (G_OFFICER, G_REVIEWER, G_APPROVER), _('return rules to draft'))
        for rule in self:
            if rule.verification_status not in ('under_review', 'reviewed', 'rejected'):
                raise UserError(_('Only rules under review, reviewed or rejected can be returned to draft.'))
            rule._wf_write({
                'verification_status': 'draft',
                'reviewed_by': False, 'reviewed_date': False,
                'submitted_by': False, 'submitted_date': False,
                'rejection_reason': False,
            })
            rule.message_post(body=_('Returned to draft.'))
            clear_activities(rule, [SUMMARY_REVIEW, SUMMARY_APPROVE, SUMMARY_LEGAL, SUMMARY_REVISE])
        return True

    def action_new_version(self):
        self.ensure_one()
        require_any_group(self.env, (G_OFFICER,), _('create a new rule version'))
        if self.verification_status not in ('active', 'superseded'):
            raise UserError(_('A new version can only be created from an active or superseded rule.'))
        if self.next_version_ids.filtered(lambda r: r.verification_status != 'rejected'):
            raise UserError(_('A newer version of this rule already exists.'))
        last = self.with_context(active_test=False).search(
            [('code', '=', self.code)], order='version desc', limit=1)
        new_rule = self.with_context(**{WORKFLOW_CTX: True}).copy({
            'version': last.version + 1,
            'previous_version_id': self.id,
            'verification_status': 'draft',
            'active': True,
            'effective_from': False,
            'effective_to': False,
            'publication_date': False,
            'official_reference': False,
            'source_url': False,
            'professional_verified_by': False,
            'professional_verified_date': False,
            'next_review_date': False,
        })
        new_rule.message_post(body=_(
            'Created as new version of %s. Enter the new official reference, source and '
            'effective date, then submit for review.', self.display_name))
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': new_rule.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_evaluations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Evaluations'),
            'res_model': 'bond.compliance.evaluation', 'view_mode': 'tree,form',
            'domain': [('rule_id', '=', self.id)],
        }

    def action_view_exceptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Exceptions'),
            'res_model': 'bond.compliance.exception', 'view_mode': 'tree,form',
            'domain': [('rule_id', '=', self.id)],
            'context': {'default_rule_id': self.id},
        }

    def action_view_versions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Rule Versions'),
            'res_model': self._name, 'view_mode': 'tree,form',
            'domain': [('code', '=', self.code)],
            'context': {'active_test': False},
        }

    # ------------------------------------------------------------------
    # Interface helpers used by bond.compliance.engine
    # ------------------------------------------------------------------
    def get_parameter_value(self, key, default=None):
        """Return the typed, confirmed value of a parameter, or ``default``."""
        self.ensure_one()
        param = self.parameter_ids.filtered(lambda p: p.key == key)[:1]
        if param and param.value_is_set:
            return param.get_value()
        return default

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_compliance_reminders(self):
        today = fields.Date.context_today(self)
        limit = today + timedelta(days=get_warning_days(self.env))
        Rule = self.sudo()

        expiring = Rule.search([
            ('verification_status', '=', 'active'),
            ('effective_to', '>=', today), ('effective_to', '<=', limit)])
        for rule in expiring:
            if not rule.next_version_ids.filtered(lambda r: r.verification_status != 'rejected'):
                schedule_group_activity(
                    rule, G_APPROVER, SUMMARY_EXPIRING,
                    note=_('This rule ends on %s. Prepare a successor version if still required.',
                           rule.effective_to),
                    deadline=rule.effective_to)

        expired = Rule.search([
            ('verification_status', '=', 'active'), ('effective_to', '<', today)])
        for rule in expired:
            if not rule.next_version_ids.filtered(lambda r: r.verification_status != 'rejected'):
                schedule_group_activity(
                    rule, G_APPROVER, SUMMARY_EXPIRED,
                    note=_('This rule ended on %s and has no successor version.', rule.effective_to))

        due = Rule.search([
            ('verification_status', '=', 'active'),
            ('next_review_date', '!=', False), ('next_review_date', '<=', limit)])
        for rule in due:
            schedule_group_activity(
                rule, G_REVIEWER, SUMMARY_REREVIEW,
                note=_('Re-check this rule against the latest official text.'),
                deadline=rule.next_review_date)

        pending = Rule.search([
            ('requires_professional_verification', '=', True),
            ('professional_verified_date', '=', False),
            ('verification_status', 'in', ('under_review', 'reviewed'))])
        for rule in pending:
            schedule_group_activity(
                rule, G_REVIEWER, SUMMARY_LEGAL,
                note=_('A legal interpretation is unresolved and blocks approval.'))
        return True
