from odoo import models, fields, api, _
from num2words import num2words

from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning


class InheritedAccountMoveInheritCustomAccountDayBook(models.Model):
    _inherit = "account.move"
    _description = "Account Move Inherit"

    account_name = fields.Char(compute='_get_account_name')
    # partner_id = fields.Many2one('res.partner', string='Vendor', tracking=True)

    partner_mobile = fields.Char(related="partner_id.mobile")
    partner_email = fields.Char(related="partner_id.email")
    # is_employee = fields.Boolean(related="partner_id.is_employee")
    # partner_type = fields.Selection(related="partner_id.mobile_customer_type", string="Partner Type")
    partner_balance_amount = fields.Float(string="Balance", related="partner_id.due_amount")
    is_particular_show = fields.Boolean(default=False)
    location_id = fields.Many2one('stock.location', string='Location')
    # comment-for-upgrade
    # location_id = fields.Many2one('stock.location', string='Location',
    #                               domain="[('state', '=', 'done')]")
    fs_dept = fields.Selection([
        ('accounts', 'Accounts'),
        ('pf', 'PF')
    ], string='FS Department', default='accounts')
    account_tag_ids = fields.Many2many('account.account.tag', string='Account Groups')

    bdt_currency_id = fields.Many2one('res.currency', 'Currency Name',
                                      default=lambda self: self.env['res.currency'].search([('name', '=', 'BDT')]))

    dr_accounts_str = fields.Char(compute='_get_dr_cr_accounts_str')
    cr_accounts_str = fields.Char(compute='_get_dr_cr_accounts_str')

    def _get_dr_cr_accounts_str(self):
        for rec in self:
            dr_accounts_str = ''
            cr_accounts_str = ''
            if len(rec.line_ids) >= 1:
                self.env.cr.execute(
                    """select id, string_agg(dr_acc::character varying, ', ') as dr_accounts_str, string_agg(cr_acc::character varying, ', ') as cr_accounts_str
                        FROM (
                            select am.id, 
                                (CASE WHEN (aml.debit > 0) THEN acc.name ELSE NULL END) AS dr_acc,
                                (CASE WHEN (aml.credit > 0) THEN acc.name ELSE NULL END) AS cr_acc
                            FROM account_move_line aml
                            JOIN account_move am on am.id=aml.move_id
                            JOIN account_account acc ON (aml.account_id=acc.id)
                            where am.id = %s
                        ) abc
                        Group By id""", [rec.id])
                values = self.env.cr.dictfetchall()
                for val in values:
                    dr_accounts_str = val['dr_accounts_str']
                    cr_accounts_str = val['cr_accounts_str']

            rec.dr_accounts_str = dr_accounts_str
            rec.cr_accounts_str = cr_accounts_str


    # journal_id = fields.Many2one('account.journal', string='Journal jh', required=True, readonly=True,
    #                              states={'draft': [('readonly', False)]},
    #                              domain="[('company_id', '=', company_id)]",
    #                              default=_get_default_journal)
    # currency_id = fields.Many2one('res.currency', store=True, readonly=True, tracking=True, required=True,
    #                               states={'draft': [('readonly', False)]},
    #                               string='Currency',
    #                               default=_get_default_currency)

    # @api.onchange('partner_id')
    # def onchange_partner_id(self):
    #     self.is_particular_show = self.partner_id.is_po_cost

    def _compute_amount_in_word(self):
        for rec in self:
            rec.amount_in_words = "".join(num2words(rec.amount_total, lang='en_IN').title().replace("-", " ")).replace(
                ",", "") + " Taka Only"

    amount_in_words = fields.Char(string="Amount In Words:", compute='_compute_amount_in_word')

    def _get_account_name(self):
        for line in self:
            if line.line_ids.account_id:
                line.update({
                    'account_name': str(line.line_ids.account_id[0].code) + " " + str(line.line_ids.account_id[0].name)
                })
            else:
                line.update({
                    'account_name': ''
                })

    def print_voucher(self):
        if self.journal_id.report_format == '0':
            return self.env.ref(
                'custom_account_day_book.journal_entry_report_id').with_context().report_action(self)
        elif self.journal_id.report_format == '1':
            return self.env.ref(
                'custom_account_day_book.voucher_report_id').with_context().report_action(self)
        elif self.journal_id.report_format == '2':
            return self.env.ref(
                'custom_account_day_book.voucher_report_id').with_context().report_action(self)
        else:
            return self.env.ref(
                'custom_account_day_book.journal_entry_report_id').with_context().report_action(self)

    @api.depends('posted_before', 'state', 'journal_id', 'date', 'move_type', 'payment_id')
    def _compute_name(self):
        self = self.sorted(lambda m: (m.date, m.ref or '', m.id))
        for move in self:
            move_has_name = move.name and move.name != '/'
            if move.state == 'draft':
                if move_has_name == False:
                    move.name = ''
            else:
                if move_has_name or move.state != 'posted' or move_has_name != False:
                    if not move.posted_before and not move._sequence_matches_date():
                        if move._get_last_sequence():
                            move.name = False
                            continue
                    else:
                        if move_has_name and move.posted_before or not move_has_name and move._get_last_sequence():
                            continue
                if move.date and (not move_has_name or not move._sequence_matches_date()):
                    move._set_next_sequence()

            if 'False' in move.name and move.move_type == 'entry' and move.journal_id.code:
                journal_code = move.journal_id.code
                journal_name = move.name.replace("False", journal_code)
                move.name = journal_name
            else:
                move.filtered(lambda m: not m.name and not move.quick_edit_mode).name = '/'
                move._inverse_name()


