# -*- coding: utf-8 -*-
"""Billing wizard implementing the billing rules of SRS 41 / 43."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

MILESTONE_SELECTION = [
    ('advance', 'Advance'),
    ('installation', 'Installation'),
    ('completion', 'Completion'),
    ('final', 'Final'),
    ('full', 'Full (100%)'),
]


class GcErmInvoiceWizard(models.TransientModel):
    _name = 'gc.erm.invoice.wizard'
    _description = 'GC ERM Invoice Creation'

    work_order_id = fields.Many2one(
        'gc.erm.work.order', string='Work Order', required=True, readonly=True)
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order',
        related='work_order_id.sale_order_id', readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        related='work_order_id.partner_id', readonly=True)
    currency_id = fields.Many2one(
        'res.currency', related='work_order_id.currency_id', readonly=True)
    billing_policy = fields.Selection(
        related='work_order_id.billing_policy', readonly=True)

    amount_total = fields.Monetary(
        string='Order Total', related='work_order_id.amount_total',
        readonly=True)
    amount_invoiced = fields.Monetary(
        string='Already Invoiced', compute='_compute_amounts')
    amount_remaining = fields.Monetary(
        string='Remaining', compute='_compute_amounts')

    milestone = fields.Selection(
        MILESTONE_SELECTION, string='Milestone', required=True, default='full')
    invoice_percent = fields.Float(
        string='Percentage to Invoice', default=100.0, required=True)
    invoice_date = fields.Date(
        string='Invoice Date', default=fields.Date.context_today, required=True)
    post_invoice = fields.Boolean(string='Post the invoice immediately')
    narration = fields.Text(string='Invoice Note')

    # ------------------------------------------------------------------
    # Compute / onchange
    # ------------------------------------------------------------------
    @api.depends('work_order_id')
    def _compute_amounts(self):
        Move = self.env['account.move']
        for wizard in self:
            invoices = Move.search([
                ('gc_work_order_id', '=', wizard.work_order_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '!=', 'cancel'),
            ])
            invoiced = sum(invoices.mapped('amount_untaxed'))
            wizard.amount_invoiced = invoiced
            wizard.amount_remaining = max(
                (wizard.work_order_id.sale_order_id.amount_untaxed or 0.0)
                - invoiced, 0.0)

    @api.onchange('work_order_id')
    def _onchange_work_order_id(self):
        for wizard in self:
            work_order = wizard.work_order_id
            if not work_order:
                continue
            policy = work_order.billing_policy
            if policy == 'milestone':
                if not work_order.installation_ids.filtered(
                        lambda i: i.state == 'done'):
                    wizard.milestone = 'advance'
                    wizard.invoice_percent = work_order.advance_percent
                else:
                    wizard.milestone = 'installation'
                    wizard.invoice_percent = work_order.installation_percent
            elif policy == 'advance_final':
                wizard.milestone = 'advance' \
                    if not wizard.amount_invoiced else 'final'
                wizard.invoice_percent = work_order.advance_percent or 50.0 \
                    if not wizard.amount_invoiced else 100.0
            elif policy == 'advance':
                wizard.milestone = 'advance'
                wizard.invoice_percent = 100.0
            else:
                wizard.milestone = 'full'
                wizard.invoice_percent = 100.0

    @api.onchange('milestone')
    def _onchange_milestone(self):
        for wizard in self:
            work_order = wizard.work_order_id
            mapping = {
                'advance': work_order.advance_percent,
                'installation': work_order.installation_percent,
                'completion': work_order.completion_percent,
            }
            if work_order.billing_policy == 'milestone' and \
                    wizard.milestone in mapping and mapping[wizard.milestone]:
                wizard.invoice_percent = mapping[wizard.milestone]
            elif wizard.milestone in ('full', 'final'):
                wizard.invoice_percent = 100.0

    @api.constrains('invoice_percent')
    def _check_percent(self):
        for wizard in self:
            if not 0.0 < wizard.invoice_percent <= 100.0:
                raise ValidationError(_(
                    'The percentage to invoice must be between 0 and 100.'))

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------
    def action_create_invoice(self):
        self.ensure_one()
        work_order = self.work_order_id
        order = work_order.sale_order_id
        if not order or order.state != 'sale':
            raise UserError(_(
                'The sales order must be confirmed before invoicing.'))
        ready, reason = work_order._evaluate_billing_ready()
        if not ready and self.milestone not in ('advance',):
            raise UserError(_(
                'Billing conditions have not been satisfied: %s', reason))
        if self.milestone == 'advance' and \
                work_order.billing_policy not in (
                    'advance', 'advance_final', 'milestone'):
            raise UserError(_(
                'The billing policy of work order %s does not allow an '
                'advance invoice.', work_order.name))

        percent = self.invoice_percent
        if percent >= 100.0 and self._is_final_invoice(order):
            invoice = self._create_full_invoice(order)
        else:
            invoice = self._create_down_payment_invoice(order, percent)

        installation = work_order.installation_ids.filtered(
            lambda i: i.state == 'done')[:1]
        invoice.write({
            'gc_work_order_id': work_order.id,
            'gc_lead_id': work_order.lead_id.id,
            'gc_proposal_id': work_order.proposal_id.id,
            'gc_installation_id': installation.id if installation else False,
            'gc_milestone': self.milestone,
            'invoice_date': self.invoice_date,
            'narration': self.narration or invoice.narration,
        })
        if self.post_invoice:
            invoice.action_post()
        work_order.message_post(body=_(
            'Invoice %(inv)s created for the %(milestone)s milestone '
            '(%(pct).2f%%).', inv=invoice.name, milestone=self.milestone,
            pct=percent))
        work_order._gc_notify(
            'gc_erm_lead_to_billing.mail_template_gc_invoice_created')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def _is_final_invoice(self, order):
        self.ensure_one()
        return self.milestone in ('full', 'final', 'completion')

    def _create_full_invoice(self, order):
        """Use the standard Odoo invoicing pipeline."""
        invoiceable = order.order_line.filtered(
            lambda l: not l.display_type and
            l.qty_to_invoice != 0)
        if not invoiceable:
            raise UserError(_(
                'Sales order %s has nothing left to invoice.', order.name))
        moves = order._create_invoices(final=True)
        return moves[0] if len(moves) > 1 else moves

    def _create_down_payment_invoice(self, order, percent):
        """Create a partial (advance / milestone) invoice."""
        amount = order.amount_untaxed * percent / 100.0
        if amount <= 0:
            raise UserError(_('The computed invoice amount is zero.'))
        product = self._get_down_payment_product()
        first_line = order.order_line.filtered(lambda l: not l.display_type)[:1]
        taxes = first_line.tax_id if first_line else self.env['account.tax']
        account = product.property_account_income_id \
            or product.categ_id.property_account_income_categ_id
        if not account:
            account = first_line.product_id.property_account_income_id \
                if first_line else self.env['account.account']
        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': (order.partner_invoice_id or order.partner_id).id,
            'currency_id': order.currency_id.id,
            'company_id': order.company_id.id,
            'invoice_origin': order.name,
            'invoice_payment_term_id': order.payment_term_id.id,
            'invoice_user_id': order.user_id.id,
            'team_id': order.team_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': _('%(milestone)s invoice (%(pct).2f%%) - %(order)s',
                          milestone=dict(MILESTONE_SELECTION)[self.milestone],
                          pct=percent, order=order.name),
                'product_id': product.id,
                'quantity': 1.0,
                'price_unit': amount,
                'tax_ids': [(6, 0, taxes.ids)],
                'account_id': account.id if account else False,
            })],
        }
        return self.env['account.move'].create(move_vals)

    def _get_down_payment_product(self):
        product = self.env.ref(
            'gc_erm_lead_to_billing.product_gc_milestone_billing',
            raise_if_not_found=False)
        if product:
            return product
        product = self.env['product.product'].search(
            [('default_code', '=', 'GC-MILESTONE')], limit=1)
        if product:
            return product
        return self.env['product.product'].create({
            'name': _('ERM Milestone Billing'),
            'default_code': 'GC-MILESTONE',
            'type': 'service',
            'invoice_policy': 'order',
            'sale_ok': False,
            'purchase_ok': False,
            'company_id': False,
        })
