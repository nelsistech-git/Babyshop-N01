# -*- coding: utf-8 -*-
"""Proposal management, approval, quotation integration and customer
acceptance (SRS 22 - 26, 60, 61)."""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

PROPOSAL_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('hod_approval', 'HOD Review'),
    ('approved', 'Approved'),
    ('sent', 'Offer Sent'),
    ('accepted', 'Customer Accepted'),
    ('refused', 'Customer Rejected'),
    ('rejected', 'Rejected by HOD'),
    ('revised', 'Superseded'),
    ('cancelled', 'Cancelled'),
]

ACCEPTANCE_METHOD_SELECTION = [
    ('internal', 'Internal Confirmation'),
    ('signed', 'Signed Acceptance Uploaded'),
    ('quotation', 'Odoo Quotation Confirmation'),
    ('portal', 'Customer Portal Acceptance'),
]


class GcErmProposal(models.Model):
    _name = 'gc.erm.proposal'
    _description = 'GC ERM Commercial Proposal'
    _inherit = ['gc.erm.document.mixin']
    _order = 'proposal_date desc, id desc'

    _gc_sequence_code = 'gc.erm.proposal'
    _gc_sla_parameter = 'gc_erm.sla_proposal_days'
    _gc_closed_states = ('accepted', 'refused', 'rejected', 'revised', 'cancelled')

    state = fields.Selection(
        PROPOSAL_STATE_SELECTION, string='Status', default='draft', required=True,
        copy=False, tracking=True, index=True, group_expand='_group_expand_state')

    # ------------------------------------------------------------------
    # References (SRS 22)
    # ------------------------------------------------------------------
    lead_id = fields.Many2one(
        'gc.erm.lead', string='Lead', ondelete='restrict', index=True,
        tracking=True)
    survey_id = fields.Many2one(
        'gc.erm.survey', string='Survey', ondelete='restrict', index=True)
    technical_report_id = fields.Many2one(
        'gc.erm.technical.report', string='Technical Report',
        ondelete='restrict', index=True, tracking=True)
    boq_id = fields.Many2one(
        'gc.erm.boq', string='BOQ', ondelete='restrict', index=True)
    boq_total_cost = fields.Monetary(
        string='Internal Cost', related='boq_id.total_cost', store=True,
        currency_field='currency_id')

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    proposal_date = fields.Date(
        string='Proposal Date', default=fields.Date.context_today, required=True,
        tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, index=True,
        tracking=True)
    contact_id = fields.Many2one('res.partner', string='Contact')
    salesperson_id = fields.Many2one(
        'res.users', string='Salesperson', required=True,
        default=lambda self: self.env.user, tracking=True, index=True)
    team_id = fields.Many2one('crm.team', string='Sales Team')
    validity_date = fields.Date(
        string='Valid Until', default=lambda self: self._default_validity_date(),
        tracking=True)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms')
    contract_duration = fields.Integer(string='Contract Duration (months)',
                                       default=12)
    service_start_date = fields.Date(string='Service Start Date')
    expected_golive_date = fields.Date(string='Expected Go-Live Date')

    technical_scope = fields.Html(string='Technical Scope', sanitize=True)
    commercial_scope = fields.Html(string='Commercial Scope', sanitize=True)
    remarks = fields.Text(string='Remarks')
    terms_conditions = fields.Html(string='Terms & Conditions', sanitize=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'gc_proposal_attachment_rel', 'proposal_id',
        'attachment_id', string='Attachments')

    # ------------------------------------------------------------------
    # Versioning (SRS 61)
    # ------------------------------------------------------------------
    version = fields.Integer(string='Version', default=1, readonly=True, copy=False)
    revision_of_id = fields.Many2one(
        'gc.erm.proposal', string='Revision Of', readonly=True, copy=False,
        ondelete='set null', index=True)
    revision_ids = fields.One2many(
        'gc.erm.proposal', 'revision_of_id', string='Revisions')
    revision_count = fields.Integer(compute='_compute_revision_count')

    # ------------------------------------------------------------------
    # Lines and amounts
    # ------------------------------------------------------------------
    line_ids = fields.One2many(
        'gc.erm.proposal.line', 'proposal_id', string='Products & Services',
        copy=True)
    global_discount = fields.Float(string='Global Discount (%)', default=0.0)
    amount_untaxed = fields.Monetary(
        string='Untaxed Amount', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    amount_discount = fields.Monetary(
        string='Discount', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    amount_tax = fields.Monetary(
        string='Taxes', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    amount_total = fields.Monetary(
        string='Total', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    margin_amount = fields.Monetary(
        string='Margin', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    margin_percentage = fields.Float(
        string='Margin (%)', compute='_compute_amounts', store=True,
        digits=(16, 2))

    # ------------------------------------------------------------------
    # Quotation / acceptance (SRS 25 / 26)
    # ------------------------------------------------------------------
    sale_order_id = fields.Many2one(
        'sale.order', string='Quotation / Sales Order', readonly=True,
        copy=False, index=True, tracking=True)
    sale_order_state = fields.Selection(
        related='sale_order_id.state', string='Order Status')
    acceptance_method = fields.Selection(
        ACCEPTANCE_METHOD_SELECTION, string='Acceptance Method', readonly=True,
        copy=False)
    acceptance_date = fields.Date(
        string='Acceptance Date', readonly=True, copy=False)
    accepted_by = fields.Char(string='Accepted By', readonly=True, copy=False)
    acceptance_remarks = fields.Text(string='Acceptance Remarks', readonly=True,
                                     copy=False)
    acceptance_attachment_ids = fields.Many2many(
        'ir.attachment', 'gc_proposal_acceptance_attachment_rel', 'proposal_id',
        'attachment_id', string='Acceptance Documents', copy=False)
    work_order_ids = fields.One2many(
        'gc.erm.work.order', 'proposal_id', string='Work Orders')
    work_order_count = fields.Integer(compute='_compute_work_order_count')
    is_expired = fields.Boolean(
        string='Expired', compute='_compute_is_expired', store=True)

    # ------------------------------------------------------------------
    # Defaults / compute
    # ------------------------------------------------------------------
    @api.model
    def _default_validity_date(self):
        days = self.env['ir.config_parameter'].sudo().get_param(
            'gc_erm.proposal_validity_days', '30')
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = 30
        return fields.Date.add(fields.Date.context_today(self), days=days)

    @api.model
    def _group_expand_state(self, states, domain, order=None):
        return [key for key, _label in PROPOSAL_STATE_SELECTION]

    @api.depends('line_ids.price_subtotal', 'line_ids.price_tax',
                 'line_ids.discount_amount', 'line_ids.cost_subtotal',
                 'global_discount', 'currency_id')
    def _compute_amounts(self):
        for proposal in self:
            lines = proposal.line_ids
            untaxed = sum(lines.mapped('price_subtotal'))
            taxes = sum(lines.mapped('price_tax'))
            line_discount = sum(lines.mapped('discount_amount'))
            global_amount = untaxed * (proposal.global_discount or 0.0) / 100.0
            net = untaxed - global_amount
            if proposal.global_discount and untaxed:
                taxes = taxes * (net / untaxed)
            proposal.amount_untaxed = net
            proposal.amount_discount = line_discount + global_amount
            proposal.amount_tax = taxes
            proposal.amount_total = net + taxes
            cost = sum(lines.mapped('cost_subtotal'))
            proposal.margin_amount = net - cost
            proposal.margin_percentage = (
                proposal.margin_amount / net * 100.0) if net else 0.0

    @api.depends('revision_ids')
    def _compute_revision_count(self):
        for proposal in self:
            proposal.revision_count = len(proposal.revision_ids)

    @api.depends('work_order_ids')
    def _compute_work_order_count(self):
        for proposal in self:
            proposal.work_order_count = len(proposal.work_order_ids)

    @api.depends('validity_date', 'state')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for proposal in self:
            proposal.is_expired = bool(
                proposal.validity_date and proposal.validity_date < today
                and proposal.state in ('approved', 'sent'))

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for proposal in self:
            if proposal.partner_id:
                proposal.payment_term_id = proposal.partner_id.property_payment_term_id
                if proposal.partner_id.child_ids and not proposal.contact_id:
                    proposal.contact_id = proposal.partner_id.child_ids[0]

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('global_discount')
    def _check_global_discount(self):
        for proposal in self:
            if not 0.0 <= proposal.global_discount <= 100.0:
                raise ValidationError(_(
                    'The global discount must be between 0 and 100 percent.'))

    @api.constrains('validity_date', 'proposal_date')
    def _check_validity(self):
        for proposal in self:
            if proposal.validity_date and proposal.proposal_date and \
                    proposal.validity_date < proposal.proposal_date:
                raise ValidationError(_(
                    'The validity date cannot be earlier than the proposal date.'))

    # ------------------------------------------------------------------
    # Locking (SRS 24 / BR-005)
    # ------------------------------------------------------------------
    LOCKED_STATES = ('approved', 'sent', 'accepted', 'refused', 'rejected',
                     'revised', 'cancelled')
    EDITABLE_WHEN_LOCKED = (
        'state', 'message_follower_ids', 'message_ids', 'activity_ids', 'color',
        'sale_order_id', 'acceptance_method', 'acceptance_date', 'accepted_by',
        'acceptance_remarks', 'acceptance_attachment_ids', 'revision_of_id',
        'approved_by_id', 'approved_date', 'rejected_by_id', 'rejected_date',
        'rejection_reason', 'revision_reason', 'submitted_by_id',
        'submitted_date', 'sla_deadline', 'sla_state', 'is_expired',
    )

    def write(self, vals):
        if not self.env.context.get('gc_bypass_lock'):
            touched = set(vals) - set(self.EDITABLE_WHEN_LOCKED)
            if touched:
                for proposal in self:
                    if proposal.state in proposal.LOCKED_STATES:
                        raise UserError(_(
                            "Proposal %(name)s (v%(v)s) is %(state)s and cannot "
                            "be silently edited. Use 'Create Revision' to "
                            "produce a new version.",
                            name=proposal.name, v=proposal.version,
                            state=proposal._gc_state_label(proposal.state)))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Workflow (SRS 23 / 24)
    # ------------------------------------------------------------------
    def _check_submit_ready(self):
        """SRS 66 / BR-004."""
        self.ensure_one()
        missing = []
        if not self.partner_id:
            missing.append(_('Customer'))
        if not self.line_ids:
            missing.append(_('At least one product or service'))
        if not self.validity_date:
            missing.append(_('Validity date'))
        if float_is_zero(self.amount_total, precision_rounding=0.01):
            missing.append(_('Pricing'))
        if missing:
            raise UserError(_(
                'The proposal cannot be submitted. Missing: %s.',
                ', '.join(missing)))
        if self._survey_mandatory() and not self.technical_report_id:
            raise UserError(_(
                'Technical costing must be completed before proposal '
                'approval. Link the technical report to proposal %s.',
                self.name))
        if self.technical_report_id and \
                self.technical_report_id.state != 'submitted':
            raise UserError(_(
                'Technical report %s has not been submitted to Sales yet.',
                self.technical_report_id.name))
        return True

    def _survey_mandatory(self):
        self.ensure_one()
        services = (self.lead_id.service_ids | self.survey_id.service_ids)
        if not services:
            return bool(self.lead_id.survey_required)
        return any(services.mapped('survey_required'))

    def action_submit(self):
        for proposal in self:
            if proposal.state not in ('draft',):
                raise UserError(_('Only a draft proposal can be submitted.'))
            proposal._check_submit_ready()
            proposal._gc_transition(
                'hod_approval', comment=_('Submitted for HOD approval.'),
                allowed_from=('draft',),
                extra_vals={
                    'submitted_by_id': self.env.user.id,
                    'submitted_date': fields.Datetime.now(),
                    'rejection_reason': False,
                    'revision_reason': False,
                })
            approver = proposal._gc_approver()
            if approver:
                proposal._gc_schedule_activity(
                    approver,
                    summary=_('Approve Proposal %s', proposal.name),
                    note=_('Proposal %(name)s for %(partner)s '
                           '(%(amount)s) requires your approval.',
                           name=proposal.name,
                           partner=proposal.partner_id.display_name,
                           amount=proposal.amount_total),
                    days=int(proposal._gc_sla_days() or 1))
            proposal._gc_notify(
                'gc_erm_lead_to_billing.mail_template_gc_proposal_approval_request')
        return True

    def _gc_approver(self):
        self.ensure_one()
        rule = self.env['gc.erm.approval.matrix']._get_rule(
            'proposal', self.amount_total, self.company_id)
        if rule and rule.approver_user_ids:
            candidates = rule.approver_user_ids.filtered(
                lambda u: u != self.env.user)
            if candidates:
                return candidates[0]
        leader = self.team_id.user_id
        if leader and leader.has_group('gc_erm_lead_to_billing.group_gc_sales_hod'):
            return leader
        candidates = self._gc_users_in_group(
            'gc_erm_lead_to_billing.group_gc_sales_hod').filtered(
                lambda u: u != self.env.user)
        return candidates[0] if candidates else self.env['res.users']

    def action_approve(self):
        for proposal in self:
            if proposal.state != 'hod_approval':
                raise UserError(_(
                    'Only a proposal pending HOD review can be approved.'))
            proposal._gc_require_group(
                'gc_erm_lead_to_billing.group_gc_sales_hod',
                _('approve proposals'))
            proposal._gc_check_not_self_approval(proposal.salesperson_id)
            allowed, rule = self.env['gc.erm.approval.matrix'].check_approver(
                'proposal', proposal.amount_total, company=proposal.company_id)
            if not allowed:
                raise AccessError(_(
                    'Proposal %(name)s totals %(amount)s, which requires '
                    'approval by %(group)s.', name=proposal.name,
                    amount=proposal.amount_total,
                    group=rule.approver_group_id.name))
            proposal._gc_transition(
                'approved', comment=_('Proposal approved.'),
                allowed_from=('hod_approval',),
                extra_vals={
                    'approved_by_id': self.env.user.id,
                    'approved_date': fields.Datetime.now(),
                })
            proposal._gc_schedule_activity(
                proposal.salesperson_id,
                summary=_('Send offer %s to customer', proposal.name), days=1)
            proposal._gc_notify(
                'gc_erm_lead_to_billing.mail_template_gc_proposal_approved')
            proposal.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def _gc_apply_rejection(self, reason):
        self.ensure_one()
        self._gc_require_group(
            'gc_erm_lead_to_billing.group_gc_sales_hod', _('reject proposals'))
        self._gc_transition(
            'rejected', comment=reason, allowed_from=('hod_approval',),
            extra_vals={
                'rejected_by_id': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
                'rejection_reason': reason,
            })
        self._gc_notify(
            'gc_erm_lead_to_billing.mail_template_gc_proposal_rejected')
        self.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def _gc_apply_revision(self, reason):
        self.ensure_one()
        self._gc_require_group(
            'gc_erm_lead_to_billing.group_gc_sales_hod', _('request revisions'))
        self.with_context(gc_bypass_lock=True)._gc_transition(
            'draft', comment=_('Revision requested: %s', reason),
            allowed_from=('hod_approval',),
            extra_vals={'revision_reason': reason})
        self._gc_schedule_activity(
            self.salesperson_id, summary=_('Revise Proposal %s', self.name),
            note=reason, days=1)
        self.activity_feedback(['mail.mail_activity_data_todo'])
        return True

    def action_create_revision(self):
        """SRS 61 -- a new version, previous version stays accessible."""
        self.ensure_one()
        if self.state not in ('approved', 'sent', 'refused', 'rejected'):
            raise UserError(_(
                'Only an approved, sent, refused or rejected proposal can be '
                'revised.'))
        new_proposal = self.with_context(gc_bypass_lock=True).copy({
            'version': self.version + 1,
            'revision_of_id': self.id,
            'state': 'draft',
            'proposal_date': fields.Date.context_today(self),
            'sale_order_id': False,
        })
        self.with_context(gc_bypass_lock=True)._gc_transition(
            'revised', comment=_('Superseded by %(name)s (v%(v)s).',
                                 name=new_proposal.name, v=new_proposal.version))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Proposal Revision'),
            'res_model': 'gc.erm.proposal',
            'res_id': new_proposal.id,
            'view_mode': 'form',
        }

    def action_reset_draft(self):
        for proposal in self:
            if proposal.state not in ('rejected', 'cancelled', 'refused'):
                raise UserError(_(
                    'Only a rejected, refused or cancelled proposal can be '
                    'reset to draft.'))
            proposal.with_context(gc_bypass_lock=True)._gc_transition(
                'draft', comment=_('Reset to draft.'),
                extra_vals={
                    'rejection_reason': False,
                    'rejected_by_id': False,
                    'rejected_date': False,
                })
        return True

    def action_cancel(self):
        for proposal in self:
            if proposal.work_order_ids.filtered(
                    lambda w: w.state not in ('draft', 'cancelled')):
                raise UserError(_(
                    'Proposal %s has active work orders.', proposal.name))
            proposal.with_context(gc_bypass_lock=True)._gc_transition(
                'cancelled', comment=_('Proposal cancelled.'))
        return True

    # ------------------------------------------------------------------
    # Odoo quotation integration (SRS 25)
    # ------------------------------------------------------------------
    def action_create_quotation(self):
        """Generate a standard ``sale.order``; never a parallel engine."""
        self.ensure_one()
        if self.state not in ('approved', 'sent'):
            raise UserError(_(
                'The proposal must be approved before a quotation can be '
                'generated.'))
        if self.sale_order_id:
            return self.action_view_sale_order()
        order = self.env['sale.order'].create(self._prepare_sale_order_vals())
        self.with_context(gc_bypass_lock=True).write({'sale_order_id': order.id})
        self.message_post(body=_('Quotation %s generated from this proposal.',
                                 order.name))
        order.message_post(body=_('Created from ERM proposal %s.', self.name))
        return self.action_view_sale_order()

    def _prepare_sale_order_vals(self):
        self.ensure_one()
        order_lines = []
        for line in self.line_ids:
            order_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'product_uom_qty': line.quantity,
                'product_uom': (line.uom_id or line.product_id.uom_id).id,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'tax_id': [(6, 0, line.tax_ids.ids)],
                'sequence': line.sequence,
            }))
        return {
            'partner_id': self.partner_id.id,
            'partner_invoice_id': (self.contact_id or self.partner_id).id,
            'partner_shipping_id': (self.contact_id or self.partner_id).id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'user_id': self.salesperson_id.id,
            'team_id': self.team_id.id or False,
            'payment_term_id': self.payment_term_id.id or False,
            'validity_date': self.validity_date,
            'origin': self.name,
            'gc_proposal_id': self.id,
            'gc_lead_id': self.lead_id.id,
            'gc_survey_id': self.survey_id.id,
            'gc_boq_id': self.boq_id.id,
            'order_line': order_lines,
        }

    def action_send_offer(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_(
                'Only an approved proposal can be sent to the customer.'))
        if not self.sale_order_id:
            self.action_create_quotation()
        self._gc_transition(
            'sent', comment=_('Offer sent to the customer.'),
            allowed_from=('approved',))
        self._gc_notify('gc_erm_lead_to_billing.mail_template_gc_quotation_sent')
        return True

    # ------------------------------------------------------------------
    # Customer acceptance (SRS 26)
    # ------------------------------------------------------------------
    def action_open_acceptance_wizard(self):
        self.ensure_one()
        if self.state not in ('approved', 'sent'):
            raise UserError(_(
                'Customer acceptance can only be recorded on an approved or '
                'sent proposal.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Record Customer Acceptance'),
            'res_model': 'gc.erm.acceptance.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_proposal_id': self.id},
        }

    def action_customer_refused(self):
        for proposal in self:
            if proposal.state not in ('approved', 'sent'):
                raise UserError(_(
                    'Only a sent proposal can be marked as refused.'))
            proposal._gc_transition(
                'refused', comment=_('Customer rejected the offer.'),
                allowed_from=('approved', 'sent'))
            if proposal.sale_order_id and \
                    proposal.sale_order_id.state in ('draft', 'sent'):
                proposal.sale_order_id.action_cancel()
        return True

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_('No quotation has been generated yet.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
        }

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Work Orders'),
            'res_model': 'gc.erm.work.order',
            'view_mode': 'tree,form',
            'domain': [('proposal_id', '=', self.id)],
        }

    def action_view_revisions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Proposal Versions'),
            'res_model': 'gc.erm.proposal',
            'view_mode': 'tree,form',
            'domain': ['|', ('revision_of_id', '=', self.id), ('id', '=', self.id)],
        }

    @api.depends('name', 'version')
    def _compute_display_name(self):
        for proposal in self:
            proposal.display_name = '%s v%s' % (proposal.name, proposal.version)

    # ------------------------------------------------------------------
    # Cron (SRS 80 -- proposal expiry)
    # ------------------------------------------------------------------
    @api.model
    def _cron_expire_proposals(self):
        today = fields.Date.context_today(self)
        expired = self.search([
            ('state', 'in', ('approved', 'sent')),
            ('validity_date', '<', today),
        ])
        for proposal in expired:
            proposal._compute_is_expired()
            proposal.message_post(body=_(
                'This proposal expired on %s.', proposal.validity_date))
            if proposal.salesperson_id:
                proposal._gc_schedule_activity(
                    proposal.salesperson_id,
                    summary=_('Proposal %s expired', proposal.name),
                    note=_('Follow up with the customer or create a revision.'),
                    days=0)
        return True