class InheritedAccountMoveLineInheritCustomAccountDayBook(models.Model):
    _inherit = "account.move.line"
    _description = "Account Move Line Inherit"

    account_tag_ids = fields.Many2many('account.account.tag', related="account_id.tag_ids", string='Account Groups',
                                       help="Optional tags you may want to assign for custom reporting")
    total_debit = fields.Float(related="account_id.total_debit")
    total_credit = fields.Float(related="account_id.total_credit")
    total_balance = fields.Float(related="account_id.total_balance")
    fs_dept = fields.Selection(related='move_id.fs_dept')
    location_id = fields.Many2one('stock.location', string='Location')

    @api.onchange('move_id')
    def _onchange_partner_id(self):
        for rec in self:
            rec.partner_id = rec.move_id.partner_id.id

    @api.onchange('location_id')
    def _onchange_location_id(self):
        for rec in self:
            if rec.move_id.location_id:
                rec.location_id = rec.move_id.location_id.id

    @api.onchange('account_id')
    def _onchange_account_tag_ids(self):
        for rec in self:
            if rec.move_id.account_tag_ids:
                account_ids = self.env['account.account'].search(
                    [('tag_ids', '=', rec.move_id.account_tag_ids.ids)]).mapped('id')
                return {'domain': {'account_id': [('id', 'in', account_ids)]}}


