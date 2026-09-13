# -*- coding: utf-8 -*-
"""Customer acceptance wizard (SRS 26)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.gc_proposal import ACCEPTANCE_METHOD_SELECTION


class GcErmAcceptanceWizard(models.TransientModel):
    _name = 'gc.erm.acceptance.wizard'
    _description = 'GC ERM Customer Acceptance'

    proposal_id = fields.Many2one(
        'gc.erm.proposal', string='Proposal', required=True, readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', related='proposal_id.partner_id',
        readonly=True)
    amount_total = fields.Monetary(
        string='Proposal Total', related='proposal_id.amount_total',
        readonly=True)
    currency_id = fields.Many2one(
        'res.currency', related='proposal_id.currency_id', readonly=True)

    method = fields.Selection(
        ACCEPTANCE_METHOD_SELECTION, string='Acceptance Method',
        required=True, default='internal')
    acceptance_date = fields.Date(
        string='Acceptance Date', required=True,
        default=fields.Date.context_today)
    accepted_by = fields.Char(string='Accepted By', required=True)
    remarks = fields.Text(string='Remarks')
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Acceptance Document')
    confirm_sale_order = fields.Boolean(
        string='Confirm the Sales Order', default=True,
        help='Confirms the Odoo quotation so that the work order can be '
             'generated.')
    create_work_order = fields.Boolean(
        string='Create the Work Order', default=True)

    @api.onchange('proposal_id')
    def _onchange_proposal_id(self):
        for wizard in self:
            if wizard.proposal_id and not wizard.accepted_by:
                wizard.accepted_by = \
                    wizard.proposal_id.contact_id.name or \
                    wizard.proposal_id.partner_id.name

    def action_confirm(self):
        self.ensure_one()
        proposal = self.proposal_id
        if proposal.state not in ('approved', 'sent'):
            raise UserError(_(
                'Proposal %s is not in a state that accepts a customer '
                'acceptance.', proposal.name))
        if self.method == 'signed' and not self.attachment_ids:
            raise UserError(_(
                'Attach the signed acceptance document before confirming.'))
        # The quotation must be generated while the proposal is still
        # approved/sent: once it is marked accepted the generation is locked.
        order = proposal.sale_order_id
        if not order and (self.confirm_sale_order or self.create_work_order):
            proposal.action_create_quotation()
            order = proposal.sale_order_id
        proposal.with_context(gc_bypass_lock=True).write({
            'acceptance_method': self.method,
            'acceptance_date': self.acceptance_date,
            'accepted_by': self.accepted_by,
            'acceptance_remarks': self.remarks,
            'acceptance_attachment_ids': [(6, 0, self.attachment_ids.ids)],
        })
        if proposal.state != 'accepted':
            proposal.with_context(gc_bypass_lock=True)._gc_transition(
                'accepted',
                comment=_('Customer acceptance recorded (%(method)s) by '
                          '%(who)s.',
                          method=dict(ACCEPTANCE_METHOD_SELECTION)[self.method],
                          who=self.accepted_by))
        if order and self.confirm_sale_order and order.state in ('draft', 'sent'):
            order.action_confirm()
        if self.create_work_order:
            if not order or order.state != 'sale':
                raise UserError(_(
                    'The sales order must be confirmed before the work order '
                    'can be created.'))
            return order.action_gc_create_work_order()
        return {'type': 'ir.actions.act_window_close'}
