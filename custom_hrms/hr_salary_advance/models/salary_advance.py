import time
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class SalaryAdvancePayment(models.Model):
    _name = "salary.advance"
    _description = "Salary Advance"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', readonly=True, default=lambda self: 'Adv/')

    def _get_employees(self):
        if self.env.user.user_work_location_id:
            return [('user_work_location_id', '=', self.env.user.user_work_location_id.id)]
        else:
            return []

    employee_id = fields.Many2one('hr.employee', string='Employee', domain=_get_employees, required=True,
                                  help="Employee")
    date = fields.Date(string='Request Date', required=True, default=lambda self: fields.Date.today(),
                       help="Request date")
    payslip_date = fields.Date(string='Payslip Date', required=True, default=lambda self: fields.Date.today(),
                               help="Payslip Date")

    reason = fields.Text(string='Reason', help="Reason")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    advance = fields.Float(string='Advance Amount', required=True)
    payment_method = fields.Many2one('account.journal', string='Payment Method')
    exceed_condition = fields.Boolean(string='Exceed than Maximum',
                                      help="The Advance is greater than the maximum percentage in salary structure")
    department = fields.Many2one('hr.department', string='Department')
    emp_id_card_no = fields.Char(string='Employee ID')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submitted'),
                              ('waiting_approval', 'HR Approval'),
                              ('approve', ' Accounts Approval'),
                              ('cancel', 'Cancelled'),
                              ('reject', 'Rejected')], string='Status', default='draft', tracking=True)
    debit = fields.Many2one('account.account', string='Debit Account')
    credit = fields.Many2one('account.account', string='Credit Account')
    journal = fields.Many2one('account.journal', string='Journal')
    employee_contract_id = fields.Many2one('hr.contract', string='Contract')
    salary_advance_settings = fields.Many2one('salary.advance.settings', string='Maximum Allowed')
    is_deducted = fields.Boolean(string='Deducted')
    gross_salary = fields.Float(string="Gross Salary", digits=(16, 2), related='employee_contract_id.gross_salary')
    max_adv_amt = fields.Float(string="Maximum Amount", compute='_compute_max_adv_amt')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip')
    move_id = fields.Many2one('account.move', string='Journal Entry', copy=False)

    @api.onchange('advance', 'max_adv_amt')
    def _check_unique_constraint_advance(self):
        for rec in self:
            if rec.advance > rec.max_adv_amt:
                raise UserError(_('Warning! Advance amount cannot be greater than the maximum advance amount.'))

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        department_id = self.employee_id.department_id.id
        user_work_location_id = self.employee_id.user_work_location_id.id
        emp_id_card_no = self.employee_id.id_card_no
        employee_contract_id = self.employee_id.contract_id.id
        # domain = [('employee_id', '=', self.employee_id.id)]
        return {'value': {'department': department_id, 'user_work_location_id': user_work_location_id,
                          'emp_id_card_no': emp_id_card_no, 'employee_contract_id': employee_contract_id}
                }

    @api.onchange('company_id')
    def onchange_company_id(self):
        company = self.company_id
        domain = [('company_id.id', '=', company.id)]
        result = {
            'domain': {
                'journal': domain,
            },

        }
        return result

    @api.onchange('salary_advance_settings', 'gross_salary')
    def _compute_max_adv_amt(self):
        self.max_adv_amt = (self.gross_salary * (self.salary_advance_settings.value / 100))

    def submit_to_manager(self):
        if self.advance <= 0:
            raise UserError(
                _("Advance amount must be greater than zero.")
            )
        self.state = 'submit'

    def cancel(self):
        self.state = 'cancel'

    def reject(self):
        self.state = 'reject'

    def unlink(self):
        for r in self:
            if r.state != 'draft':
                raise UserError(_("Only 'Draft' record can be deleted!"))
        return super(SalaryAdvancePayment, self).unlink()

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            val['name'] = self.env['ir.sequence'].next_by_code('salary.advance.seq') or ' '
        res_id = super(SalaryAdvancePayment, self).create(vals)
        return res_id

    def approve_request(self):
        """This Approve the employee salary advance request.
                   """
        emp_obj = self.env['hr.employee']
        address = emp_obj.browse([self.employee_id.id]).address_home_id
        if not address.id:
            raise ValidationError(
                'Define home address for the employee. i.e address under private information of the employee.')

        salary_advance_search = self.search([('employee_id', '=', self.employee_id.id), ('id', '!=', self.id),
                                             ('state', '=', 'approve')])
        current_month = datetime.strptime(str(self.payslip_date), '%Y-%m-%d').strftime('%Y-%m')
        for each_advance in salary_advance_search:
            existing_month = datetime.strptime(str(each_advance.payslip_date), '%Y-%m-%d').strftime('%Y-%m')
            if current_month == existing_month:
                raise ValidationError('Advance can be requested once in a month')

        struct_id = self.employee_contract_id.struct_id
        adv = self.advance

        if not self.advance:
            raise UserError('You must Enter the Salary Advance amount')
        payslip_obj = self.env['hr.payslip'].search([('employee_id', '=', self.employee_id.id),
                                                     ('state', '=', 'done'), ('date_from', '<=', self.payslip_date),
                                                     ('date_to', '>=', self.payslip_date)], limit=1)
        if payslip_obj:
            raise UserError("This month salary already calculated")

        self.state = 'waiting_approval'

    def approve_request_acc_dept(self):
        """This Approve the employee salary advance request from accounting department.
                   """
        salary_advance_search = self.search([('employee_id', '=', self.employee_id.id), ('id', '!=', self.id),
                                             ('state', '=', 'approve')])
        current_month = datetime.strptime(str(self.payslip_date), '%Y-%m-%d').strftime('%Y-%m')
        for each_advance in salary_advance_search:
            existing_month = datetime.strptime(str(each_advance.payslip_date), '%Y-%m-%d').strftime('%Y-%m')
            if current_month == existing_month:
                raise UserError('Advance can be requested once in a month')
        if not self.debit or not self.credit or not self.journal:
            raise UserError("You must enter Debit & Credit account and journal to approve ")
        if not self.advance:
            raise UserError('You must Enter the Salary Advance amount')

        move_obj = self.env['account.move']
        timenow = time.strftime('%Y-%m-%d')
        line_ids = []
        debit_sum = 0.0
        credit_sum = 0.0
        for request in self:
            amount = request.advance
            request_name = request.employee_id.name
            reference = request.name
            journal_id = request.journal.id
            partner_id = request.employee_id.address_home_id.id if request.employee_id.address_home_id else None
            location_id = request.user_work_location_id.id

            move = {
                'narration': 'Salary Advance Of ' + request_name,
                'ref': reference,
                'journal_id': journal_id,
                'date': timenow,
                'partner_id': partner_id,
                'location_id': location_id,
            }

            debit_account_id = request.debit.id
            credit_account_id = request.credit.id

            if debit_account_id:
                debit_line = (0, 0, {
                    'name': request_name,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount > 0.0 and amount or 0.0,
                    'credit': amount < 0.0 and -amount or 0.0,
                    'partner_id': partner_id
                })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

            if credit_account_id:
                credit_line = (0, 0, {
                    'name': request_name,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'date': timenow,
                    'debit': amount < 0.0 and -amount or 0.0,
                    'credit': amount > 0.0 and amount or 0.0,
                    'partner_id': partner_id
                })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
            move.update({'line_ids': line_ids})
            draft = move_obj.create(move)
            self.move_id = draft.id
            draft.post()
            self.state = 'approve'
            return True

    def view_journal_entry(self):
        if self.move_id:
            return {
                'view_mode': 'form',
                'res_id': self.move_id.id,
                'res_model': 'account.move',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
            }
