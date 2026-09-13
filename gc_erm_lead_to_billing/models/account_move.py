# -*- coding: utf-8 -*-
"""Billing integration and payment tracking (SRS 42 / 44)."""

from odoo import _, api, fields, models

GC_MILESTONE_SELECTION = [
    ('advance', 'Advance'),
    ('installation', 'Installation'),
    ('completion', 'Completion'),
    ('final', 'Final'),
    ('full', 'Full'),
]


class AccountMove(models.Model):
    _inherit = 'account.move'

    gc_work_order_id = fields.Many2one(
        'gc.erm.work.order', string='ERM Work Order', copy=False, index=True,
        ondelete='set null')
    gc_lead_id = fields.Many2one(
        'gc.erm.lead', string='ERM Lead', copy=False, index=True,
        ondelete='set null')
    gc_proposal_id = fields.Many2one(
        'gc.erm.proposal', string='ERM Proposal', copy=False,
        ondelete='set null')
    gc_installation_id = fields.Many2one(
        'gc.erm.installation', string='ERM Installation', copy=False,
        ondelete='set null')
    gc_milestone = fields.Selection(
        GC_MILESTONE_SELECTION, string='Billing Milestone', copy=False,
        index=True)
    gc_is_erm_invoice = fields.Boolean(
        string='From ERM', compute='_compute_gc_is_erm_invoice', store=True)
    gc_is_overdue = fields.Boolean(
        string='Overdue', compute='_compute_gc_is_overdue', store=True)

    @api.depends('gc_work_order_id', 'gc_lead_id')
    def _compute_gc_is_erm_invoice(self):
        for move in self:
            move.gc_is_erm_invoice = bool(
                move.gc_work_order_id or move.gc_lead_id)

    @api.depends('invoice_date_due', 'payment_state', 'state', 'move_type')
    def _compute_gc_is_overdue(self):
        today = fields.Date.context_today(self)
        for move in self:
            move.gc_is_overdue = bool(
                move.move_type in ('out_invoice', 'out_refund')
                and move.state == 'posted'
                and move.payment_state in ('not_paid', 'partial')
                and move.invoice_date_due and move.invoice_date_due < today)

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        for move in posted.filtered(
                lambda m: m.gc_work_order_id and
                m.move_type in ('out_invoice', 'out_refund')):
            move.gc_work_order_id.message_post(body=_(
                'Invoice %(inv)s posted for %(amount)s.',
                inv=move.name, amount=move.amount_total))
            move.gc_work_order_id._compute_invoice_amounts()
        return posted

    def action_gc_view_work_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gc.erm.work.order',
            'res_id': self.gc_work_order_id.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Cron (SRS 80 -- invoice reminder)
    # ------------------------------------------------------------------
    @api.model
    def _cron_gc_invoice_reminder(self):
        today = fields.Date.context_today(self)
        overdue = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('invoice_date_due', '<', today),
            ('gc_is_erm_invoice', '=', True),
        ])
        template = self.env.ref(
            'gc_erm_lead_to_billing.mail_template_gc_payment_reminder',
            raise_if_not_found=False)
        for move in overdue:
            move._compute_gc_is_overdue()
            if template:
                try:
                    template.send_mail(move.id, force_send=False)
                except Exception:  # pragma: no cover - never break the cron
                    pass
            if move.gc_work_order_id:
                move.gc_work_order_id.message_post(body=_(
                    'Invoice %(inv)s is overdue since %(date)s.',
                    inv=move.name, date=move.invoice_date_due))
        return True
