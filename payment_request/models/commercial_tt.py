# -*- coding: utf-8 -*-
"""
TT -> Accounting hand-off
=========================
Per BBBL's process: "tt part its forward to accounting module for its
process." TT (Telegraphic Transfer) is a foreign-currency outward
remittance, not a domestic BEFTN/RTGS transfer, so a TT does not generate
an RTGS/BEFTN bank letter here - instead it is forwarded into a Payment
Request line (Payment Mode = "Bank Transfer") so it goes through the SAME
approval chain and the same "Create Vendor Payment" accounting posting as
every other vendor payment, exactly as the LC side already forwards into
EDF Loan Management.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CommercialTT(models.Model):
    _inherit = 'commercial.tt'

    payment_request_id = fields.Many2one(
        'payment.request', string='Payment Request', copy=False, readonly=True,
        help='Payment Request auto-created when this TT was forwarded to Accounting.')

    def _find_matching_vendor_bill(self, tt):
        """Best-effort auto-match of the single posted Vendor Bill this TT is
        settling, so "Create Vendor Payment" can run without a manual step.
        Only attaches when there is exactly ONE unambiguous candidate - a
        TT's own PO/vendor with a posted, unpaid Vendor Bill not already
        claimed by another Payment Request line. If there's no bill yet
        (common - a TT is often raised before the vendor bill is booked) or
        more than one open bill on that PO, this deliberately returns
        nothing rather than guessing which one, matching the "leave blank
        rather than guess" rule used everywhere else in this engagement.
        """
        if not tt.purchase_id or not tt.partner_id:
            return self.env['account.move']
        already_claimed = self.env['payment.request.line'].search(
            [('invoice_id', '!=', False)]).mapped('invoice_id')
        candidates = self.env['account.move'].search([
            ('move_type', 'in', ('in_invoice',)),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ('paid', 'reversed')),
            ('partner_id', '=', tt.partner_id.id),
            ('invoice_line_ids.purchase_order_id', '=', tt.purchase_id.id),
        ]) - already_claimed
        return candidates if len(candidates) == 1 else self.env['account.move']

    def action_forward_to_accounting(self):
        PaymentRequest = self.env['payment.request']
        for tt in self:
            if tt.payment_request_id:
                raise UserError(_('This TT is already forwarded to Payment Request %s.')
                                % tt.payment_request_id.name)
            if not tt.amount:
                raise UserError(_('Enter the TT Amount before forwarding to Accounting.'))
            company = tt.company_id
            bdt_amount = tt.currency_id._convert(
                tt.amount, company.currency_id, company, tt.date or fields.Date.context_today(self))
            bill = tt._find_matching_vendor_bill(tt)
            line_vals = {
                'partner_id': tt.partner_id.id,
                'bill_amount': bdt_amount,
                'payment_mode': 'bank',
                'value_date': tt.date,
                'purpose': _('TT %s - PI %s (%s %.2f)') % (
                    tt.reference_no or tt.name, tt.pi_no or '', tt.currency_id.name, tt.amount),
                'invoice_ref': tt.pi_no,
                'invoice_date': tt.pi_date,
                'bank_id': tt.partner_bank_id.id if tt.partner_bank_id else False,
                'beneficiary_bank_name': tt.beneficiary_bank_name,
                'beneficiary_account_number': tt.beneficiary_account_number,
                'beneficiary_address': tt.beneficiary_address,
            }
            if bill:
                # Mirror what the line's own onchange does when a user picks
                # a Vendor Bill by hand: the bill's own residual is the
                # authoritative amount, not the TT's spot-converted estimate.
                line_vals['invoice_id'] = bill.id
                line_vals['bill_amount'] = bill.amount_residual
                line_vals['invoice_ref'] = bill.ref or bill.name
                line_vals['invoice_date'] = bill.invoice_date
            request = PaymentRequest.create({
                'company_id': company.id,
                'commercial_tt_id': tt.id,
                'line_ids': [(0, 0, line_vals)],
            })
            tt.payment_request_id = request.id
            if bill:
                tt.message_post(body=_(
                    'TT forwarded to Accounting: Payment Request %s created and auto-linked to Vendor '
                    'Bill %s (Bill Amount taken from the bill\'s own outstanding balance, %s %.2f).')
                    % (request.name, bill.name, company.currency_id.name, bill.amount_residual))
            else:
                tt.message_post(body=_(
                    'TT forwarded to Accounting: Payment Request %s created (Bill Amount converted to '
                    '%s %.2f at today\'s rate - please verify against the bank\'s actual TT rate before '
                    'approval). No single matching posted Vendor Bill was found to auto-link - open the '
                    'Payment Request line and set "Vendor Bill" manually before it can be submitted for '
                    'approval, since "Create Vendor Payment" requires it.')
                    % (request.name, company.currency_id.name, bdt_amount))

    def action_view_payment_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment Request',
            'res_model': 'payment.request',
            'view_mode': 'form',
            'res_id': self.payment_request_id.id,
        }
