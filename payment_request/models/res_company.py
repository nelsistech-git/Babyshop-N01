# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ------------------------------------------------------------------
    # Our own bank account debited for RTGS / BEFTN payment requests
    # (shown as "Originating Customer Details" on RTGS, and as the letter's
    # debit account on BEFTN). Kept separate from commercial's FC/CD
    # accounts since those are for LC/TT foreign-currency remittance -
    # RTGS/BEFTN here are for local BDT vendor/supplier payments.
    # ------------------------------------------------------------------
    pr_own_bank_id = fields.Many2one(
        'res.partner.bank', string='Own Bank Account (RTGS/BEFTN)',
        domain="[('partner_id', '=', partner_id)]",
        help='Your own bank account debited for Payment Request RTGS/BEFTN transfers '
             '(e.g. the Commercial Bank of Ceylon PLC current account). Must be a bank '
             'account already saved on the company\'s own Contact record.')
    pr_own_bank_branch = fields.Char(string='Own Bank Branch', default='Motijheel Branch')

    # ------------------------------------------------------------------
    # Accounting configuration for "Create Vendor Payment" - can be left
    # blank; the action will raise a clear message telling you what to
    # configure rather than guessing or posting an incomplete entry.
    # ------------------------------------------------------------------
    pr_journal_id = fields.Many2one(
        'account.journal', string='Payment Request Journal',
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', id)]")
    pr_bank_account_id = fields.Many2one(
        'account.account', string='Bank Account (Credited on Payment)',
        domain="[('company_id', '=', id)]")
    pr_tds_payable_account_id = fields.Many2one(
        'account.account', string='TDS (WHT) Payable Account',
        domain="[('company_id', '=', id)]",
        help='Liability account credited for tax withheld from vendor payments (WHT column).')
    pr_vds_payable_account_id = fields.Many2one(
        'account.account', string='VDS (WHVAT) Payable Account',
        domain="[('company_id', '=', id)]",
        help='Liability account credited for VAT withheld from vendor payments (WHVAT column).')

    # ------------------------------------------------------------------
    # Signatory shown on the RTGS Application ("Account Holder's Signature")
    # ------------------------------------------------------------------
    pr_signatory_name = fields.Char(string='RTGS/BEFTN Signatory Name')
    pr_signatory_designation = fields.Char(
        string='RTGS/BEFTN Signatory Designation', default='Chief Executive Officer')
    pr_signatory_name_2 = fields.Char(
        string='BEFTN 2nd Signatory Name',
        help='BEFTN letters carry two authorized signatories - leave blank if yours only needs one.')
    pr_signatory_designation_2 = fields.Char(string='BEFTN 2nd Signatory Designation')

    # ------------------------------------------------------------------
    # Mushak 6.6 VDS (VAT Deducted at Source) Certificate - the deducting
    # entity's (our company's) own BIN, printed in the certificate header.
    # Not the same as any vendor/supplier BIN, which is read per-line from
    # the beneficiary's Contact record (res.partner.vat).
    # ------------------------------------------------------------------
    pr_vds_company_bin = fields.Char(
        string='Company BIN (VAT Registration)',
        help='Our own Business Identification Number (BIN), as registered with NBR - printed as '
             '"উৎসে কর কর্তনকারী সত্তার বিআইএন" on the Mushak 6.6 VDS Certificate.')

    def pr_get_address_text(self):
        """One-line company address for the Mushak 6.6 header, built from the
        company's own address fields (Settings > Companies)."""
        self.ensure_one()
        parts = [self.street, self.street2, self.city,
                 self.state_id.name if self.state_id else False,
                 self.zip, self.country_id.name if self.country_id else False]
        return ', '.join(p for p in parts if p) or '-'

    def pr_format_amount(self, amount):
        """Bangladeshi/Indian digit grouping (last 3 digits, then groups of 2 -
        e.g. 1834000 -> '18,34,000.00'), as used on NBR Mushak forms."""
        return format_bdt_grouped(amount)

    def action_pr_setup_chart_of_accounts(self):
        """Match/link the Payment Request account heads by code then name from the
        already-imported Chart of Accounts, mirroring lc_management's and
        edf.scheme's auto-setup pattern. Never overwrites a field already set."""
        self.ensure_one()
        Account = self.env['account.account'].with_context(active_test=False)
        heads = [
            ('pr_bank_account_id', ['1802013817'], ['CBC Current Account', 'Bank - CBC']),
            ('pr_tds_payable_account_id', [], ['TDS Payable', 'Tax Deducted at Source Payable']),
            ('pr_vds_payable_account_id', [], ['VDS Payable', 'VAT Deducted at Source Payable']),
        ]
        linked, skipped = [], []
        for field_name, codes, names in heads:
            if self[field_name]:
                continue
            account = False
            for code in codes:
                account = Account.search([('code', '=', code), ('company_id', '=', self.id)], limit=1)
                if account:
                    break
            if not account:
                for name in names:
                    account = Account.search([('name', '=ilike', name), ('company_id', '=', self.id)], limit=1)
                    if account:
                        break
            if account:
                self[field_name] = account.id
                linked.append('%s -> %s %s' % (field_name, account.code, account.name))
            else:
                skipped.append(field_name)
        if not self.pr_journal_id:
            journal = self.env['account.journal'].search(
                [('type', 'in', ('bank', 'cash')), ('company_id', '=', self.id)], limit=1)
            if journal:
                self.pr_journal_id = journal.id
                linked.append('pr_journal_id -> %s' % journal.name)

        message = ''
        if linked:
            message += 'Linked:\n' + '\n'.join(linked) + '\n'
        if skipped:
            message += ('Not found in your Chart of Accounts (set manually): ' + ', '.join(skipped))
        if not message:
            message = 'All Payment Request account heads are already configured - nothing to do.'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Payment Request Chart of Accounts', 'message': message,
                       'sticky': bool(skipped), 'type': 'success' if not skipped else 'warning'},
        }


