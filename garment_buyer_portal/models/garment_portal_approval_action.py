# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentPortalApprovalAction(models.Model):
    """Buyer Portal Approval Action (SRS sections 12, 26, 32) —
    garment.portal.approval.action.

    A single unified "Approvals inbox" record for a Tech Pack / Sample /
    Style approval step awaiting buyer sign-off. It never stores its own
    approval outcome as the source of truth - `action_apply_decision()`
    writes the buyer decision back onto the *real* approval record
    (garment.tech.approval / garment.sample.approval / garment.style.approval)
    and the parent document, matching "Approval Data" (SRS section 26):
    Approved By, Date, Comments, Version, Attachment.
    """
    _name = 'garment.portal.approval.action'
    _description = 'Buyer Portal Approval Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'requested_date desc'

    name = fields.Char(string='Approval Ref.', copy=False, readonly=True, default=lambda s: _('New'))

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Buyer Portal User', tracking=True,
                                  help='The buyer contact expected to (or who did) take this decision.')

    approval_type = fields.Selection([
        ('techpack', 'Tech Pack'),
        ('sample', 'Sample'),
        ('style', 'Style'),
    ], string='Approval Type', required=True, tracking=True)

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack')
    techpack_approval_id = fields.Many2one('garment.tech.approval', string='Tech Pack Approval Step',
                                            ondelete='cascade')
    sample_id = fields.Many2one('garment.sample', string='Sample')
    sample_approval_id = fields.Many2one('garment.sample.approval', string='Sample Approval Step',
                                          ondelete='cascade')
    style_id = fields.Many2one('garment.style', string='Style')
    style_approval_id = fields.Many2one('garment.style.approval', string='Style Approval Step',
                                         ondelete='cascade')

    order_id = fields.Many2one('garment.order', string='Related Order',
                                help='Optional context link so the approval also shows on the Order Details page.')

    version = fields.Char(string='Version')
    decision = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('revision_required', 'Revision Required'),
        ('rejected', 'Rejected'),
    ], string='Buyer Decision', default='pending', required=True, tracking=True)
    comments = fields.Text(string='Buyer Comments')
    attachment = fields.Binary(string='Attachment', attachment=True)
    attachment_filename = fields.Char(string='Attachment Filename')

    requested_date = fields.Datetime(string='Requested Date', default=fields.Datetime.now)
    decision_date = fields.Datetime(string='Decision Date', readonly=True, copy=False)
    ip_address = fields.Char(string='IP Address', readonly=True, copy=False)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('techpack_approval_uniq', 'unique(techpack_approval_id)',
         'A Tech Pack Approval Step can only have one portal approval action.'),
        ('sample_approval_uniq', 'unique(sample_approval_id)',
         'A Sample Approval Step can only have one portal approval action.'),
        ('style_approval_uniq', 'unique(style_approval_id)',
         'A Style Approval Step can only have one portal approval action.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.portal.approval.action') or _('New')
        return super().create(vals_list)

    @api.onchange('approval_type')
    def _onchange_approval_type(self):
        for rec in self:
            if rec.approval_type != 'techpack':
                rec.techpack_id = rec.techpack_approval_id = False
            if rec.approval_type != 'sample':
                rec.sample_id = rec.sample_approval_id = False
            if rec.approval_type != 'style':
                rec.style_id = rec.style_approval_id = False

    # ------------------------------------------------------------------
    # Inbox sync — called from the portal controller before /my/approvals
    # is rendered so every open buyer-facing approval step is represented.
    # ------------------------------------------------------------------
    @api.model
    def _sync_pending_for_buyer(self, buyer):
        if not buyer:
            return self.browse()
        created = self.browse()
        created |= self._sync_techpack_steps(buyer)
        created |= self._sync_sample_steps(buyer)
        created |= self._sync_style_steps(buyer)
        return created

    def _sync_techpack_steps(self, buyer):
        steps = self.env['garment.tech.approval'].search([
            ('techpack_id.buyer_id', '=', buyer.id),
            ('approval_stage', 'in', ('buyer_submission', 'buyer_review')),
            ('status', '=', 'pending'),
        ])
        created = self.browse()
        for step in steps:
            if not self.search_count([('techpack_approval_id', '=', step.id)]):
                created |= self.create({
                    'approval_type': 'techpack', 'buyer_id': buyer.id, 'partner_id': buyer.partner_id.id,
                    'techpack_id': step.techpack_id.id, 'techpack_approval_id': step.id,
                    'version': step.techpack_id.version,
                })
        return created

    def _sync_sample_steps(self, buyer):
        steps = self.env['garment.sample.approval'].search([
            ('sample_id.buyer_id', '=', buyer.id),
            ('approval_stage', 'in', ('buyer_submission', 'buyer_review')),
            ('status', '=', 'pending'),
        ])
        created = self.browse()
        for step in steps:
            if not self.search_count([('sample_approval_id', '=', step.id)]):
                created |= self.create({
                    'approval_type': 'sample', 'buyer_id': buyer.id, 'partner_id': buyer.partner_id.id,
                    'sample_id': step.sample_id.id, 'sample_approval_id': step.id,
                })
        return created

    def _sync_style_steps(self, buyer):
        steps = self.env['garment.style.approval'].search([
            ('style_id.buyer_id', '=', buyer.id),
            ('approval_step', '=', 'buyer_approval'),
            ('status', '=', 'pending'),
        ])
        created = self.browse()
        for step in steps:
            if not self.search_count([('style_approval_id', '=', step.id)]):
                created |= self.create({
                    'approval_type': 'style', 'buyer_id': buyer.id, 'partner_id': buyer.partner_id.id,
                    'style_id': step.style_id.id, 'style_approval_id': step.id,
                })
        return created

    # ------------------------------------------------------------------
    # Decision write-back (SRS sections 12, 26)
    # ------------------------------------------------------------------
    def action_apply_decision(self):
        for rec in self:
            if rec.decision == 'pending':
                raise UserError(_('Select Approve, Request Revision or Reject first.'))
            rec.decision_date = fields.Datetime.now()
            if rec.approval_type == 'techpack':
                rec._apply_techpack_decision()
            elif rec.approval_type == 'sample':
                rec._apply_sample_decision()
            elif rec.approval_type == 'style':
                rec._apply_style_decision()
            rec.message_post(body=_('Buyer decision recorded: %s') % dict(
                rec._fields['decision'].selection).get(rec.decision))
        return True

    def _apply_techpack_decision(self):
        self.ensure_one()
        step = self.techpack_approval_id
        if not step:
            return
        if self.decision == 'approved':
            step.action_approve()
            if self.techpack_id and self.techpack_id.state in ('buyer_review', 'sample_development'):
                self.techpack_id.write({'state': 'approved', 'approval_date': fields.Date.context_today(self)})
        elif self.decision == 'revision_required':
            step.write({'status': 'modification_requested', 'comments': self.comments})
        else:
            step.action_reject()
            step.comments = self.comments

    def _apply_sample_decision(self):
        self.ensure_one()
        step = self.sample_approval_id
        if not step:
            return
        if self.decision == 'approved':
            step.action_approve()
            if self.sample_id:
                self.sample_id.action_mark_approved()
        elif self.decision == 'revision_required':
            step.write({'status': 'pending', 'comments': self.comments})
            if self.sample_id:
                self.sample_id.write({'status': 'revision'})
        else:
            step.action_reject()
            if self.sample_id:
                self.sample_id.write({'status': 'rejected'})

    def _apply_style_decision(self):
        self.ensure_one()
        step = self.style_approval_id
        if not step:
            return
        if self.decision == 'approved':
            step.action_approve()
        else:
            step.action_reject()
        step.comments = self.comments or step.comments