class GcErmProposalLine(models.Model):
    _name = 'gc.erm.proposal.line'
    _description = 'GC ERM Proposal Line'
    _order = 'proposal_id, sequence, id'

    proposal_id = fields.Many2one(
        'gc.erm.proposal', string='Proposal', required=True, ondelete='cascade',
        index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        related='proposal_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='proposal_id.currency_id', store=True)
    partner_id = fields.Many2one(related='proposal_id.partner_id')
    state = fields.Selection(related='proposal_id.state', string='Status')

    product_id = fields.Many2one(
        'product.product', string='Product', required=True,
        domain="[('sale_ok', '=', True)]")
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(
        string='Quantity', default=1.0, required=True,
        digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    price_unit = fields.Monetary(
        string='Unit Price', currency_field='currency_id')
    discount = fields.Float(string='Discount (%)', default=0.0)
    tax_ids = fields.Many2many(
        'account.tax', 'gc_proposal_line_tax_rel', 'line_id', 'tax_id',
        string='Taxes', domain="[('type_tax_use', '=', 'sale')]")
    boq_line_id = fields.Many2one(
        'gc.erm.boq.line', string='BOQ Line', ondelete='set null')
    unit_cost = fields.Monetary(
        string='Unit Cost', compute='_compute_cost', store=True,
        currency_field='currency_id')
    cost_subtotal = fields.Monetary(
        string='Cost Subtotal', compute='_compute_cost', store=True,
        currency_field='currency_id')

    discount_amount = fields.Monetary(
        string='Discount Amount', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    price_subtotal = fields.Monetary(
        string='Subtotal', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    price_tax = fields.Monetary(
        string='Tax', compute='_compute_amounts', store=True,
        currency_field='currency_id')
    price_total = fields.Monetary(
        string='Total', compute='_compute_amounts', store=True,
        currency_field='currency_id')

    @api.depends('boq_line_id.line_cost', 'boq_line_id.quantity', 'quantity',
                 'product_id')
    def _compute_cost(self):
        for line in self:
            if line.boq_line_id:
                unit = (line.boq_line_id.line_cost / line.boq_line_id.quantity) \
                    if line.boq_line_id.quantity else 0.0
            else:
                unit = line.product_id.standard_price
            line.unit_cost = unit
            line.cost_subtotal = unit * line.quantity

    @api.depends('price_unit', 'quantity', 'discount', 'tax_ids', 'currency_id')
    def _compute_amounts(self):
        for line in self:
            gross = line.price_unit * line.quantity
            line.discount_amount = gross * (line.discount or 0.0) / 100.0
            net = gross - line.discount_amount
            if line.tax_ids:
                taxes = line.tax_ids.compute_all(
                    line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                    currency=line.currency_id or line.company_id.currency_id,
                    quantity=line.quantity,
                    product=line.product_id,
                    partner=line.partner_id)
                line.price_subtotal = taxes['total_excluded']
                line.price_tax = taxes['total_included'] - taxes['total_excluded']
                line.price_total = taxes['total_included']
            else:
                line.price_subtotal = net
                line.price_tax = 0.0
                line.price_total = net

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id
            if not product:
                continue
            line.name = product.display_name
            line.uom_id = product.uom_id
            if not line.price_unit:
                line.price_unit = product.list_price
            line.tax_ids = [(6, 0, product.taxes_id.filtered(
                lambda t: t.company_id == (line.company_id or self.env.company)).ids)]

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if float_compare(line.quantity, 0.0, precision_digits=4) <= 0:
                raise ValidationError(_(
                    'The quantity of line "%s" must be greater than zero.',
                    line.name or ''))

    @api.constrains('discount')
    def _check_discount(self):
        for line in self:
            if not 0.0 <= line.discount <= 100.0:
                raise ValidationError(_(
                    'The discount must be between 0 and 100 percent.'))
