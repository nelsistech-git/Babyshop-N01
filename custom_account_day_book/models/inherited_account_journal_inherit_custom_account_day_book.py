from odoo import models, fields
from num2words import num2words


class InheritedAccountJournalInheritDaybook(models.Model):
    _inherit = "account.journal"
    _description = "Inherited Account Journal Inherit Daybook"

    report_format = fields.Selection([
        ('0', 'Default'),
        ('1', 'Print as Payment Voucher'),
        ('2', 'Print as Receipt Voucher'),
        ('3', 'Print as Contra Voucher'),
        ('4', 'Print as Journal Voucher'),
        ('5', 'Print as Salary Voucher')
    ], string='Report Format', default='0')

    is_daybook_display = fields.Boolean(string="Display in Day Book?", default=True,
                                        help="Check if this Journal is show in day book")
    is_payment_display = fields.Boolean(string="Display in Payment?", default=True,
                                        help="Check if this Journal is show in Payment")
    is_deposit_journal = fields.Boolean(string="Is Deposit Journal?", default=False,
                                        help="Check if this Journal is a Deposit Journal")
    is_stock_market_display = fields.Boolean(string="Display in Stock Market?", default=False,
                                             help="Check if this Journal is show in Stock Market Share")
    is_pf_display = fields.Boolean(string="Display in PF?", default=False,
                                   help="Check if this Journal is show in Provident Fund")
    is_wppf_display = fields.Boolean(string="Display in WPPF?", default=False,
                                     help="Check if this Journal is show in WPPF")
    is_online_payment = fields.Boolean(string="Display in Online Payment?", default=False,
                                        help="Check if this Journal is show in Online Payment")
    is_payment_journal = fields.Boolean(
        string="Is Payment Journal?",
        default=False,
        help="Check if this Journal is a Payment/Expense Journal"
    )