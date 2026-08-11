import base64

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, exceptions, _
from odoo.addons.hr_payroll.models.browsable_object import BrowsableObject, InputLine, WorkedDays, Payslips
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round, date_utils
from odoo.tools.misc import format_date
from odoo.tools.safe_eval import safe_eval
from num2words import num2words
from datetime import time
from odoo import tools
from odoo.addons.helper import validator
from pytz import timezone

class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Pay Slip'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _order = 'date_to desc'

    struct_id = fields.Many2one('hr.payroll.structure', string='Structure',
                                help='Defines the rules that have to be applied to this payslip, accordingly '
                                     'to the contract chosen. If you let empty the field contract, this field isn\'t '
                                     'mandatory anymore and thus the rules applied will be all the rules set on the '
                                     'structure of all contracts of the employee valid for the chosen period')
    name = fields.Char(string='Payslip Name', required=True)
    #readonly=True, , states = {'draft': [('readonly', False)], 'verify': [('readonly', False)]}

    number = fields.Char(string='Salary Slip Number', copy=False)
    ref_note = fields.Char(string='Reference', copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    #, readonly = True, states = {'draft': [('readonly', False)], 'verify': [('readonly', False)]}, domain = "['|', ('company_id', '=', False), ('company_id', '=', company_id)]"

    id_card_no = fields.Char(string="Employee ID", groups="hr.group_hr_user",
                             related='employee_id.id_card_no')
    device_user_id = fields.Char(string='Biometric Device ID',
                                 related='employee_id.device_user_id')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    inter_company_id = fields.Many2one("internal.company", string="Inter Company", ondelete="restrict", related="user_work_location_id.inter_company_id", store=True)

    department_id = fields.Many2one('hr.department', string='Department', help='Employee Department')
    date_from = fields.Date(string='From', required=True,
                            default=lambda self: fields.Date.to_string(
                                date.today().replace(day=1) - relativedelta(months=1)),
                            )
    date_to = fields.Date(string='To', required=True,
                          default=lambda self: fields.Date.to_string(
                              ((date.today().replace(day=1) - relativedelta(months=1)) + relativedelta(months=+1, day=1,
                                                                                                       days=-1))),
                          )
    # this is chaos: 4 states are defined, 3 are used ('verify' isn't) and 5 exist ('confirm' seems to have existed)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft',
        help="""* When the payslip is created the status is \'Draft\'
                \n* If the payslip is under verification, the status is \'Waiting\'.
                \n* If the payslip is confirmed then status is set to \'Done\'.
                \n* When user cancel payslip the status is \'Rejected\'.""")
    line_ids = fields.One2many('hr.payslip.line', 'slip_id', string='Payslip Lines')
    company_id = fields.Many2one('res.company', string='Company', copy=False, required=True,
                                 default=lambda self: self.env.company)
    worked_days_line_ids = fields.One2many('hr.payslip.worked_days', 'payslip_id',
                                           string='Payslip Worked Days', copy=True)
    input_line_ids = fields.One2many('hr.payslip.input', 'payslip_id', string='Payslip Inputs')
    paid = fields.Boolean(string='Made Payment Order ? ', copy=False)
    note = fields.Text(string='Internal Note')
    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  domain="[('company_id', '=', company_id)]")
    credit_note = fields.Boolean(string='Credit Note', help="Indicates this payslip has a refund of another")
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Batch Name',
                                     copy=False,
                                     ondelete='cascade',
                                     domain="[('company_id', '=', company_id)]")
    compute_date = fields.Date('Computed On')
    basic_wage = fields.Monetary(compute='_compute_basic_net')
    net_wage = fields.Monetary(compute='_compute_basic_net')
    currency_id = fields.Many2one(related='contract_id.currency_id')
    warning_message = fields.Char(readonly=True)
    is_paid = fields.Boolean(string='Payment Paid?', copy=False)
    salary_payment_id = fields.Many2one('salary.payment', string='Salary Payment', copy=False,
                                        ondelete='cascade',
                                        domain="[('company_id', '=', company_id)]")
    emp_private_address_id = fields.Many2one(related='employee_id.address_home_id', string='Private Address')
    disbursement_type = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('bank_cash', 'Bank & Cash')
    ], string="Payment Type")
    s_bank_name = fields.Many2one('hr.bank', string="Salary Bank Name", help="Salary A/C Bank Name")
    s_bank_account_no = fields.Char(string='Salary Account No', help='Salary Account No')

    # bank_account_id = fields.Many2one('account.account', string="Bank Account")
    bank_amount = fields.Monetary(string="Bank Amount", help="Bank Amount")
    # cash_account_id = fields.Many2one('account.account', string="Cash Account")
    cash_amount = fields.Monetary(string="Cash Amount", help="Cash Amount")
    payment_date = fields.Date(string="Payment Date")

    bank_payment_move_id = fields.Many2one('account.move', string='Bank Payment Entry')
    cash_payment_move_id = fields.Many2one('account.move', string='Cash Payment Entry')
    #batch_payment_id = fields.Many2one('salary.payment', string='Batch Payment Ref.')

    def amount_in_words(self, amount):
        amount_in_word = "".join(num2words(amount, lang='en_IN').title().replace("-", " ")).replace(",",
                                                                                                    "") + " Taka Only."
        return amount_in_word

    @api.onchange('cash_amount', 'bank_amount')
    def _onchange_amount_constraint_check(self):
        for rec in self:
            cash_amt = rec.cash_amount
            if cash_amt < 0:
                raise exceptions.ValidationError("Amount cannot be negative value")
            bank_amt = rec.bank_amount
            if bank_amt < 0:
                raise exceptions.ValidationError("Amount cannot be negative value")

    @api.onchange('worked_days_line_ids', 'input_line_ids')
    def _onchange_worked_days_inputs(self):
        if self.line_ids and self.state in ['draft', 'verify']:
            values = [(5, 0, 0)] + [(0, 0, line_vals) for line_vals in self._get_payslip_lines()]
            self.update({'line_ids': values})

    def _compute_basic_net(self):
        for payslip in self:
            payslip.basic_wage = payslip._get_salary_line_total('BASIC')
            payslip.net_wage = payslip._get_salary_line_total('NET')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if any(self.filtered(lambda payslip: payslip.date_from > payslip.date_to)):
            raise ValidationError(_("Payslip 'Date From' must be earlier 'Date To'."))

    @api.constrains('employee_id', 'struct_id', 'date_from', 'date_to')
    def _check_duplicate_payslip(self):
        for rec in self:
            msg = 'In same period and same structure, Employee "%s" Payslip ' % rec.employee_id.name
            envobj = self.env['hr.payslip']
            conditionlist = [('employee_id', '=', rec.employee_id.id), ('struct_id', '=', rec.struct_id.id),
                             ('date_from', '>=', rec.date_from), ('date_to', '<=', rec.date_from),
                             ('state', '!=', 'cancel')]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    def action_payslip_draft(self):
        return self.write({'state': 'draft'})

    def action_payslip_done(self):
        if any(slip.state == 'cancel' for slip in self):
            raise ValidationError(_("You can't validate a cancelled payslip."))
        net_sal_line = self.line_ids.filtered(lambda x: x.code == 'NET')
        if net_sal_line.amount < 0:
            raise ValidationError(_("You can't validate a payslip with a negative Net Salary."))
        if net_sal_line.amount != (self.cash_amount + self.bank_amount):
            raise exceptions.ValidationError("Total amount must be equal to NET amount")

        # emp_obj = self.env['hr.employee'].search(
        #     [('id', '=', self.employee_id.id), ('active', '=', True), ('employee_type_id.is_deny_pf', '=', False)],
        #     limit=1)
        # if emp_obj:
        #if self.contract_id.is_pf_allowed or self.employee_id.employee_type_id.is_deny_pf == False:

        pf_line = self.line_ids.filtered(lambda x: x.code == 'PF')
        pf_amt = (-1) * pf_line.amount
        if pf_amt > 0:
            pf_model_chk = self.env['ir.model'].sudo().search([('model', '=', 'hr.employee.pf')], limit=1)
            if pf_model_chk:
                cpf_type = self.env.company.cpf_type
                cpf_percentage = self.env.company.cpf_percentage

                pf_obj = self.env['hr.employee.pf'].sudo().search([('employee_id', '=', self.employee_id.id),
                        ('year', '=', str(self.date_to.year)), ('month', '=', str(self.date_to.month).zfill(2)),
                        ('contribution_type', '=', 'salary')], limit=1)
                if pf_obj:
                    if pf_obj.state == 'draft':
                        cpf_amt = 0
                        if cpf_type == 'cpf_pf':
                            cpf_amt = round((pf_amt * cpf_percentage) / 100, 2)
                        elif cpf_type == 'cpf_basic':
                            basic = self.line_ids.filtered(lambda x: x.code == 'BASIC').amount
                            cpf_amt = round((basic * cpf_percentage) / 100, 2)
                        elif cpf_type == 'cpf_gross':
                            gross_salary = self.employee_id.contract_id.gross_salary
                            cpf_amt = round((gross_salary * cpf_percentage) / 100, 2)

                        pf_obj.pf_amount = pf_amt
                        pf_obj.cpf_amount = cpf_amt

                else:
                    cpf_amt = 0
                    if cpf_type == 'cpf_pf':
                        cpf_amt = round((pf_amt * cpf_percentage) / 100, 2)
                    elif cpf_type == 'cpf_basic':
                        basic = self.line_ids.filtered(lambda x: x.code == 'BASIC').amount
                        cpf_amt = round((basic * cpf_percentage) / 100, 2)
                    elif cpf_type == 'cpf_gross':
                        gross_salary = self.employee_id.contract_id.gross_salary
                        cpf_amt = round((gross_salary * cpf_percentage) / 100, 2)

                    self.env['hr.employee.pf'].sudo().create([{
                        'employee_id': self.employee_id.id,
                        'year': str(self.date_to.year),
                        'month': str(self.date_to.month).zfill(2),
                        'pf_amount': pf_amt,
                        'cpf_amount': cpf_amt,
                        'contribution_type': 'salary'
                    }])

        self.write({'state': 'done'})
        self.mapped('payslip_run_id').action_close()

        # ---------- Disciplinary Action Deduction
        if self.employee_id:
            employee_id = self.employee_id.id
            date_from = self.date_from
            date_to = self.date_to
            input_lines = self.input_line_ids

            payroll_codes = [line.code for line in input_lines if line.code == 'DISP' and line.amount > 0]
            if len(payroll_codes) > 0:
                punishments_rows = self.env['hr.punishments'].search([
                    ('employee_id', '=', employee_id),
                    ('payslip_date', '>=', date_from),
                    ('payslip_date', '<=', date_to),
                    ('state', '=', 'approve'),
                    ('amount', '>', 0),
                    ('allow_payslip', '=', True),
                    ('is_deducted', '=', False)
                ])
                for rec in punishments_rows:
                    rec.is_deducted = True
                    rec.payslip_id = self.id

        # ------------ payslip file generate??
        # if self.env.context.get('payslip_generate_pdf'):
        #     for payslip in self:
        #         if not payslip.struct_id or not payslip.struct_id.report_id:
        #             report = self.env.ref('hr_payroll.action_report_payslip', False)
        #         else:
        #             report = payslip.struct_id.report_id
        #         pdf_content, content_type = report.render_qweb_pdf(payslip.id)
        #         if payslip.struct_id.report_id.print_report_name:
        #             pdf_name = safe_eval(payslip.struct_id.report_id.print_report_name, {'object': payslip})
        #         else:
        #             pdf_name = _("Payslip")
        #         self.env['ir.attachment'].sudo().create({
        #             'name': pdf_name,
        #             'type': 'binary',
        #             'datas': base64.encodestring(pdf_content),
        #             'res_model': payslip._name,
        #             'res_id': payslip.id
        #         })

    def action_payslip_cancel(self):
        if self.filtered(lambda slip: slip.state == 'done'):
            raise UserError(_("Cannot cancel a payslip that is done."))
        self.write({'state': 'cancel'})
        self.mapped('payslip_run_id').action_close()

    def refund_sheet(self):
        for payslip in self:
            copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name})
            copied_payslip.compute_sheet()
            copied_payslip.action_payslip_done()
        formview_ref = self.env.ref('hr_payroll.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'),
                      (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            contract_id = val.get('contract_id')
            if contract_id and not val.get('struct_id'):
                val['struct_id'] = self.env['hr.contract'].browse(contract_id).structure_type_id.default_struct_id.id
        res = super(HrPayslip, self).create(vals)
        return res

    def unlink(self):
        for rec in self:
            if any(rec.filtered(lambda payslip: payslip.state not in ('draft', 'cancel'))):
                raise UserError(_('You cannot delete a payslip which is not draft or cancelled!'))
        return super(HrPayslip, self).unlink()

    def refresh_payment_type(self):
        for payslip in self:
            payslip.disbursement_type = payslip.contract_id.disbursement_type
            payslip.s_bank_name = payslip.contract_id.s_bank_name
            payslip.s_bank_account_no = payslip.contract_id.s_bank_account_no
            payslip.compute_sheet()

    def compute_sheet(self):
        for payslip in self.filtered(lambda slip: slip.state not in ['cancel', 'done']):
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            # delete old payslip lines
            payslip.line_ids.unlink()
            lines = [(0, 0, line) for line in payslip._get_payslip_lines()]
            payslip.write({'line_ids': lines, 'number': number, 'state': 'verify', 'compute_date': fields.Date.today()})
            line_row = payslip.line_ids.filtered(lambda x: x.code == 'NET').amount

            bank_amount = 0
            cash_amount = 0
            bank_fixed = 0
            cash_fixed = 0

            bank_fixed_line = payslip.line_ids.filtered(lambda x: x.salary_rule_id.disbursement_type == 'bank')
            cash_fixed_line = payslip.line_ids.filtered(lambda x: x.salary_rule_id.disbursement_type == 'cash')
            if bank_fixed_line:
                bank_fixed = sum(bank_fixed_line.mapped('amount'))
            if cash_fixed_line:
                cash_fixed = sum(cash_fixed_line.mapped('amount'))

            if payslip.disbursement_type == 'bank':
                if cash_fixed > 0:
                    payslip.disbursement_type = 'bank_cash'
                    cash_amount = cash_fixed
                    bank_amount = line_row - cash_fixed
                else:
                    bank_amount = line_row
            elif payslip.disbursement_type == 'cash':
                if bank_fixed > 0:
                    payslip.disbursement_type = 'bank_cash'
                    bank_amount = bank_fixed
                    cash_amount = line_row - bank_fixed
                else:
                    cash_amount = line_row
            else:
                if cash_fixed > 0:
                    cash_amount = cash_fixed
                    bank_amount = line_row - cash_fixed
                elif bank_fixed > 0:
                    bank_amount = bank_fixed
                    cash_amount = line_row - bank_fixed
                else:
                    bank_amount = line_row / 2
                    cash_amount = line_row / 2

            payslip.bank_amount = bank_amount
            payslip.cash_amount = cash_amount

            # if payslip.disbursement_type == 'bank':
            #     payslip.bank_amount = line_row
            # elif payslip.disbursement_type == 'cash':
            #     payslip.cash_amount = line_row
            # else:
            #     if bank_fixed > 0:
            #         bank_amount = bank_fixed
            #     if cash_fixed > 0:
            #         cash_amount = cash_fixed
            #
            #     payslip.bank_amount = line_row / 2
            #     payslip.cash_amount = line_row / 2


        return True

    def _round_days(self, work_entry_type, days):
        if work_entry_type.round_days != 'NO':
            precision_rounding = 0.5 if work_entry_type.round_days == "HALF" else 1
            day_rounded = float_round(days, precision_rounding=precision_rounding,
                                      rounding_method=work_entry_type.round_days_type)
            return day_rounded
        return days

    def _get_worked_day_lines(self):
        """
        :returns: a list of dict containing the worked days values that should be applied for the given payslip
        """
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        contract = self.contract_id
        if contract.resource_calendar_id:
            paid_amount = self._get_contract_wage()
            unpaid_work_entry_types = self.struct_id.unpaid_work_entry_type_ids.ids

            work_hours = contract._get_work_hours(self.date_from, self.date_to)
            total_hours = sum(work_hours.values()) or 1
            work_hours_ordered = sorted(work_hours.items(), key=lambda x: x[1])
            biggest_work = work_hours_ordered[-1][0] if work_hours_ordered else 0
            add_days_rounding = 0
            for work_entry_type_id, hours in work_hours_ordered:
                work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
                is_paid = work_entry_type_id not in unpaid_work_entry_types
                calendar = contract.resource_calendar_id
                days = round(hours / calendar.hours_per_day, 5) if calendar.hours_per_day else 0
                if work_entry_type_id == biggest_work:
                    days += add_days_rounding
                day_rounded = self._round_days(work_entry_type, days)
                add_days_rounding += (days - day_rounded)
                attendance_line = {
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type_id,
                    'number_of_days': day_rounded,
                    'number_of_hours': hours,
                    'amount': hours * paid_amount / total_hours if is_paid else 0,
                }
                res.append(attendance_line)
        return res

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = []
        # fill only if the contract as a working schedule linked
        for contract in contracts.filtered(lambda contract: contract.resource_calendar_id):
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)

            # compute leave days
            leaves = {}
            calendar = contract.resource_calendar_id
            tz = timezone(calendar.tz)
            day_leave_intervals = contract.employee_id.list_leaves(day_from, day_to,
                                                                   calendar=contract.resource_calendar_id)
            for day, hours, leave in day_leave_intervals:
                holiday = leave.holiday_id
                current_leave_struct = leaves.setdefault(holiday.holiday_status_id, {
                    'name': holiday.holiday_status_id.name or _('Global Leaves'),
                    'sequence': 5,
                    'code': holiday.holiday_status_id.code or 'GLOBAL',
                    'number_of_days': 0.0,
                    'number_of_hours': 0.0,
                    'contract_id': contract.id,
                })
                current_leave_struct['number_of_hours'] -= hours
                work_hours = calendar.get_work_hours_count(
                    tz.localize(datetime.combine(day, time.min)),
                    tz.localize(datetime.combine(day, time.max)),
                    compute_leaves=False,
                )
                if work_hours:
                    current_leave_struct['number_of_days'] -= hours / work_hours

            # compute worked days
            work_data = contract.employee_id._get_work_days_data(
                day_from,
                day_to,
                calendar=contract.resource_calendar_id,
                compute_leaves=False,
            )

            attendances = {
                'name': _("Normal Working Days paid at 100%"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': work_data['days'],
                'number_of_hours': work_data['hours'],
                'contract_id': contract.id,
            }

            res.append(attendances)
            res.extend(leaves.values())
        return res
    @api.model
    def get_inputs(self, contracts=False, date_from=False, date_to=False):
        res = []
        # not used
        # structure_ids = contracts.get_all_structures()
        # inputs = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        # ---- end not used
        if self.struct_id:
            inputs = self.struct_id.input_line_type_ids
            for input in inputs:
                input_data = {
                    'input_type_id': input.id,
                    'name': input.name,
                    'code': input.code,
                    # 'contract_id': contract.id,
                }
                res += [input_data]
        else:
            for contract in contracts:
                if contract.struct_id:
                    inputs = contract.struct_id.input_line_type_ids
                    for input in inputs:
                        input_data = {
                            'input_type_id': input.id,
                            'name': input.name,
                            'code': input.code,
                            'contract_id': contract.id,
                        }
                        res += [input_data]
                if contract.bonus_struct_id:
                    inputs = contract.bonus_struct_id.input_line_type_ids
                    for input in inputs:
                        input_data = {
                            'input_type_id': input.id,
                            'name': input.name,
                            'code': input.code,
                            'contract_id': contract.id,
                        }
                        res += [input_data]

        # --- Disciplinary Action amount update
        if contracts[0]:
            employee_obj = contracts[0].employee_id
            if employee_obj:
                punishments_rows = self.env['hr.punishments'].search([
                    ('employee_id', '=', employee_obj.id),
                    ('payslip_date', '>=', date_from),
                    ('payslip_date', '<=', date_to),
                    ('state', '=', 'approve'),
                    ('amount', '>', 0),
                    ('allow_payslip', '=', True),
                    ('is_deducted', '=', False)
                ])
                for punish_obj in punishments_rows:
                    punish_amount = punish_obj.amount
                    for result in res:
                        if result.get('code') == 'DISP':
                            total_punish_amt = result.get('amount') or 0
                            result['amount'] = total_punish_amt + punish_amount

        return res

    # not used
    # def get_other_inputs(self,contract=False,date_from=False,date_to=False):
    #     """
    #     :returns: a list of dict containing the input values that should be applied for the given payslip
    #     """
    #     contract = self.contract_id
    #
    #     self.update({
    #         'input_line_ids': None,
    #     })
    #
    #     input_line_ids = self.get_inputs(contract,date_from,date_to)
    #
    #     res['value'].update({
    #         #'worked_days_line_ids': worked_days_line_ids,
    #         'input_line_ids': input_line_ids
    #     })
    #     return res

    # if contract.struct_id:
    #     input_ids = contract.struct_id.input_line_type_ids
    #
    #     adv_obj = self.env['salary.advance'].search(
    #         [('employee_id', '=', self.employee_id.id), ('state', '=', 'approve'),
    #          ('employee_contract_id', '=', self.contract_id.id), ('is_deducted', '=', False)], order='date',
    #         limit=1)
    #
    #     input_line = []
    #
    #     if input_ids:
    #         for rec in input_ids:
    #             if rec['code'] == 'SAR':
    #                 input_data = {
    #                     'input_type_id': rec.id,
    #                     'amount': adv_obj['advance']
    #                 }
    #                 input_line.append((0, 0, input_data))
    #             elif rec['code'] == 'INSUR':
    #                 input_data = {
    #                     'input_type_id': rec.id,
    #                 }
    #                 input_line.append((0, 0, input_data))
    #         self.update({
    #             'input_line_ids': input_line
    #         })

    def _get_base_local_dict(self):
        return {
            'float_round': float_round
        }

    def _get_payslip_lines(self):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = localdict['categories'].dict.get(category.code, 0) + amount
            return localdict

        self.ensure_one()
        result = {}
        rules_dict = {}
        worked_days_dict = {line.code: line for line in self.worked_days_line_ids if line.code}
        inputs_dict = {line.code: line for line in self.input_line_ids if line.code}

        employee = self.employee_id
        contract = self.contract_id

        localdict = {
            **self._get_base_local_dict(),
            **{
                'categories': BrowsableObject(employee.id, {}, self.env),
                'rules': BrowsableObject(employee.id, rules_dict, self.env),
                'payslip': Payslips(employee.id, self, self.env),
                'worked_days': WorkedDays(employee.id, worked_days_dict, self.env),
                'inputs': InputLine(employee.id, inputs_dict, self.env),
                'employee': employee,
                'contract': contract
            }
        }
        for rule in sorted(self.struct_id.rule_ids, key=lambda x: x.sequence):
            localdict.update({
                'result': None,
                'result_qty': 1.0,
                'result_rate': 100})
            if rule._satisfy_condition(localdict):
                amount, qty, rate = rule._compute_rule(localdict)
                # check if there is already a rule computed with that code
                previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                # set/overwrite the amount computed for this rule in the localdict
                tot_rule = amount * qty * rate / 100.0
                localdict[rule.code] = tot_rule
                rules_dict[rule.code] = rule
                # sum the amount for its salary category
                localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                # create/overwrite the rule in the temporary results
                result[rule.code] = {
                    'sequence': rule.sequence,
                    'code': rule.code,
                    'name': rule.name,
                    'note': rule.note,
                    'salary_rule_id': rule.id,
                    'contract_id': contract.id,
                    'employee_id': employee.id,
                    'amount': amount,
                    'quantity': qty,
                    'rate': rate,
                    'slip_id': self.id,
                }
        return result.values()

    # not used
    # def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
    #
    #     # defaults
    #     res = {
    #         'value': {
    #             'line_ids': [],
    #             # delete old input lines
    #             'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
    #             # delete old worked days lines
    #             'worked_days_line_ids': [(2, x,) for x in self.worked_days_line_ids.ids],
    #             # 'details_by_salary_head':[], TODO put me back
    #             'name': '',
    #             'contract_id': False,
    #             'struct_id': False,
    #         }
    #     }
    #     if (not employee_id) or (not date_from) or (not date_to):
    #         return res
    #     ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
    #     employee = self.env['hr.employee'].browse(employee_id)
    #     locale = self.env.context.get('lang') or 'en_US'
    #     payslip_name = self.struct_id.payslip_name or _('Salary Slip')
    #     # res['value'].update({
    #     #     'name': _('Salary Slip of %s for %s') % (employee.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale))),            
    #     #     'company_id': employee.company_id.id,
    #     # })
    #     res['value'].update({
    #         'name': _('%s - %s - %s' % (payslip_name, employee.name or '', format_date(self.env, self.date_from, date_format="MMMM y"))),            
    #         'company_id': employee.company_id.id
    #     })
    #
    #     # self.name = '%s - %s - %s' % (
    #     #     payslip_name, self.employee_id.name or '', format_date(self.env, self.date_from, date_format="MMMM y"))
    #
    #     # if not self.env.context.get('contract'):
    #     #     # fill with the first contract of the employee
    #     #     contract_ids = self.get_contract(employee, date_from, date_to)
    #     # else:
    #     contract_ids = []
    #     if contract_id:
    #         # set the list of contract for which the input have to be filled
    #         contract_ids = [contract_id]
    #     else:
    #         pass
    #         # if we don't give the contract, then the input to fill should be for all current contracts of the employee
    #         #contract_ids = self.get_contract(employee, date_from, date_to)
    #
    #     if not contract_ids:
    #         return res
    #     contract = self.env['hr.contract'].browse(contract_ids[0])
    #
    #     res['value'].update({
    #         'contract_id': contract.id
    #     })
    #     struct = contract.struct_id
    #     if not struct:
    #         return res
    #     res['value'].update({
    #         'struct_id': struct.id,
    #     })
    #     # computation of the salary input
    #     contracts = self.env['hr.contract'].browse(contract_ids)
    #     #worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
    #     worked_days_line_ids = self._get_new_worked_days_lines()
    #
    #     input_line_ids = self.get_inputs(contract,date_from, date_to)
    #
    #     res['value'].update({
    #         'worked_days_line_ids': worked_days_line_ids,
    #         'input_line_ids': input_line_ids,
    #     })
    #     return res

    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        self.update({
            'input_line_ids': None,
        })
        # ----------

        if not self.emp_private_address_id:
            raise ValidationError(_('Private Address not mapped for employee: %s') % self.employee_id.name)

        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contracts = []

        self.company_id = employee.company_id
        self.user_work_location_id = employee.user_work_location_id
        self.department_id = employee.department_id
        if not self.contract_id or self.employee_id != self.contract_id.employee_id:  # Add a default contract if not already defined
            contracts = employee._get_contracts(date_from, date_to)

            if not contracts or not contracts[0].structure_type_id.default_struct_id:
                self.contract_id = False
                self.struct_id = False
                return
            self.contract_id = contracts[0]
            self.disbursement_type = self.contract_id.disbursement_type

            self.s_bank_name = self.contract_id.s_bank_name
            self.s_bank_account_no = self.contract_id.s_bank_account_no

            # if self.disbursement_type == 'bank':
            #     self.bank_account_id = self.contract_id.bank_account_id
            # elif self.disbursement_type == 'cash':
            #     self.cash_account_id = self.contract_id.cash_account_id
            # else:
            #     self.bank_account_id = self.contract_id.bank_account_id
            #     self.cash_account_id = self.contract_id.cash_account_id

            self.struct_id = contracts[0].structure_type_id.default_struct_id
        # line_row = self.env['hr.payslip.line'].search([('slip_id', '=', self.id)], order="id desc", limit=1)
        # print(line_row)
        payslip_name = self.struct_id.payslip_name or _('Salary Slip')
        self.name = '%s - %s - %s' % (
            payslip_name, self.employee_id.name or '', format_date(self.env, self.date_to, date_format="MMMM y"))

        if date_to > date_utils.end_of(fields.Date.today(), 'month'):
            self.warning_message = _(
                "This payslip can be erroneous! Work entries may not be generated for the period from %s to %s." %
                (date_utils.add(date_utils.end_of(fields.Date.today(), 'month'), days=1), date_to))
        else:
            self.warning_message = False

        self.worked_days_line_ids = self._get_new_worked_days_lines()
        input_line_ids = self.get_inputs(self.contract_id, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines

        #---------
        # computation of the salary input
        #contracts = self.env['hr.contract'].browse(contracts)
        # if contracts:
        #     worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        #     worked_days_lines = self.worked_days_line_ids.browse([])
        #     for r in worked_days_line_ids:
        #         worked_days_lines += worked_days_lines.new(r)
        #     self.worked_days_line_ids = worked_days_lines
        #
        #     input_line_ids = self.get_inputs(contracts, date_from, date_to)
        #     input_lines = self.input_line_ids.browse([])
        #     for r in input_line_ids:
        #         input_lines += input_lines.new(r)
        #     self.input_line_ids = input_lines

        # self.input_line_ids = input_line_ids

    # @api.onchange('employee_id')
    # def _onchange_employee_inputs(self):
    #     self.get_other_inputs()

    def _get_new_worked_days_lines(self):
        if self.struct_id.use_worked_day_lines:
            # computation of the salary worked days
            worked_days_line_values = self._get_worked_day_lines()
            worked_days_lines = self.worked_days_line_ids.browse([])
            for r in worked_days_line_values:
                worked_days_lines |= worked_days_lines.new(r)
            return worked_days_lines
        else:
            return [(5, False, False)]

    # unused
    # def _get_new_input_lines(self):
    #     if self.struct_id.regular_pay:
    #         # computation of the salary worked days
    #         input_line_values = self._get_inputs()
    #         print(input_line_values)
    #         input_lines = self.input_line_ids.browse([])
    #         print(input_lines)
    #         for r in input_line_values:
    #             input_lines |= input_lines.new(r)
    #         return input_lines
    #     else:
    #         return [(5, False, False)]

    def _get_salary_line_total(self, code):
        lines = self.line_ids.filtered(lambda line: line.code == code)
        return sum([line.total for line in lines])

    def action_print_payslip(self):
        return {
            'name': 'Payslip',
            'type': 'ir.actions.act_url',
            'url': '/print/payslips?list_ids=%(list_ids)s' % {'list_ids': ','.join(str(x) for x in self.ids)},
        }

    def _get_contract_wage(self):
        self.ensure_one()
        return self.contract_id.wage

    def _get_paid_amount(self):
        self.ensure_one()
        if not self.worked_days_line_ids:
            return self._get_contract_wage()
        total_amount = 0
        for line in self.worked_days_line_ids:
            total_amount += line.amount
        return total_amount

    def _get_unpaid_amount(self):
        self.ensure_one()
        return self._get_contract_wage() - self._get_paid_amount()

    # -------- Salary-PF SMS
    def salary_pf_sms(self, employee_id=None, contact_no=None, disbursement_type=None, amount=None, payment_date=None,
                      payslip_date_to=None):
        if not contact_no:
            return False
            #raise UserError(_('Required Employee Mobile No.'))

        template_obj_pf = self.env['sms.template.custom'].sudo().search(
            [('type', '=', 'hr_pf'), ('is_active', '=', True)],
            limit=1)
        if template_obj_pf:
            pf_model_chk = self.env['ir.model'].sudo().search([('model', '=', 'hr.employee.pf')], limit=1)
            if pf_model_chk:
                sms_obj = self.env['sms.outbox.details'].sudo()

                sms_text = template_obj_pf.sms_format

                month_year = format_date(self.env, payslip_date_to, date_format="MMMM y")
                year = str(payslip_date_to.year)
                month = str(payslip_date_to.month).zfill(2)

                # current month pf, cpf, profit amount
                current_employee_pf_obj = self.env['hr.employee.pf'].sudo().search(
                    [('contribution_type', '=', 'salary'),('employee_id', '=', employee_id.id), ('year', '=', year), ('month', '=', month)], limit=1)
                current_pf_amt = current_employee_pf_obj.pf_amount
                current_cpf_amt = current_employee_pf_obj.cpf_amount
                #current_profit_amt = current_employee_pf_obj.profit_amount

                # as on date pf, cpf, profit amount
                total_employee_pf_obj = self.env['hr.employee.pf'].sudo().search([('contribution_type', '=', 'salary'),('employee_id', '=', employee_id.id)])
                total_pf_amt = round(sum(total_employee_pf_obj.mapped('pf_amount')),2)
                total_cpf_amt = round(sum(total_employee_pf_obj.mapped('cpf_amount')),2)

                total_employee_pf_obj2 = self.env['hr.employee.pf'].sudo().search(
                    [('contribution_type', '=', 'profit'), ('employee_id', '=', employee_id.id)])

                total_profit_amt = round(sum(total_employee_pf_obj2.mapped('pf_amount')) + sum(total_employee_pf_obj2.mapped('cpf_amount')),2)
                grand_total = total_pf_amt + total_cpf_amt + total_profit_amt

                final_sms = sms_text.replace('$employee_name', employee_id.name).replace('$employee_id_card', employee_id.id_card_no).replace('$amount', str(amount)).replace(
                    '$payment_date', payment_date).replace('$contact_no', contact_no).replace('$disbursement_type', disbursement_type).replace('$month_year', month_year).replace('$current_pf_amt', str(current_pf_amt)).replace('$current_cpf_amt', str(current_cpf_amt)).replace('$total_pf_amt', str(total_pf_amt)).replace('$total_cpf_amt', str(total_cpf_amt)).replace('$total_profit_amt', str(total_profit_amt)).replace('$payslip_date_to', payslip_date_to.strftime("%d-%b-%Y")).replace('$grand_total', str(grand_total))

                # print(final_sms)
                # pr

                sms_data = {'module_name': '6',
                            'source_ref': 'Payslip: ' + str(self.number),
                            'mobile_no': contact_no,
                            'msg_body': final_sms,
                            'is_header_sent': template_obj_pf.is_header_sent,
                            'is_footer_sent': template_obj_pf.is_footer_sent,
                            'header_text': template_obj_pf.header_text,
                            'footer_text': template_obj_pf.footer_text
                            }
                sms_obj.create(sms_data)

    # -------- Salary SMS
    def salary_sms(self, employee_id=None, contact_no=None, disbursement_type=None, amount=None, payment_date=None,
                   payslip_date_to=None):
        if not contact_no:
            return False
            # raise UserError(_('Required Employee Mobile No.'))

        template_obj = self.env['sms.template.custom'].sudo().search(
            [('type', '=', 'hr_salary'), ('is_active', '=', True)],
            limit=1)
        if template_obj:
            sms_obj = self.env['sms.outbox.details'].sudo()
            sms_text = template_obj.sms_format

            # amount = 0
            # if self.cash_amount:
            #     amount = amount + self.cash_amount
            # if self.bank_amount:
            #     amount = amount + self.bank_amount
            month_year = format_date(self.env, payslip_date_to, date_format="MMMM y")

            final_sms = sms_text.replace('$employee_name', employee_id.name).replace('$amount', str(amount)).replace('$payment_date', payment_date).replace('$contact_no', contact_no).replace('$disbursement_type', disbursement_type).replace('$month_year', month_year)

            sms_data = {'module_name': '6',
                        'source_ref': 'Payslip: ' + str(self.number),
                        'mobile_no': contact_no,
                        'msg_body': final_sms,
                        'is_header_sent': template_obj.is_header_sent,
                        'is_footer_sent': template_obj.is_footer_sent,
                        'header_text': template_obj.header_text,
                        'footer_text': template_obj.footer_text
                        }
            sms_obj.create(sms_data)


class HrPayslipLine(models.Model):
    _name = 'hr.payslip.line'
    _description = 'Payslip Line'
    _order = 'contract_id, sequence, code'

    name = fields.Char(required=True, translate=True)
    note = fields.Text(string='Description')
    sequence = fields.Integer(required=True, index=True, default=5,
                              help='Use to arrange calculation sequence')
    code = fields.Char(required=True,
                       help="The code of salary rules can be used as reference in computation of other rules. "
                            "In that case, it is case sensitive.")
    slip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Rule', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True, index=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    rate = fields.Float(string='Rate (%)', digits='Payroll Rate', default=100.0)
    amount = fields.Float(digits='Payroll')
    quantity = fields.Float(digits='Payroll', default=1.0)
    total = fields.Float(compute='_compute_total', string='Total', digits='Payroll', store=True)

    amount_select = fields.Selection(related='salary_rule_id.amount_select', readonly=True)
    amount_fix = fields.Float(related='salary_rule_id.amount_fix', readonly=True)
    amount_percentage = fields.Float(related='salary_rule_id.amount_percentage', readonly=True)
    appears_on_payslip = fields.Boolean(related='salary_rule_id.appears_on_payslip', readonly=True)
    category_id = fields.Many2one(related='salary_rule_id.category_id', readonly=True, store=True)
    cat_type = fields.Selection(related='salary_rule_id.cat_type')
    partner_id = fields.Many2one(related='salary_rule_id.partner_id', readonly=True, store=True)

    date_from = fields.Date(string='From', related="slip_id.date_from", store=True)
    date_to = fields.Date(string='To', related="slip_id.date_to", store=True)
    company_id = fields.Many2one(related='slip_id.company_id')

    @api.depends('quantity', 'amount', 'rate')
    def _compute_total(self):
        for line in self:
            line.total = float(line.quantity) * line.amount * line.rate / 100

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'employee_id' not in values or 'contract_id' not in values:
                payslip = self.env['hr.payslip'].browse(values.get('slip_id'))
                values['employee_id'] = values.get('employee_id') or payslip.employee_id.id
                values['contract_id'] = values.get('contract_id') or payslip.contract_id and payslip.contract_id.id
                if not values['contract_id']:
                    raise UserError(_('You must set a contract to create a payslip line.'))
        return super(HrPayslipLine, self).create(vals_list)


class HrPayslipWorkedDays(models.Model):
    _name = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'
    _order = 'payslip_id, sequence'

    name = fields.Char(related='work_entry_type_id.name', string='Description', readonly=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(string='Code', related='work_entry_type_id.code')
    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Type',
                                         help="The code that can be used in the salary rules") # required=True,
    number_of_days = fields.Float(string='Number of Days')
    number_of_hours = fields.Float(string='Number of Hours')
    amount = fields.Monetary(string='Amount', default=0.0)
    contract_id = fields.Many2one(related='payslip_id.contract_id', string='Contract', required=True,
                                  help="The contract for which applied this worked days")
    currency_id = fields.Many2one('res.currency', related='payslip_id.currency_id')


class HrPayslipInput(models.Model):
    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _order = 'payslip_id, sequence'

    name = fields.Char(related='input_type_id.name', string="Name", readonly=True)
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    input_type_id = fields.Many2one('hr.payslip.input.type', string='Description', required=True)
    code = fields.Char(related='input_type_id.code', required=True,
                       help="The code that can be used in the salary rules")
    amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
                               "1% commission of basic salary for per product can defined in expression "
                               "like result = inputs.SALEURO.amount * contract.wage*0.01.")
    contract_id = fields.Many2one(related='payslip_id.contract_id', string='Contract', required=True,
                                  help="The contract for which applied this input")
    struct_id = fields.Many2one('hr.payroll.structure', string='Structure', related='payslip_id.struct_id')

    @api.onchange('struct_id')
    def _onchange_struct_id(self):
        return {'domain': {'input_type_id': ['|', ('id', 'in', self.payslip_id.struct_id.input_line_type_ids.ids),
                                             ('struct_ids', '=', False)]}}


class HrPayslipInputType(models.Model):
    _name = 'hr.payslip.input.type'
    _description = 'Payslip Input Type'

    name = fields.Char(string='Description', required=True)
    code = fields.Char(required=True, help="The code that can be used in the salary rules")
    struct_ids = fields.Many2many('hr.payroll.structure', string='Avaibility in Structure',
                                  help='This input will be only available in those structure. If empty, it will be available in all payslip.')
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.company.country_id)


class HrPayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _description = 'Payslip Batches'
    _order = 'date_end desc'

    name = fields.Char()
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verify'),
        ('close', 'Done'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(string='Date From', required=True,
                             default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True,
                           default=lambda self: fields.Date.to_string(
                               (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    credit_note = fields.Boolean(string='Credit Note',
                                 help="If its checked, indicates that all payslips generated from here are refund payslips.")
    payslip_count = fields.Integer(compute='_compute_payslip_count')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True,
                                 default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')])

    @api.onchange('user_work_location_id', 'date_from', 'date_end')
    def onchange_employee(self):
        self.name = 'Batch Payslip: %s - %s' % (self.user_work_location_id.display_name or '',
                                                format_date(self.env,
                                                            self.date_end,
                                                            date_format="MMMM y"))

    def _compute_payslip_count(self):
        for payslip_run in self:
            payslip_run.payslip_count = len(self.slip_ids)

    def action_draft(self):
        return self.write({'state': 'draft'})

    def action_close(self):
        if self._are_payslips_ready():
            self.write({'state': 'close'})

    def action_validate(self):
        slip_ids = self.mapped('slip_ids').filtered(lambda slip: slip.state != 'cancel')
        for rec in slip_ids:
            rec.action_payslip_done()
        self.action_close()

    def action_open_payslips(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [['id', 'in', self.slip_ids.ids]],
            "name": "Payslips",
        }

    def _are_payslips_ready(self):
        return all(slip.state in ['done', 'cancel'] for slip in self.mapped('slip_ids'))


class ContributionRegisterReport(models.AbstractModel):
    _name = 'report.hr_payroll.contribution_register'
    _description = 'Model for Printing hr.payslip.line grouped by register'

    def _get_report_values(self, docids, data):
        docs = []
        lines_data = {}
        lines_total = {}

        for result in self.env['hr.payslip.line'].read_group([('id', 'in', docids)],
                                                             ['partner_id', 'total', 'ids:array_agg(id)'],
                                                             ['partner_id']):
            if result['partner_id']:
                docid = result['partner_id'][0]
                docs.append(docid)
                lines_data[docid] = self.env['hr.payslip.line'].browse(result['ids'])
                lines_total[docid] = result['total']

        return {
            'docs': self.env['res.partner'].browse(docs),
            'data': data,
            'lines_data': lines_data,
            'lines_total': lines_total
        }


class PayslipReport(models.AbstractModel):
    _name = 'report.hr_payroll.report_payslip'
    _description = 'Model for Printing hr.payslip'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_color_obj = self.env['report.color.settings'].search([('report_name', '=', '01')], limit=1)

        if report_color_obj.color1:
            color1 = report_color_obj.color1 if report_color_obj.color1.startswith(
                "#") else '#' + report_color_obj.color1
        else:
            color1 = '#FFFFFF'
        if report_color_obj.color2:
            color2 = report_color_obj.color2 if report_color_obj.color2.startswith(
                "#") else '#' + report_color_obj.color2
        else:
            color2 = '#FFFFFF'
        if report_color_obj.color3:
            color3 = report_color_obj.color3 if report_color_obj.color3.startswith(
                "#") else '#' + report_color_obj.color3
        else:
            color3 = '#FFFFFF'

        data = {
            'color1': color1,
            'color2': color2,
            'color3': color3
        }

        docargs = {
            'doc_ids': docids,
            'doc_model': "hr.payslip",
            'docs': self.env['hr.payslip'].browse(docids),
            'data': data,
        }

        return docargs


class PayslipReportExtra(models.AbstractModel):
    _name = 'report.hr_payroll.report_payslip_extra'
    _description = 'Model for Printing hr.payslip'

    @api.model
    def _get_report_values(self, docids, data=None):
        report_color_obj = self.env['report.color.settings'].search([('report_name', '=', '01')], limit=1)

        if report_color_obj.color1:
            color1 = report_color_obj.color1 if report_color_obj.color1.startswith(
                "#") else '#' + report_color_obj.color1
        else:
            color1 = '#FFFFFF'
        if report_color_obj.color2:
            color2 = report_color_obj.color2 if report_color_obj.color2.startswith(
                "#") else '#' + report_color_obj.color2
        else:
            color2 = '#FFFFFF'
        if report_color_obj.color3:
            color3 = report_color_obj.color3 if report_color_obj.color3.startswith(
                "#") else '#' + report_color_obj.color3
        else:
            color3 = '#FFFFFF'

        data = {
            'color1': color1,
            'color2': color2,
            'color3': color3
        }

        docargs = {
            'doc_ids': docids,
            'doc_model': "hr.payslip",
            'docs': self.env['hr.payslip'].browse(docids),
            'data': data,
        }

        return docargs