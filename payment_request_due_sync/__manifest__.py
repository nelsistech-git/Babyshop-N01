{
    'name': 'Payment Requests - Due for Payment',
    'version': '17.0.1.2.0',
    'summary': 'Vendor bills and expenses that fall due appear in a "Due for Payment" window; '
               'select them to create a draft Payment Request.',
    'description': """
Due for Payment (first window of Payment Requests)
==================================================
* Vendor Bills of any amount are listed AUTOMATICALLY the moment the Head of Finance clicks "Post"
  on the validated bill (stage Due for Payment) - regardless of the due date.
* Vendor bills are paid ONLY from the Payment Request ("Mark Paid" posts the accounting payment and
  the bill shows Paid in Accounting). "Register Payment" on vendor bills is hidden and blocked, so
  one bill can never be paid twice.
* Expense reports above BDT 5,000, once approved and unpaid, are synced automatically.
  Up to BDT 5,000 they are paid directly with "Register Payment" in the Expenses module; above
  BDT 5,000 "Register Payment" is blocked and the report must go through a Payment Request.
* Once the request is paid (or the bill payment is posted) the row becomes "Paid" and is no
  longer listed in Due for Payment (visible only under the "Paid (history)" filter).
* The list is refreshed every time the window is opened and by an hourly scheduled action.
* Select any rows and press "Create Payment Request": they are parked in a new Payment Request
  in Draft status (one line per bill / expense), and the rows show as "In Payment Request".
  If that request is cancelled or rejected, the rows return to "Pending".

System parameters (Settings > Technical > System Parameters), all optional:
  payment_request_due_sync.expense_min_amount  minimum expense total in company currency (default 5000)

Developer : Nelsis Tech
Company   : Bit Body Bangladesh Limited
""",
    'author': 'Nelsis Tech',
    'category': 'Accounting/Accounting',
    'depends': ['payment_request', 'hr_expense', 'account', 'custom_account_day_book'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_due_item_views.xml',
        'views/hr_expense_sheet_views.xml',
        'views/account_move_views.xml',
        'views/menu_views.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
