from odoo import fields, models, api
from odoo.exceptions import UserError
import datetime
from datetime import datetime, timedelta, date
from calendar import monthrange
from dateutil.relativedelta import relativedelta


class MissingPFWizard(models.TransientModel):
    _name = "missing.pf.wizard"
    _description = "Missing PF Wizard"

    year = fields.Selection(
        [(str(yearno), str(yearno)) for yearno in range(2021, ((date.today().year) + 5))],
        default=str(date.today().year), string='Year', required=True)

    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month', required=True)

    def missing_pf_generate(self):
        m = int(self.month)
        y = int(self.year)
        ndays = monthrange(y, m)[1]
        start_date = date(y, m, 1)
        end_date = date(y, m, ndays)

        slip_obj = self.env['hr.payslip'].sudo().search(
            [('state', '=', 'done'), ('date_from', '>=', start_date), ('date_to', '<=', end_date)])

        for rec in slip_obj:
            pf_line = rec.line_ids.filtered(lambda x: x.code == 'PF')
            pf_amt = (-1) * pf_line.amount

            pf_obj = self.env['hr.employee.pf'].sudo().search(
                [('employee_id', '=', rec.employee_id.id), ('year', '=', str(rec.date_from.year)),
                 ('month', '=', str(rec.date_from.month).zfill(2)), ('contribution_type', '=', 'salary')], limit=1)
            if pf_obj:
                if pf_obj.state != 'draft':
                    continue
                else:
                    if pf_amt > 0:
                        cpf_type = self.env.company.cpf_type
                        cpf_percentage = self.env.company.cpf_percentage
                        cpf_amt = 0
                        if cpf_type == 'cpf_pf':
                            cpf_amt = round((pf_amt * cpf_percentage) / 100, 2)
                        elif cpf_type == 'cpf_basic':
                            basic = rec.line_ids.filtered(lambda x: x.code == 'BASIC').amount
                            cpf_amt = round((basic * cpf_percentage) / 100, 2)
                        elif cpf_type == 'cpf_gross':
                            gross_salary = rec.employee_id.contract_id.gross_salary
                            cpf_amt = round((gross_salary * cpf_percentage) / 100, 2)

                        pf_obj.pf_amount = pf_amt
                        pf_obj.cpf_amount = cpf_amt
                    else:
                        pf_obj.sudo().unlink()
            else:
                if pf_amt > 0:
                    cpf_type = self.env.company.cpf_type
                    cpf_percentage = self.env.company.cpf_percentage
                    cpf_amt = 0
                    if cpf_type == 'cpf_pf':
                        cpf_amt = round((pf_amt * cpf_percentage) / 100, 2)
                    elif cpf_type == 'cpf_basic':
                        basic = rec.line_ids.filtered(lambda x: x.code == 'BASIC').amount
                        cpf_amt = round((basic * cpf_percentage) / 100, 2)
                    elif cpf_type == 'cpf_gross':
                        gross_salary = rec.employee_id.contract_id.gross_salary
                        cpf_amt = round((gross_salary * cpf_percentage) / 100, 2)

                    self.env['hr.employee.pf'].sudo().create([{
                        'employee_id': rec.employee_id.id,
                        'year': str(rec.date_from.year),
                        'month': str(rec.date_from.month).zfill(2),
                        'pf_amount': pf_amt,
                        'cpf_amount': cpf_amt,
                        'contribution_type': 'salary'
                    }])

    def cpf_generate(self):
        pf_rows = self.env['hr.employee.pf'].sudo().search(
            [('year', '=', self.year), ('month', '=', self.month), ('contribution_type', '=', 'salary'),
             ('state', '=', 'draft')])
        cpf_type = self.env.company.cpf_type
        cpf_percentage = self.env.company.cpf_percentage
        for rec in pf_rows:
            cpf_amt = 0
            if cpf_type == 'cpf_pf':
                cpf_amt = round((rec.pf_amount * cpf_percentage) / 100, 2)
            elif cpf_type == 'cpf_basic':
                basic = rec.employee_id.contract_id.wage
                cpf_amt = round((basic * cpf_percentage) / 100, 2)
            elif cpf_type == 'cpf_gross':
                gross_salary = rec.employee_id.contract_id.gross_salary
                cpf_amt = round((gross_salary * cpf_percentage) / 100, 2)

            rec.cpf_amount = cpf_amt