# ---------------------------------------------------------------------
# Bangladeshi Taka amount-in-words (Lakh/Crore numbering, as used on the
# RTGS Application - "Taka Eight Lac Only.") - NOT the Western
# Million/Billion system, so Odoo's/num2words' default English converter
# cannot be reused as-is.
# ---------------------------------------------------------------------
_ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
         'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
         'Seventeen', 'Eighteen', 'Nineteen']
_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']


def _two_digits_to_words(n):
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (' ' + _ONES[n % 10] if n % 10 else '')).strip()


def _three_digits_to_words(n):
    if n >= 100:
        rest = n % 100
        return ('%s Hundred' % _ONES[n // 100]) + (' ' + _two_digits_to_words(rest) if rest else '')
    return _two_digits_to_words(n)


def format_bdt_grouped(amount):
    """Bangladeshi/Indian style digit grouping: last 3 digits, then groups of
    2 (e.g. 1834000.5 -> '18,34,000.50'). Used on Mushak forms instead of the
    Western 3-digit grouping."""
    amount = round(amount or 0.0, 2)
    sign = '-' if amount < 0 else ''
    amount = abs(amount)
    int_part = int(amount)
    dec_part = int(round((amount - int_part) * 100))
    digits = str(int_part)
    if len(digits) > 3:
        last3, rest = digits[-3:], digits[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        digits = ','.join(groups) + ',' + last3
    return '%s%s.%02d' % (sign, digits, dec_part)


def amount_to_words_bdt(amount):
    """1 Lac = 100,000 ; 1 Crore = 1,00,00,000 (10,000,000)."""
    amount = round(amount or 0.0, 2)
    rupees = int(amount)
    paisa = int(round((amount - rupees) * 100))

    if rupees == 0:
        words = 'Zero'
    else:
        crore, remainder = divmod(rupees, 10000000)
        lac, remainder = divmod(remainder, 100000)
        thousand, remainder = divmod(remainder, 1000)
        hundred = remainder

        parts = []
        if crore:
            parts.append('%s Crore' % _three_digits_to_words(crore))
        if lac:
            parts.append('%s Lac' % _three_digits_to_words(lac))
        if thousand:
            parts.append('%s Thousand' % _three_digits_to_words(thousand))
        if hundred:
            parts.append(_three_digits_to_words(hundred))
        words = ' '.join(parts) if parts else 'Zero'

    result = 'Taka %s Only.' % words
    if paisa:
        result = 'Taka %s and Paisa %s Only.' % (words, _two_digits_to_words(paisa))
    return result