class AccountAccountInherit(models.Model):
    _inherit = "account.account"
    _description = "Account Account Inherit"

    tag_ids = fields.Many2many('account.account.tag', 'account_account_account_tag', string='Account Groups',
                               help="Optional tags you may want to assign for custom reporting")
    total_debit = fields.Float(compute='_get_total_account_values')
    total_credit = fields.Float(compute='_get_total_account_values')
    total_balance = fields.Float(compute='_get_total_account_values')

    is_emp_ledger = fields.Boolean(string='Employee Ledger', tracking=True)
    is_cus_rec_ledger = fields.Boolean(string='Customer Receivable Ledger', tracking=True)
    is_cus_adv_ledger = fields.Boolean(string='Customer Advance Ledger', tracking=True)
    is_vendor_pay_ledger = fields.Boolean(string='Vendor Payable Ledger', tracking=True)
    is_vendor_adv_ledger = fields.Boolean(string='Vendor Advance Ledger', tracking=True)
    is_default_cus_adv = fields.Boolean(string='Default Customer Advance Account', tracking=True)
    is_default_vendor_adv = fields.Boolean(string='Default Vendor Advance Account', tracking=True)
    is_wip_acc = fields.Boolean(string='Is WIP Account?', default=False, tracking=True)
    is_production_acc = fields.Boolean(string='Is Production Account?', default=False, tracking=True)
    is_foreign_gain_loss_acc = fields.Boolean(default=False, string='Foreign Gain/Loss?')
    is_online_payment = fields.Boolean(string="Is Online Payment Account?", default=False,
                                       help="Check if this account is show in Online Payment Transaction")

    production_extra_cost_category = fields.Selection([
        ('electricity', 'Electricity'),
        ('labour_wages', 'Labour Wages'),
        ('wages', 'Wages'),
        ('accessories', 'Accessories'),
        ('packaging', 'Packaging'),
        ('fec_overhead', 'Factory Overhead')
    ], string="Production Extra Cost Category", default='', copy=False, tracking=True)

    project_extra_cost_category = fields.Selection([
        ('overhead', 'Overhead'),
        ('labour', 'Labour'),
        ('vat', 'VAT'),
        ('tax', 'TAX'),
        ('other', 'Other Cost')
    ], string="Project Extra Cost Category", default='', copy=False, tracking=True)

    acc_remarks = fields.Char(string="Remarks")
    fs_dept = fields.Selection([
        ('accounts', 'Accounts'),
        ('pf', 'PF')
    ], string='FS Department', default='accounts')

    def _get_total_account_values(self):
        if len(self) > 1:
            # this is for multiple journal item information

            for data in self:
                self.env.cr.execute(
                    """SELECT id, debit AS total_debit, credit AS total_credit, balance As total_balance FROM account_move_line
                    WHERE account_id = %s AND parent_state='posted' """,
                    [data.id])
                values = self.env.cr.dictfetchall()

                totalDebit = 0
                totalCredit = 0
                totalBalance = 0

                for val in values:
                    totalDebit += val['total_debit']
                    totalCredit += val['total_credit']
                    totalBalance += val['total_balance']

                data.update({
                    'total_debit': totalDebit,
                    'total_credit': totalCredit,
                    'total_balance': totalBalance
                })

        else:
            # this is for individual journal item information
            id = self._origin.id

            self.env.cr.execute(
                """SELECT sum(debit) AS total_debit, sum(credit) AS total_credit, sum(balance) As total_balance FROM account_move_line 
                WHERE account_id = %s AND parent_state='posted' GROUP BY account_id""",
                [id])
            vals = self.env.cr.dictfetchall()

            totalDebit = 0
            totalCredit = 0
            totalBalance = 0

            for val in vals:
                totalDebit += val['total_debit']
                totalCredit += val['total_credit']
                totalBalance += val['total_balance']

            if self:
                self.update({
                    'total_debit': totalDebit,
                    'total_credit': totalCredit,
                    'total_balance': totalBalance
                })
            else:
                self.update({
                    'total_debit': '',
                    'total_credit': '',
                    'total_balance': ''
                })

    # @api.model
    # def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
    #     args = args or []
    #     domain = []
    #     if name:
    #         domain = ['|', '|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name),
    #                   ('acc_remarks', operator, name)]
    #         if operator in expression.NEGATIVE_TERM_OPERATORS:
    #             domain = ['&', '!'] + domain[1:]
    #     account_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
    #     return models.lazy_name_get(self.browse(account_ids).with_user(name_get_uid))


class AccountAccountTagInheritCustomAccountDayBook(models.Model):
    _inherit = 'account.account.tag'
    name = fields.Char('Group Name', required=True)
    type = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('service_income', 'Service Income'),
        ('contract_income', 'Contract Income'),
    ], string='Type')
