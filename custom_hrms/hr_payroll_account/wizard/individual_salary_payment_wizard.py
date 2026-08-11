from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime
from odoo.tools.misc import format_date


class SingleSalaryPaymentWizard(models.TransientModel):
    _name = "single.salary.payment.wizard"
    _description = "Single Salary Payment Wizard"

    # @api.onchange('struct_id')
    # def _onchange_debit_acc_id(self):
    #     if self.struct_id:
    #         debit_acc_id = self.struct_id.journal_id.default_account_id
    #
    #         return {'value': {'debit_account_id': debit_acc_id}}

    payslip_id = fields.Many2one('hr.payslip', string='Payslip', domain=[('is_paid', '=', False), ('state', '=', 'done')])
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    inter_company_id = fields.Many2one('internal.company', string='Inter Company',
                                       related='user_work_location_id.inter_company_id')

    department_id = fields.Many2one('hr.department', string='Department')
    disbursement_type = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('bank_cash', 'Bank & Cash')
    ], string="Payment Type", default="cash")
    s_bank_name = fields.Many2one('hr.bank', string="Salary Bank Name", help="Salary A/C Bank Name")
    s_bank_account_no = fields.Char(string='Salary Account No', help='Salary Account No')

    struct_id = fields.Many2one('hr.payroll.structure', string="Salary Structure")
    number = fields.Char(string='Salary Slip Number', readonly=True)
    bank_journal_id = fields.Many2one('account.journal', string='Bank Journal', domain=[('type', '=', 'bank')])
    cash_journal_id = fields.Many2one('account.journal', string='Cash Journal', domain=[('type', '=', 'cash')])
    bank_credit_account_id = fields.Many2one('account.account', 'Bank Credit Account')
    cash_credit_account_id = fields.Many2one('account.account', 'Cash Credit Account')
    debit_account_id = fields.Many2one('account.account', 'Debit Account',
                                            domain="[('account_type', '!=', 'view')]")
    bank_amount = fields.Float(string="Bank Amount", help="Bank Amount")
    cash_amount = fields.Float(string="Cash Amount", help="Cash Amount")
    payment_date = fields.Date(string="Payment Date", default=fields.Datetime.now())
    emp_private_address_id = fields.Many2one('res.partner', string='Private Address')
    # comment-for-upgrade
    # bank_credit_inter_company_id = fields.Many2one('internal.company', string='Bank Inter Company',
    #                                    related='bank_credit_account_id.inter_company_id')
    # cash_credit_inter_company_id = fields.Many2one('internal.company', string='Cash Inter Company',
    #                                                related='cash_credit_account_id.inter_company_id')

    bank_credit_inter_company_id = fields.Many2one('internal.company', string='Bank Inter Company')
    cash_credit_inter_company_id = fields.Many2one('internal.company', string='Cash Inter Company')

    @api.model
    def default_get(self, fields):
        res = super(SingleSalaryPaymentWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        salary_payment_obj = self.env['hr.payslip'].browse(active_id)
        res['payslip_id'] = salary_payment_obj.id

        return res

    @api.onchange('payslip_id')
    def _onchange_payslip_id(self):
        active_id = self.env.context.get('active_id')
        if self.payslip_id:
            self.employee_id = self.payslip_id.employee_id.id
            self.emp_private_address_id = self.payslip_id.emp_private_address_id.id
            self.struct_id = self.payslip_id.struct_id.id
            self.user_work_location_id = self.payslip_id.user_work_location_id.id
            self.department_id = self.payslip_id.department_id.id
            self.disbursement_type = self.payslip_id.disbursement_type
            self.s_bank_name = self.payslip_id.s_bank_name
            self.s_bank_account_no = self.payslip_id.s_bank_account_no
            self.bank_amount = self.payslip_id.bank_amount
            self.cash_amount = self.payslip_id.cash_amount
            self.number = self.payslip_id.number
            self.debit_account_id = self.payslip_id.struct_id.journal_id.default_account_id.id
        if active_id:
            return {'domain': {
                'payslip_id': [('id', '=', self.payslip_id.id)]}}

    @api.onchange('disbursement_type')
    def _onchange_payment_type(self):
        accounts = []
        if self.disbursement_type == 'bank':
            bank_journals = self.env['account.journal'].search([('type', '=', self.disbursement_type)])
            for journal in bank_journals:
                accounts.append(journal.default_account_id.id)
            return {'domain': {
                'bank_credit_account_id': [('id', 'in', accounts)],
                'cash_credit_account_id': [('id', 'in', None)]}}
        elif self.disbursement_type == 'cash':
            cash_journals = self.env['account.journal'].search([('type', '=', self.disbursement_type)])
            for journal in cash_journals:
                accounts.append(journal.default_account_id.id)
            return {'domain': {
                'bank_credit_account_id': [('id', 'in', None)],
                'cash_credit_account_id': [('id', 'in', accounts)]}}
        else:
            bank_accounts = []
            cash_accounts = []
            bank_journals = self.env['account.journal'].search([('type', '=', 'bank')])
            cash_journals = self.env['account.journal'].search([('type', '=', 'cash')])

            for journal in bank_journals:
                bank_accounts.append(journal.default_account_id.id)
            for journal in cash_journals:
                cash_accounts.append(journal.default_account_id.id)

            return {'domain': {
                'bank_credit_account_id': [('id', 'in', bank_accounts)],
                'cash_credit_account_id': [('id', 'in', cash_accounts)]
            }}

    def action_confirm(self):
        #payslip_obj = self.env['hr.payslip'].browse(self.env.context.get('active_id'))

        payslip_obj =  self.payslip_id
        payslip_date_to = payslip_obj.date_to
        disbursement_type = self.disbursement_type
        partner_id = self.employee_id.address_home_id.id
        bank_journal_id = self.bank_journal_id
        debit_account_id = self.debit_account_id
        bank_credit_account_id = self.bank_credit_account_id
        cash_journal_id = self.cash_journal_id
        cash_credit_account_id = self.cash_credit_account_id
        cash_amount = self.cash_amount
        bank_amount = self.bank_amount
        slip_no = self.number
        location_id = self.user_work_location_id.id
        payment_date = self.payment_date

        inter_company_id = self.inter_company_id
        bank_credit_inter_company_id = self.bank_credit_inter_company_id
        cash_credit_inter_company_id = self.cash_credit_inter_company_id


        bank_move_line = []
        cash_move_line = []

        if not self.emp_private_address_id:
            raise ValidationError(_('Private Address not mapped for employee: %s') % self.employee_id.name)

        if disbursement_type in ('bank', 'bank_cash') and bank_amount > 0:
            # individual employee payment move line debit account line for bank and bank_cash
            debit_val = {
                'account_id': debit_account_id.id,
                'debit': bank_amount,
                'credit': 0.0,
                'partner_id': partner_id,
                'name': slip_no,
                #'exclude_from_invoice_tab': False,
            }
            bank_move_line.append((0, 0, debit_val))

            # individual employee payment move line credit account line for bank and bank_cash
            credit_val = {
                'account_id': bank_credit_account_id.id,
                'debit': 0.0,
                'credit': bank_amount,
                'partner_id': partner_id,
                'name': slip_no,
                #'exclude_from_invoice_tab': False,
            }
            bank_move_line.append((0, 0, credit_val))

            #----------- for bank inter-company
            if (inter_company_id and bank_credit_inter_company_id and inter_company_id != bank_credit_inter_company_id):
                if not inter_company_id.payable_acc_id:
                    raise ValidationError(_("Required Payable Account setting in Inter-company of '%s'") % inter_company_id.name)
                if not bank_credit_inter_company_id.receivable_acc_id:
                    raise ValidationError(_("Required Receivable Account setting in Inter-company of '%s'") % bank_credit_inter_company_id.name)

                debit_val2 = {
                    'account_id': bank_credit_inter_company_id.receivable_acc_id.id,
                    'debit': bank_amount,
                    'credit': 0.0,
                    'partner_id': inter_company_id.partner_id.id or None,
                    'name': slip_no,
                    #'exclude_from_invoice_tab': False,
                }
                bank_move_line.append((0, 0, debit_val2))
                credit_val2 = {
                    'account_id': inter_company_id.payable_acc_id.id,
                    'debit': 0.0,
                    'credit': bank_amount,
                    'partner_id': bank_credit_inter_company_id.partner_id.id or None,
                    'name': slip_no,
                    #'exclude_from_invoice_tab': False,
                }
                bank_move_line.append((0, 0, credit_val2))
            # ----------- end inter-company

            bank_move = self.env['account.move'].sudo().create({
                'journal_id': bank_journal_id.id,
                'ref': slip_no,
                'name': '/',
                'line_ids': bank_move_line,
                'partner_id': partner_id,
                'location_id': location_id,
                'date': payment_date
            })
            if bank_move:
                # Journal Post
                bank_move.action_post()

                payslip_obj.bank_payment_move_id = bank_move.id

        if disbursement_type in ('cash', 'bank_cash') and cash_amount > 0:
            # individual employee payment move line debit account line for cash and bank_cash
            debit_val = {
                'account_id': debit_account_id.id,
                'debit': cash_amount,
                'credit': 0.0,
                'partner_id': partner_id,
                'name': slip_no,
                #'exclude_from_invoice_tab': False,
            }
            cash_move_line.append((0, 0, debit_val))

            # individual employee payment move line credit account line for cash and bank_cash
            credit_val = {
                'account_id': cash_credit_account_id.id,
                'debit': 0.0,
                'credit': cash_amount,
                'partner_id': partner_id,
                'name': slip_no,
                #'exclude_from_invoice_tab': False,
            }
            cash_move_line.append((0, 0, credit_val))

            # ----------- for cash inter-company
            if (inter_company_id and cash_credit_inter_company_id and inter_company_id != cash_credit_inter_company_id):
                if not inter_company_id.payable_acc_id:
                    raise ValidationError(
                        _("Required Payable Account setting in Inter-company of '%s'") % inter_company_id.name)
                if not cash_credit_inter_company_id.receivable_acc_id:
                    raise ValidationError(
                        _("Required Receivable Account setting in Inter-company of '%s'") % cash_credit_inter_company_id.name)

                debit_val2 = {
                    'account_id': cash_credit_inter_company_id.receivable_acc_id.id,
                    'debit': cash_amount,
                    'credit': 0.0,
                    'partner_id': inter_company_id.partner_id.id or None,
                    'name': slip_no,
                    #'exclude_from_invoice_tab': False,
                }
                cash_move_line.append((0, 0, debit_val2))
                credit_val2 = {
                    'account_id': inter_company_id.payable_acc_id.id,
                    'debit': 0.0,
                    'credit': cash_amount,
                    'partner_id': cash_credit_inter_company_id.partner_id.id or None,
                    'name': slip_no,
                    #'exclude_from_invoice_tab': False,
                }
                cash_move_line.append((0, 0, credit_val2))
            # ----------- end inter-company

            cash_move = self.env['account.move'].sudo().create({
                'journal_id': cash_journal_id.id,
                'ref': slip_no,
                'name': '/',
                'line_ids': cash_move_line,
                'partner_id': partner_id,
                'location_id': location_id,
                'date': payment_date
            })
            if cash_move:
                # Journal Post
                cash_move.action_post()
                payslip_obj.cash_payment_move_id = cash_move.id

        payslip_obj.is_paid = True
        payslip_obj.payment_date = payment_date

        payment_date = self.payment_date.strftime("%d-%b-%Y")
        employee_id = self.employee_id
        contact_no = self.employee_id.contact_no if self.employee_id else None
        disburse_type = dict(self._fields['disbursement_type'].selection).get(disbursement_type)
        amount = 0
        if self.cash_amount:
            amount = amount + self.cash_amount
        if self.bank_amount:
            amount = amount + self.bank_amount

        # -------- Salary SMS
        #payslip_obj.salary_sms(employee_id, contact_no, disburse_type, amount, payment_date, payslip_date_to)

        # -------- Salary-PF SMS
        #payslip_obj.salary_pf_sms(employee_id, contact_no, disburse_type, amount, payment_date, payslip_date_to)
        # self.write({'sms_hr_payslip_sent': True})

