from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class SalaryPaymentWizard(models.TransientModel):
    _name = "salary.payment.wizard"
    _description = "Salary Payment Wizard"

    @api.onchange('user_work_location_id', 'department_id')
    def _onchange_payslips(self):
        domains = []
        #emp_domain = []
        struct_id = self.struct_id
        date_from = self.date_from
        date_to = self.date_to

        domains += [('struct_id', '=', struct_id.id), ('state', '=', 'done'), ('is_paid', '=', False)]
        domains += [('date_from', '>=', date_from), ('date_to', '<=', date_to)]
        domains += [('disbursement_type', '=', self.disbursement_type)]
        domains += [('contract_id.state', '=', 'open')]

        #emp_domain += [('company_id', '=', self.env.company.id), ('contract_ids.state', '=', 'open')]
        if self.user_work_location_id:
            domains += [('user_work_location_id', '=', self.user_work_location_id.id)]
        if self.department_id:
            domains += [('department_id', '=', self.department_id.id)]

        #emp_ids = self.env['hr.employee'].sudo().search(emp_domain)
        #domains += [('employee_id', 'in', emp_ids.ids)]

        payslip_ids = self.env['hr.payslip'].sudo().search(domains)

        return {'value': {'payslip_ids': [(6, 0, payslip_ids.ids)]}, 'domain': {
            'payslip_ids': domains,
        }}

    payslip_ids = fields.Many2many('hr.payslip', 'payslip_salary_payment_rel',
                                   'salary_payment_id', 'slip_id', string='Payslips', required=True)
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
    struct_id = fields.Many2one('hr.payroll.structure', string="Salary Structure")
    bank_journal_id = fields.Many2one('account.journal', string='Bank Journal')
    cash_journal_id = fields.Many2one('account.journal', string='Cash Journal')
    bank_credit_account_id = fields.Many2one('account.account', 'Bank Credit Account',
                                             domain="[('account_type', '!=', 'view')]")
    cash_credit_account_id = fields.Many2one('account.account', 'Cash Credit Account',
                                             domain="[('account_type', '!=', 'view')]")
    debit_account_id = fields.Many2one('account.account', 'Debit Account',
                                            domain="[('account_type', '!=', 'view')]")
    payment_date = fields.Date(string="Payment Date")

    date_from = fields.Date(string='Payslip From')
    date_to = fields.Date(string='Payslip To')

    # comment-for-upgrade
    # bank_credit_inter_company_id = fields.Many2one('internal.company', string='Bank Inter Company',
    #                                                related='bank_credit_account_id.inter_company_id')
    # cash_credit_inter_company_id = fields.Many2one('internal.company', string='Cash Inter Company',
    #                                                related='cash_credit_account_id.inter_company_id')

    bank_credit_inter_company_id = fields.Many2one('internal.company', string='Bank Inter Company')
    cash_credit_inter_company_id = fields.Many2one('internal.company', string='Cash Inter Company')

    @api.model
    def default_get(self, fields):
        res = super(SalaryPaymentWizard, self).default_get(fields)
        salary_payment_obj = self.env['salary.payment'].browse(self.env.context.get('active_id'))
        res['struct_id'] = salary_payment_obj.struct_id.id
        res['user_work_location_id'] = salary_payment_obj.user_work_location_id.id
        res['disbursement_type'] = salary_payment_obj.disbursement_type
        res['bank_journal_id'] = salary_payment_obj.bank_journal_id.id
        res['bank_credit_account_id'] = salary_payment_obj.bank_credit_account_id.id
        res['cash_journal_id'] = salary_payment_obj.cash_journal_id.id
        res['debit_account_id'] = salary_payment_obj.debit_account_id.id
        res['cash_credit_account_id'] = salary_payment_obj.cash_credit_account_id.id
        res['payment_date'] = salary_payment_obj.payment_date
        res['date_from'] = salary_payment_obj.date_from
        res['date_to'] = salary_payment_obj.date_to
        return res

    def action_confirm(self):
        salary_payment_obj = self.env['salary.payment'].browse(self.env.context.get('active_id'))
        payment_date = salary_payment_obj.payment_date
        payslip_ids = self.payslip_ids
        disbursement_type = self.disbursement_type
        bank_journal_id = self.bank_journal_id
        bank_credit_account_id = self.bank_credit_account_id
        cash_journal_id = self.cash_journal_id
        debit_account_id = self.debit_account_id
        cash_credit_account_id = self.cash_credit_account_id


        bank_credit_inter_company_id = self.bank_credit_inter_company_id
        cash_credit_inter_company_id = self.cash_credit_inter_company_id

        location_id = self.user_work_location_id
        bank_move_line = []
        cash_move_line = []
        ref = []
        slip_ids = []
        if len(payslip_ids) > 0:
            for rec in payslip_ids:
                cash_amount = rec.cash_amount
                bank_amount = rec.bank_amount
                slip_no = rec.number
                inter_company_id = rec.inter_company_id

                if not rec.employee_id.address_home_id:
                    raise ValidationError(_('Private Address not mapped for employee: %s') % rec.employee_id.name)

                if disbursement_type in ('bank', 'bank_cash') and bank_amount > 0:
                    # individual employee payment move line debit account line for bank and bank_cash
                    debit_val = {
                        'account_id': debit_account_id.id,
                        'debit': bank_amount,
                        'credit': 0.0,
                        'partner_id': rec.employee_id.address_home_id.id,
                        'name': rec.number,
                        #'exclude_from_invoice_tab': False,
                    }
                    bank_move_line.append((0, 0, debit_val))

                    # individual employee payment move line credit account line for bank and bank_cash
                    credit_val = {
                        'account_id': bank_credit_account_id.id,
                        'debit': 0.0,
                        'credit': bank_amount,
                        'partner_id': rec.employee_id.address_home_id.id,
                        'name': rec.number,
                        #'exclude_from_invoice_tab': False,
                    }
                    bank_move_line.append((0, 0, credit_val))
                    # ----------- for bank inter-company
                    if (inter_company_id and bank_credit_inter_company_id and inter_company_id != bank_credit_inter_company_id):
                        if not inter_company_id.payable_acc_id:
                            raise ValidationError(
                                _("Required Payable Account setting in Inter-company of '%s'") % inter_company_id.name)
                        if not bank_credit_inter_company_id.receivable_acc_id:
                            raise ValidationError(
                                _("Required Receivable Account setting in Inter-company of '%s'") % bank_credit_inter_company_id.name)

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

                if disbursement_type in ('cash', 'bank_cash') and cash_amount > 0:
                    # individual employee payment move line debit account line for cash and bank_cash
                    debit_val = {
                        'account_id': debit_account_id.id,
                        'debit': cash_amount,
                        'credit': 0.0,
                        'partner_id': rec.employee_id.address_home_id.id,
                        'name': rec.number,
                        #'exclude_from_invoice_tab': False,
                    }
                    cash_move_line.append((0, 0, debit_val))

                    # individual employee payment move line credit account line for cash and bank_cash
                    credit_val = {
                        'account_id': cash_credit_account_id.id,
                        'debit': 0.0,
                        'credit': cash_amount,
                        'partner_id': rec.employee_id.address_home_id.id,
                        'name': rec.number,
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

                ref.append(rec.number)  # all slip name in account move reference
                slip_ids.append(rec.id)
                rec.is_paid = True
                rec.payment_date = payment_date
                rec.batch_payment_id = salary_payment_obj.id

                amount = 0
                if cash_amount:
                    amount = amount + cash_amount
                if bank_amount:
                    amount = amount + bank_amount

                disburse_type = dict(self._fields['disbursement_type'].selection).get(disbursement_type)

                # -------- Salary SMS
                rec.salary_sms(rec.employee_id, rec.employee_id.contact_no, disburse_type, amount, payment_date.strftime("%d-%b-%Y"), rec.date_to)
                # -------- Salary-PF SMS
                rec.salary_pf_sms(rec.employee_id, rec.employee_id.contact_no, disburse_type, amount, payment_date.strftime("%d-%b-%Y"), rec.date_to)

            # journal creation for bank or bank_cash
            if disbursement_type in ('bank', 'bank_cash') and bank_amount > 0:
                bank_move = self.env['account.move'].sudo().create({
                    'journal_id': bank_journal_id.id,
                    'ref': ', '.join(ref),
                    'name': '/',
                    'line_ids': bank_move_line,
                    'location_id': location_id.id,
                    'date': payment_date,
                    'narration': ', '.join(ref)
                })
                if bank_move:
                    # Journal Post
                    bank_move.action_post()

                    salary_payment_obj.bank_payment_move_id = bank_move.id

            # journal creation for cash or bank_cash
            if disbursement_type in ('cash', 'bank_cash') and cash_amount > 0:
                cash_move = self.env['account.move'].sudo().create({
                    'journal_id': cash_journal_id.id,
                    'ref': ', '.join(ref),
                    'name': '/',
                    'line_ids': cash_move_line,
                    'location_id': location_id.id,
                    'date': payment_date,
                    'narration': ', '.join(ref)
                })
                if cash_move:
                    # Journal Post
                    cash_move.action_post()
                    salary_payment_obj.cash_payment_move_id = cash_move.id

            salary_payment_obj.slip_ids = [(6, 0, slip_ids)]
            salary_payment_obj.state = 'done'