class PFDoneWizard(models.TransientModel):
    _name = "pf.done.wizard"
    _description = "PF Done Wizard"

    def _get_year(self):
        """ Get company start year and display_year from res_company """
        year_list = []
        company = self.env.company
        if company.start_date:
            start_year = company.start_date.year
            if company.display_year:
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, i
                    year_list.append(list_format)
        else:
            if company.display_year:
                start_year = datetime.today().year
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, i
                    year_list.append(list_format)
            else:
                list_format = '%s' % datetime.today().year, datetime.today().year
                year_list.append(list_format)
        return year_list

    year = fields.Selection(_get_year, string="Year", default=str(datetime.today().year), required=True)

    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month', required=True)

    journal_type = fields.Selection([
        ('accounts', 'Main Accounts'),
        ('pf', 'PF Accounts')
    ], string='Journal Type', required=True, default='pf')

    journal_id = fields.Many2one('account.journal', string='Journal', required=True,
                                 domain="[('is_pf_display','=',True)]")

    debit_acc_id = fields.Many2one('account.account', 'Expense Account (DR)', required=True, help="PF expense account",
                                   domain="[('fs_dept', '=', 'pf')]")
    credit_acc_id = fields.Many2one('account.account', 'Contribution Account (CR)', required=True,
                                    help="Payable account", domain="[('fs_dept', '=', 'pf')]")
    journal_date = fields.Date('Journal Date', required=True)

    @api.onchange('year', 'month')
    def _onchange_year_month(self):
        if self.year and self.month:
            date1 = str(self.year) + '-' + str(self.month) + '-01'
            date2 = datetime.strptime(str(date1), '%Y-%m-%d') + relativedelta(months=1) - timedelta(days=1)
            self.journal_date = date2.strftime('%Y-%m-%d')

    @api.onchange('journal_type')
    def _onchange_journal_type(self):
        if self.journal_type == 'accounts':
            return {'domain': {'debit_acc_id': [('fs_dept', '=', 'accounts')],
                               'credit_acc_id': [('fs_dept', '=', 'accounts')]}}
        else:
            return {'domain': {'debit_acc_id': [('fs_dept', '=', 'pf')], 'credit_acc_id': [('fs_dept', '=', 'pf')]}}

    def action_pf_done(self):
        journal_id = self.journal_id.id
        company_id = self.env.user.company_id.id
        year = self.year
        month = dict(self._fields['month'].selection).get(self.month)
        year_month = str(year) + '-' + month

        pf_rows = self.env['hr.employee.pf'].sudo().search(
            [('year', '=', self.year), ('month', '=', self.month), ('state', '=', 'draft')])
        if pf_rows:
            vals = {
                'date': self.journal_date,
                'journal_id': journal_id,
                'company_id': company_id,
                'partner_id': False,
                'location_id': False,
                'fs_dept': self.journal_type,
                'ref': 'PF Contribution: ' + str(year_month)
            }
            acc_move_id = self.env['account.move'].create(vals)
            lst = []
            debit_acc_id = self.debit_acc_id.id or False
            credit_acc_id = self.credit_acc_id.id or False
            total_amt = 0
            for rec in pf_rows:
                if not rec.employee_id.address_home_id:
                    raise UserError("Required Mapped Employee for '%s'!!" % (rec.employee_id.name))
                else:
                    partner_id = rec.employee_id.address_home_id.id

                ref = rec.employee_id.name
                amount = rec.total_pf_amount
                total_amt += amount
                #  debit journal entry
                lst.append((0, 0, {
                    'account_id': debit_acc_id,
                    'partner_id': partner_id,
                    'name': ref,
                    'debit': amount or 0.0,
                }))

                #  Credit journal entry
                lst.append((0, 0, {
                    'account_id': credit_acc_id,
                    'partner_id': False,
                    'name': ref,
                    'credit': amount or 0.0,
                }))

                rec.state = 'done'

        acc_move_id.line_ids = lst
        acc_move_id.action_post()
