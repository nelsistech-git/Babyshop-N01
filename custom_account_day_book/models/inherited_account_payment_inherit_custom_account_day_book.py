from odoo import models, fields
from num2words import num2words


class InheritedAccountPaymentInheritCustomSale(models.Model):
    _inherit = "account.payment"
    _description = "Account Payment"

    def amount_in_word(self, amount):
        amount_in_words = "".join(num2words(amount, lang='en_IN').title().replace("-", " ")).replace(",","") + " Taka Only."
        return amount_in_words

    def compute_partner_ledger(self, partner_id):
        total_adv_payment = 0.00
        total_recv_payment = 0.00
        account_filter = "NULL"
        account_filter2 = "NULL"
        partner_filter = ""
        if partner_id:
            partner_filter = "AND partner_id = %s" % partner_id.id
            if partner_id.customer_advance_account_id and self.payment_type == 'inbound':
                account_filter = "SUM(CASE WHEN account_id = %s THEN COALESCE(balance, 0) ELSE 0 END)" % partner_id.customer_advance_account_id.id
                account_filter2 = "SUM(CASE WHEN account_id = %s THEN COALESCE(balance, 0) ELSE 0 END)" % partner_id.property_account_receivable_id.id
            if partner_id.vendor_advance_account_id and self.payment_type == 'outbound':
                account_filter = "SUM(CASE WHEN account_id = %s THEN COALESCE(balance, 0) ELSE 0 END)" % partner_id.vendor_advance_account_id.id
                account_filter2 = "SUM(CASE WHEN account_id = %s THEN COALESCE(balance, 0) ELSE 0 END)" % partner_id.property_account_payable_id.id
            partner_ledger_sql = """
                            SELECT 
                            COALESCE({0}, 0) AS total_adv_amt,
                            COALESCE({1}, 0) AS total_recv_amt
                            FROM account_move_line
                            WHERE parent_state='posted' {2}
                            GROUP BY partner_id
                            """.format(account_filter, account_filter2, partner_filter)
            self.env.cr.execute(partner_ledger_sql)
            partner_ledger_dict = self.env.cr.dictfetchone()

            if partner_ledger_dict is not None:
                total_adv_payment = partner_ledger_dict['total_adv_amt']
                total_recv_payment = partner_ledger_dict['total_recv_amt']
            return [total_adv_payment, total_recv_payment]
        else:
            return [total_adv_payment, total_recv_payment]

    def action_post(self):
        res = super(InheritedAccountPaymentInheritCustomSale, self).action_post()
        self.state = 'posted'
        return res
    # amount_in_words = fields.Char(string="Amount In Words:", compute='_compute_amount_in_word')
