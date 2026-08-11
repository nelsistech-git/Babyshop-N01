from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import UserError
import pandas as pd
import xlsxwriter


import base64
from io import BytesIO


class PFInterestDisburse(models.Model):
    _name = "pf.interest.disburse"
    _description = "PF Interest Disburse"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def get_years(self):
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

    interest_disburse_type = [
        ('weighted_avg', 'Weighted Average'),
        ('opening_closing_balance', 'Opening Closing Balance'),
        ('normal_avg', 'Normal Average')
    ]
    STATE = [
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('disbursed', 'Disbursed')
    ]
    SOURCE_TYPE = [
        ('interest', 'Profit'),
        ('forfeiture', 'Forfeiture')
    ]

    file_data = fields.Binary(' Report')
    fiscalyear_id = fields.Many2one('account.fiscal.year', required=True, string='Fiscal Year')
    state = fields.Selection(selection=STATE, default='draft', tracking=True)
    name = fields.Char(string='Name', default='New', readonly=True, store=True)
    date_from = fields.Date(string="From", required=True, tracking=True)
    date_to = fields.Date(string="To", required=True, tracking=True)
    year = fields.Selection(get_years, default=str(datetime.today().year), string='Year', required=True)
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
    month_count = fields.Integer(string='Number of Month', default=0)
    notes = fields.Text(string='Notes')
    interest_type = fields.Selection(selection=interest_disburse_type, string='Profit Type', readonly=True)
    pf_board_id = fields.Many2one(comodel_name="pf.provident.board", string="Board", index=True, readonly=True,
                                  tracking=True)  # required=True,
    interest_disburse_line_monthly = fields.One2many(comodel_name='pf.interest.disburse.line.monthly',
                                                     inverse_name='pf_interest_id', string='Monthly Contribution Lines',
                                                     copy=False, auto_join=True, readonly=False)
    interest_disburse_line_yearly = fields.One2many(comodel_name='pf.interest.disburse.line.yearly',
                                                    inverse_name='pf_interest_id', string='Yearly Contribution Lines',
                                                    copy=False, auto_join=True, readonly=False)
    interest_disburse_line = fields.One2many(comodel_name='pf.interest.disburse.line', inverse_name='pf_interest_id',
                                             string='Disburse Lines', copy=False, auto_join=True, readonly=False)
    date_disburse = fields.Date(string='Disburse Date', readonly=True, tracking=True)
    amount_interest = fields.Float(string="Profit Amount", required=True, readonly=True,
                                   tracking=True)

    pf_contribution = fields.Float(string='PF Contribution (Average)', default=0.0,
                                   compute="_compute_total_contribution", store=True)
    cpf_contribution = fields.Float(string='CPF Contribution (Average)', default=0.0,
                                    compute="_compute_total_contribution", store=True)
    total_contribution = fields.Float(string='Total Contribution (Average)', default=0.0,
                                      compute="_compute_total_contribution", store=True)

    pf_interest = fields.Float(string='PF Profit', default=0.0, compute="_compute_total_profit", store=True)
    cpf_interest = fields.Float(string='CPF Profit', default=0.0, compute="_compute_total_profit", store=True)
    total_interest = fields.Float(string='Total Profit', default=0.0, compute="_compute_total_profit", store=True)
    diff_interest = fields.Float(string='Profit Difference', default=0.0, compute="_compute_profit_diff")
    is_profit_distribution = fields.Boolean(string='Is Profit Distribution?', default=False)

    #  accounts
    journal_id_disbursement = fields.Many2one('account.journal', string='Disburse Journal')

    payable_acc_id = fields.Many2one('account.account', 'Payable Account (DR)')
    expense_acc_id = fields.Many2one('account.account', 'Expense Account (CR)')
    disburse_move_id = fields.Many2one('account.move', 'Disburse Journal Entries (Payable)')

    @api.depends('interest_disburse_line_yearly')
    def _compute_total_contribution(self):
        for rec in self:
            rec.pf_contribution = sum(rec.interest_disburse_line_yearly.mapped('balance_net_pf_amt'))
            rec.cpf_contribution = sum(rec.interest_disburse_line_yearly.mapped('balance_net_cpf_amt'))
            rec.total_contribution = rec.pf_contribution + rec.cpf_contribution

            rec.pf_interest = sum(rec.interest_disburse_line_monthly.mapped('interest_pf'))
            rec.cpf_interest = sum(rec.interest_disburse_line_monthly.mapped('interest_cpf'))
            rec.total_interest = rec.pf_interest + rec.cpf_interest

    @api.depends('interest_disburse_line_yearly.interest_pf', 'interest_disburse_line_yearly.interest_cpf')
    def _compute_total_profit(self):
        for rec in self:
            rec.pf_interest = sum(rec.interest_disburse_line_yearly.mapped('interest_pf'))
            rec.cpf_interest = sum(rec.interest_disburse_line_yearly.mapped('interest_cpf'))
            rec.total_interest = rec.pf_interest + rec.cpf_interest

    @api.depends('amount_interest', 'total_interest')
    def _compute_profit_diff(self):
        for rec in self:
            rec.diff_interest = rec.amount_interest - rec.total_interest

    @api.onchange('fiscalyear_id')
    def onchange_fiscalyear(self):
        if self.fiscalyear_id:
            self.date_from = self.fiscalyear_id.date_from
            self.date_to = self.fiscalyear_id.date_to
            self.year = self.date_to.strftime("%Y")
            self.month = self.date_to.strftime("%m")
        else:
            self.date_from = None
            self.date_to = None
            self.year = None
            self.month = None

    @api.onchange('date_from', 'date_to')
    def onchange_date_from_to(self):
        if self.date_from and self.date_to:
            month_list = pd.period_range(start=self.date_from, end=self.date_to, freq='M')
            month_list = [month.strftime("%Y-%m") for month in month_list]
            self.month_count = len(month_list)
        else:
            self.month_count = 0

    @api.onchange('month', 'year')  # , 'pf_board_id'
    def _set_name(self):
        if self.month and self.year:  # and self.pf_board_id
            month = dict(self._fields['month'].selection).get(self.month)

            name = _('PF Profit Disbursement of %s-%s') % (month, self.year)  # , self.pf_board_id.name
            self.name = name

    def disburse_interest(self):
        year = self.year
        month = self.month

        if self.journal_id_disbursement and self.journal_id_disbursement.is_pf_display:
            fs_dept = 'pf'
        else:
            fs_dept = 'accounts'

        vals = {
            'date': fields.Date.today(),
            'journal_id': self.journal_id_disbursement and self.journal_id_disbursement.id,
            'company_id': self.env.user.company_id.id,
            'partner_id': False,
            'location_id': False,
            'ref': 'Ref: ' + str(self.name),
            'fs_dept': fs_dept
        }
        acc_move_id = self.env['account.move'].create(vals)

        lst = []
        debit_account_id = self.payable_acc_id.id or False
        fund_credit_acc_id = self.expense_acc_id.id or False
        ref = str(self.name)

        pf_obj = self.env['hr.employee.pf'].sudo()
        for line in self.interest_disburse_line_yearly:
            interest_pf = line.interest_pf
            interest_cpf = line.interest_cpf

            pf_obj.create([{
                'employee_id': line.employee_id.id,
                'year': str(year),
                'month': str(month),
                'pf_amount': interest_pf,
                'cpf_amount': interest_cpf,
                'contribution_type': 'profit',
                'state': 'done'
            }])
            profit_amt = round(line.interest_total, 2)
            partner_id = line.employee_id.address_home_id.id or False
            #  debit journal entry
            lst.append((0, 0, {
                'account_id': debit_account_id,
                'partner_id': partner_id,
                'name': ref,
                'debit': profit_amt or 0.0,
            }))

            #  Credit journal entry
            lst.append((0, 0, {
                'account_id': fund_credit_acc_id,
                'partner_id': False,
                'name': ref,
                'credit': profit_amt or 0.0,
            }))

        acc_move_id.line_ids = lst
        acc_move_id.action_post()

        self.write(
            {'state': 'disbursed', 'date_disburse': fields.Date.today(), 'disburse_move_id': acc_move_id.id or False})

    def confirm(self):
        config_obj = self.env['pf.profit.disb.configuration'].sudo().search([], limit=1)
        for rec in self:
            if config_obj:
                rec.journal_id_disbursement = config_obj[0].journal_id_disbursement.id if config_obj[
                    0].journal_id_disbursement else None
                rec.payable_acc_id = config_obj[0].payable_acc_id.id if config_obj[0].payable_acc_id else None
                rec.expense_acc_id = config_obj[0].expense_acc_id.id if config_obj[0].expense_acc_id else None

        if self.diff_interest != 0:
            self.set_profit_distribution()

        self.write({'state': 'confirm'})

    def action_draft(self):
        self.state = 'draft'

    def unlink(self):
        for record in self:
            if record.state != "draft":
                raise UserError("You can delete only draft data.")
            super(PFInterestDisburse, record).unlink()

    def get_contribution(self):
        self.get_contribution_monthly()
        self.env.cr.commit()
        self.get_contribution_yearly()
        return True

    def get_contribution_monthly(self):
        self.is_profit_distribution = False

        from_year_month = self.date_from.strftime('%Y-%m')
        to_year_month = self.date_to.strftime('%Y-%m')
        monthly_line_obj = self.env['pf.interest.disburse.line.monthly']
        yearly_line_obj = self.env['pf.interest.disburse.line.yearly']

        # delete existing for new create
        monthly_line_obj.sudo().search([('pf_interest_id', '=', self.id)]).unlink()
        # delete existing for new create
        yearly_line_obj.sudo().search([('pf_interest_id', '=', self.id)]).unlink()

        data_sql = """
                SELECT tbl1.employee_id, tbl1.year, tbl1.month,
                COALESCE(tbl2.op_pf_amt, 0) AS op_pf_amt, tbl1.pf_amt AS pf_amt,
                COALESCE(tbl2.op_cpf_amt, 0) AS op_cpf_amt, tbl1.cpf_amt AS cpf_amt,
                COALESCE(tbl3.op_loan_pf, 0) AS op_loan_pf, tbl1.loan_pf AS loan_pf,
                COALESCE(tbl3.op_loan_cpf, 0) AS op_loan_cpf, tbl1.loan_cpf AS loan_cpf
                FROM(
                    SELECT tbl1_dpf.employee_id as employee_id, tbl1_dpf.year as year, tbl1_dpf.month as month, tbl1_dpf.pf_amt as pf_amt, tbl1_dpf.cpf_amt as cpf_amt, 
                    COALESCE(tbl1_drl.loan_pf, 0) as loan_pf, COALESCE(tbl1_drl.loan_cpf, 0) as loan_cpf 
                    FROM (
                    SELECT employee_id, year, month, SUM(pf_amount) as pf_amt, SUM(cpf_amount) as cpf_amt from hr_employee_pf
                    WHERE CONCAT(year,'-',month) BETWEEN '{0}' and '{1}' AND state='done'
                    GROUP BY employee_id, year, month
                    ORDER BY employee_id, year, month
                    ) tbl1_dpf
                    LEFT JOIN (	
                        SELECT employee_id, year, month,
                            loan_pf, 
                            loan_cpf
                        FROM (
                            SELECT employee_id, year, month,
                                SUM(loan_pf_due) as loan_pf, 
                                SUM(loan_cpf_due) as loan_cpf
                            FROM (
                                    SELECT employee_id, loan_id, year, month,
                                        ROUND((sum(loan_pf) - sum(paid_pf))::NUMERIC,2) as loan_pf_due, 
                                        ROUND((sum(loan_cpf) - sum(paid_cpf))::NUMERIC,2) as loan_cpf_due
                    
                                        FROM (
                                        Select eln.employee_id as employee_id, eln.id as loan_id, 
                                        EXTRACT(YEAR FROM approve_date)::text as year, 
                                        LPAD(EXTRACT(MONTH FROM approve_date)::text,2,'0') as month,
                                        loan_amount_pf as loan_pf,
                                        loan_amount_cpf as loan_cpf,
                                        0 as paid_pf, 
                                        0 as paid_cpf
                                        from employee_loan eln
                                        JOIN employee_loan_type elnt ON elnt.id = eln.loan_type_id
                                        where eln.state in ('done', 'close') and elnt.type='pf_loan'
                    
                                        UNION ALL
                    
                                        SELECT employee_id, loan_id, year, month, 
                                        0 as loan_pf, 0 as loan_cpf, paid_pf, (paid_amt-paid_pf) as paid_cpf
                                        FROM(
                                            SELECT employee_id, loan_id, year, month, loan_amt, paid_amt,loan_amt_pf, (loan_amt_pf * paid_amt / loan_amt) as paid_pf
                                            FROM (
                                                SELECT employee_id, loan_id, year, month, 
                                                    max(loan_amt) as loan_amt,
                                                    max(loan_amt_pf) as loan_amt_pf, 
                                                    SUM(installment_amt) as paid_amt
                                                    FROM (
                                                    select eln.employee_id as employee_id, eln.id as loan_id,
                                                    EXTRACT(YEAR FROM paid_date)::text as year, 
                                                    LPAD(EXTRACT(MONTH FROM paid_date)::text,2,'0') as month,
                                                    eln.loan_amount as loan_amt, 
                                                    eln.loan_amount_pf as loan_amt_pf,
                                                    installment_amt
                                                    from installment_line insln
                                                    JOIN employee_loan eln ON eln.id = insln.loan_id
                                                    JOIN employee_loan_type elnt ON elnt.id = eln.loan_type_id
                                                    where eln.state in ('done', 'close') and elnt.type='pf_loan'
                                                    and insln.is_paid = True
                                                ) tbl_line1 GROUP BY employee_id, loan_id, year, month
                                            ) tbl_line2
                                        ) tbl_line3
                                    ) tbl2_dl GROUP BY employee_id, loan_id, year, month ORDER BY employee_id, loan_id, year, month
                            ) tbl3_dl GROUP BY employee_id, year, month ORDER BY employee_id, year, month
                        ) tbl4_dl 
                        WHERE CONCAT(year,'-',month) BETWEEN '{0}' and '{1}'
                        ) tbl1_drl ON (tbl1_dpf.employee_id=tbl1_drl.employee_id and tbl1_dpf.year=tbl1_drl.year and tbl1_dpf.month=tbl1_drl.month)
                ) tbl1
                LEFT JOIN (
                    SELECT employee_id, SUM(pf_amount) as op_pf_amt, SUM(cpf_amount) as op_cpf_amt from hr_employee_pf
                    WHERE CONCAT(year,'-',month) < '{0}' AND state='done'
                    GROUP BY employee_id
                    ORDER BY employee_id
                ) tbl2 ON tbl1.employee_id=tbl2.employee_id
                LEFT JOIN (
                    SELECT employee_id,
                        SUM(loan_pf) as op_loan_pf, 
                        SUM(loan_cpf) as op_loan_cpf
                    FROM (
                    
                        SELECT employee_id, year, month,
                            SUM(loan_pf_due) as loan_pf, 
                            SUM(loan_cpf_due) as loan_cpf
                        FROM (
                                SELECT employee_id, loan_id, year, month,
                                    ROUND((sum(loan_pf) - sum(paid_pf))::NUMERIC,2) as loan_pf_due, 
                                    ROUND((sum(loan_cpf) - sum(paid_cpf))::NUMERIC,2) as loan_cpf_due
                    
                                    FROM (
                                    Select eln.employee_id as employee_id, eln.id as loan_id, 
                                    EXTRACT(YEAR FROM approve_date)::text as year, 
                                    LPAD(EXTRACT(MONTH FROM approve_date)::text,2,'0') as month,
                                    loan_amount_pf as loan_pf,
                                    loan_amount_cpf as loan_cpf,
                                    0 as paid_pf, 
                                    0 as paid_cpf
                                    from employee_loan eln
                                    JOIN employee_loan_type elnt ON elnt.id = eln.loan_type_id
                                    where eln.state in ('done', 'close') and elnt.type='pf_loan'
                    
                                    UNION ALL
                    
                                    SELECT employee_id, loan_id, year, month, 
                                    0 as loan_pf, 0 as loan_cpf, paid_pf, (paid_amt-paid_pf) as paid_cpf
                                    FROM(
                                        SELECT employee_id, loan_id, year, month, loan_amt, paid_amt,loan_amt_pf, (loan_amt_pf * paid_amt / loan_amt) as paid_pf
                                        FROM (
                                            SELECT employee_id, loan_id, year, month, 
                                                max(loan_amt) as loan_amt,
                                                max(loan_amt_pf) as loan_amt_pf, 
                                                SUM(installment_amt) as paid_amt
                                                FROM (
                                                select eln.employee_id as employee_id, eln.id as loan_id,
                                                EXTRACT(YEAR FROM paid_date)::text as year, 
                                                LPAD(EXTRACT(MONTH FROM paid_date)::text,2,'0') as month,
                                                eln.loan_amount as loan_amt, 
                                                eln.loan_amount_pf as loan_amt_pf,
                                                installment_amt
                                                from installment_line insln
                                                JOIN employee_loan eln ON eln.id = insln.loan_id
                                                JOIN employee_loan_type elnt ON elnt.id = eln.loan_type_id
                                                where eln.state in ('done', 'close') and elnt.type='pf_loan'
                                                and insln.is_paid = True
                                            ) tbl_line1 GROUP BY employee_id, loan_id, year, month
                                        ) tbl_line2
                                    ) tbl_line3
                                ) tbl2_opl GROUP BY employee_id, loan_id, year, month ORDER BY employee_id, loan_id, year, month
                        ) tbl3_opl GROUP BY employee_id, year, month ORDER BY employee_id, year, month
                    ) tbl4_opl 
                    WHERE CONCAT(year,'-',month) < '{0}'
                    GROUP BY employee_id
                ) tbl3 ON tbl1.employee_id=tbl3.employee_id
                ORDER BY tbl1.employee_id, tbl1.year, tbl1.month;
            """.format(from_year_month, to_year_month)

        self.env.cr.execute(data_sql)
        query_res = self.env.cr.dictfetchall()

        prev_emp = ''
        for res in query_res:
            employee_id = res['employee_id']

            if employee_id != prev_emp:
                prev_emp = employee_id
                op_pf_amt = res['op_pf_amt']
                op_cpf_amt = res['op_cpf_amt']
                op_loan_pf = res['op_loan_pf']
                op_loan_cpf = res['op_loan_cpf']
                dur_pf_amt = 0
                dur_cpf_amt = 0
                dur_loan_pf = 0
                dur_loan_cpf = 0
            else:
                op_pf_amt += dur_pf_amt
                op_cpf_amt += dur_cpf_amt
                op_loan_pf += dur_loan_pf
                op_loan_cpf += dur_loan_cpf

            dur_pf_amt = res['pf_amt']
            dur_cpf_amt = res['cpf_amt']
            dur_loan_pf = res['loan_pf']
            dur_loan_cpf = res['loan_cpf']

            create_vals = {
                'pf_interest_id': self.id,
                'employee_id': employee_id,
                'year': res['year'],
                'month': res['month'],

                'op_pf_amt': op_pf_amt,
                'pf_amt': dur_pf_amt,
                'op_cpf_amt': op_cpf_amt,
                'cpf_amt': dur_cpf_amt,
                'op_loan_amt_pf': op_loan_pf,
                'loan_amt_pf': dur_loan_pf,
                'op_loan_amt_cpf': op_loan_cpf,
                'loan_amt_cpf': dur_loan_cpf
            }
            monthly_line_obj.sudo().create(create_vals)

        return True

    def get_contribution_yearly(self):
        self.is_profit_distribution = False

        # --------------------
        yearly_line_obj = self.env['pf.interest.disburse.line.yearly']
        month_count = self.month_count

        # delete existing for new create
        yearly_line_obj.sudo().search([('pf_interest_id', '=', self.id)]).unlink()

        #  Yearly contribution
        data_sql2 = """
                SELECT employee_id,
                    SUM(balance_net_pf_amt)/{0} as avg_pf,
                    SUM(balance_net_cpf_amt)/{0} as avg_cpf
                FROM pf_interest_disburse_line_monthly
                WHERE pf_interest_id = {1}
                GROUP BY employee_id
                ORDER BY employee_id
            """.format(month_count, self.id)

        self.env.cr.execute(data_sql2)
        query_res2 = self.env.cr.dictfetchall()

        for res in query_res2:
            employee_id = res['employee_id']

            create_vals2 = {
                'pf_interest_id': self.id,
                'employee_id': employee_id,
                'balance_net_pf_amt': round(res['avg_pf'], 2),
                'balance_net_cpf_amt': round(res['avg_cpf'], 2)
            }
            yearly_line_obj.sudo().create(create_vals2)

        return True

    def set_profit_distribution(self):
        self.is_profit_distribution = True
        for rec in self:
            amount_interest = rec.amount_interest
            total_contribution = rec.total_contribution

            unit_interest = 0
            if total_contribution > 0:
                unit_interest = amount_interest / total_contribution
            else:
                raise UserError("Employee contribution as done state, not available!")

            for line in rec.interest_disburse_line_yearly:
                net_pf_amt = line.balance_net_pf_amt
                net_cpf_amt = line.balance_net_cpf_amt

                line.interest_pf = round(unit_interest * net_pf_amt, 2)
                line.interest_cpf = round(unit_interest * net_cpf_amt, 2)

        return True

    def action_print_excel(self):

        file_name = "Profit Disburse Report.xlsx"
        file_pointer = BytesIO()

        workbook = xlsxwriter.Workbook(file_pointer)

        # main header formatting
        format0 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
        format0.set_align('center')
        format0.set_border()

        # column header formatting
        format1 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format1.set_align('left')
        format1.set_border()
        format2 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format2.set_align('center')
        format2.set_border()
        format3 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format3.set_align('right')
        format3.set_border()

        # body formatting
        format4 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format4.set_align('left')
        format4.set_border()
        format5 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format5.set_align('center')
        format5.set_border()
        format10 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format10.set_align('left')
        format10.set_border()
        format9 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format9.set_align('right')
        format9.set_border()
        format8 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
        format8.set_align('left')
        format8.set_border()
        format6 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format6.set_align('right')
        format6.set_border()
        format7 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format7.set_border()
        format7.set_align('center')

        sheet = workbook.add_worksheet('Profit Disburse Report')

        sheet.merge_range(0, 0, 0, 7, "Profit Disburse Report", format0)

        sheet.write(2, 0, "Fiscal Year", format1)
        sheet.write(2, 1, self.fiscalyear_id.name, format4)

        sheet.write(2, 3, "Board", format1)
        sheet.write(2, 4, self.pf_board_id.name if self.pf_board_id.name else '', format4)

        sheet.write(2, 6, "Month-Year of Profit", format1)
        selection_name = dict(self._fields['month'].selection).get(self.month)
        sheet.write(2, 7, selection_name, format4)

        sheet.write(3, 0, "Date From", format1)
        sheet.write(3, 1, datetime.strptime(self.date_from.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S').strftime(
            '%d-%b-%y'), format4)

        sheet.write(3, 3, "Date To", format1)
        sheet.write(3, 4, datetime.strptime(self.date_to.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S').strftime(
            '%d-%b-%y'), format4)

        sheet.write(3, 6, "Number of Month", format1)
        sheet.write(3, 7, self.month_count, format4)

        sheet.write(4, 0, "Date Disburse", format1)
        sheet.write(4, 1, self.date_disburse if self.date_disburse else '', format4)

        sheet.write(4, 3, "Profit Amount", format1)
        sheet.write(4, 4, self.amount_interest, format4)

        sheet.write(4, 6, "Notes", format1)
        sheet.write(4, 7, self.notes if self.notes else '', format4)

        h_col = 0
        h_row = 6
        sheet.write(h_row, h_col, 'Sl No.', format2)
        h_col += 1
        sheet.write(h_row, h_col, 'Employee', format1)
        h_col += 1
        sheet.write(h_row, h_col, 'PF Contribution', format3)
        h_col += 1
        sheet.write(h_row, h_col, 'CPF Contribution', format3)
        h_col += 1
        sheet.write(h_row, h_col, 'Total Contribution', format3)
        h_col += 1

        sheet.write(h_row, h_col, 'Profit PF', format3)
        h_col += 1
        sheet.write(h_row, h_col, 'Profit CPF', format3)
        h_col += 1
        sheet.write(h_row, h_col, 'Total Profit', format3)
        h_col += 1

        row = 7
        col = 0
        sl_no = 1

        disburse_line_obj = self.env['pf.interest.disburse.line.yearly'].search([('pf_interest_id', '=', self.id)],
                                                                                order='id asc')
        for rec in disburse_line_obj:
            sheet.write(row, col, sl_no, format5)
            col += 1
            sheet.write(row, col, rec.employee_id.name, format4)
            col += 1
            sheet.write(row, col, rec.balance_net_pf_amt, format9)
            col += 1
            sheet.write(row, col, rec.balance_net_cpf_amt, format9)
            col += 1
            sheet.write(row, col, rec.balance_total_contribution, format9)
            col += 1
            sheet.write(row, col, rec.interest_pf, format9)
            col += 1
            sheet.write(row, col, rec.interest_cpf, format9)
            col += 1
            sheet.write(row, col, rec.interest_total, format9)
            col = 0

            row = row + 1
            sl_no = sl_no + 1

        sheet.write(row, 0, 'Total', format6)
        sheet.write(row, 1, '', format6)
        sheet.write(row, 2, self.pf_contribution, format6)
        sheet.write(row, 3, self.cpf_contribution, format6)
        sheet.write(row, 4, self.total_contribution, format6)
        sheet.write(row, 5, self.pf_interest, format6)
        sheet.write(row, 6, self.cpf_interest, format6)
        sheet.write(row, 7, self.total_interest, format6)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'FDR Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=pf.interest.disburse&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }


class PFInterestDisburseLineMonthly(models.Model):
    _name = "pf.interest.disburse.line.monthly"
    _description = "PF Interest Disburse Line Monthly"

    pf_interest_id = fields.Many2one(comodel_name='pf.interest.disburse', string='Monthly PF Profit Disburse',
                                     ondelete='cascade')

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', required=True)
    pf_profile_id = fields.Many2one(comodel_name='pf.profile', string='PF Profile')
    year = fields.Char(string='Year', required=True)
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

    op_pf_amt = fields.Float(string='Op.PF', default=0.0, help="Opening PF")
    pf_amt = fields.Float(string='Dur.PF', default=0.0, help="During PF")
    op_cpf_amt = fields.Float(string='Op.CPF', default=0.0, help="Opening CPF")
    cpf_amt = fields.Float(string='Dur.CPF', default=0.0, help="During CPF")
    op_loan_amt_pf = fields.Float(string='Op.Loan (PF)', default=0.0, help="Opening Loan (PF)")
    loan_amt_pf = fields.Float(string='Dur.Loan (PF)', default=0.0, help="During Loan (PF)")
    op_loan_amt_cpf = fields.Float(string='Op.Loan (CPF)', default=0.0, help="Opening Loan (CPF)")
    loan_amt_cpf = fields.Float(string='Dur.Loan (CPF)', default=0.0, help="During Loan (CPF)")

    #  Net contribution
    opening_net_pf_amt = fields.Float(string='Net Op.PF', default=0.0, help="Net Opening PF")
    net_pf_amt = fields.Float(string='Net Dur.PF', default=0.0, help="Net During PF")

    opening_net_cpf_amt = fields.Float(string='Net Op.CPF', default=0.0, help="Net Opening CPF")
    net_cpf_amt = fields.Float(string='Net Dur.CPF', default=0.0, help="Net During CPF")

    opening_total_contribution = fields.Float(string='Op.Contribution', default=0.0, help="Opening Contribution")
    total_contribution = fields.Float(string='Dur.Contribution', default=0.0, help="During Contribution")

    balance_net_pf_amt = fields.Float(string='Balance PF ', default=0.0, compute="get_net_contribution",
                                      store=True)
    balance_net_cpf_amt = fields.Float(string='Balance CPF', default=0.0, compute="get_net_contribution",
                                       store=True)
    balance_total_contribution = fields.Float(string='Balance Contribution', default=0.0,
                                              compute="get_net_contribution",
                                              store=True)

    interest_pf = fields.Float(string='Profit PF', default=0.0)
    interest_cpf = fields.Float(string='Profit CPF', default=0.0)
    interest_total = fields.Float(string='Total Profit', default=0.0, compute="get_total_interest", store=True)

    @api.depends('op_pf_amt', 'pf_amt', 'op_cpf_amt', 'cpf_amt', 'op_loan_amt_pf', 'loan_amt_pf', 'op_loan_amt_cpf',
                 'loan_amt_cpf')
    def get_net_contribution(self):
        for rec in self:
            rec.opening_net_pf_amt = round(rec.op_pf_amt - rec.op_loan_amt_pf, 2)
            rec.opening_net_cpf_amt = round(rec.op_cpf_amt - rec.op_loan_amt_cpf, 2)
            rec.opening_total_contribution = round(rec.opening_net_pf_amt + rec.opening_net_cpf_amt, 2)

            rec.net_pf_amt = round(rec.pf_amt - rec.loan_amt_pf, 2)
            rec.net_cpf_amt = round(rec.cpf_amt - rec.loan_amt_cpf, 2)
            rec.total_contribution = round(rec.net_pf_amt + rec.net_cpf_amt, 2)

            rec.balance_net_pf_amt = round(rec.opening_net_pf_amt + rec.net_pf_amt, 2)
            rec.balance_net_cpf_amt = round(rec.opening_net_cpf_amt + rec.net_cpf_amt, 2)
            rec.balance_total_contribution = round(rec.balance_net_pf_amt + rec.balance_net_cpf_amt, 2)

    @api.depends('interest_pf', 'interest_cpf')
    def get_total_interest(self):
        for rec in self:
            rec.interest_total = round(rec.interest_pf + rec.interest_cpf, 2)


class PFInterestDisburseLineYearly(models.Model):
    _name = "pf.interest.disburse.line.yearly"
    _description = "PF Interest Disburse Line Yearly"

    pf_interest_id = fields.Many2one(comodel_name='pf.interest.disburse', string='Yearly PF Profit Disburse',
                                     ondelete='cascade')

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', required=True)
    pf_profile_id = fields.Many2one(comodel_name='pf.profile', string='PF Profile')

    #  Net contribution
    balance_net_pf_amt = fields.Float(string='PF Contribution', default=0.0)
    balance_net_cpf_amt = fields.Float(string='CPF Contribution', default=0.0)
    balance_total_contribution = fields.Float(string='Total Contribution', default=0.0,
                                              compute="get_net_contribution_yearly",
                                              store=True)

    interest_pf = fields.Float(string='Profit PF', default=0.0)
    interest_cpf = fields.Float(string='Profit CPF', default=0.0)
    interest_total = fields.Float(string='Total Profit', default=0.0, compute="get_total_interest_yearly", store=True)

    @api.depends('balance_net_pf_amt', 'balance_net_cpf_amt')
    def get_net_contribution_yearly(self):
        for rec in self:
            rec.balance_total_contribution = round(rec.balance_net_pf_amt + rec.balance_net_cpf_amt, 2)

    @api.depends('interest_pf', 'interest_cpf')
    def get_total_interest_yearly(self):
        for rec in self:
            rec.interest_total = round(rec.interest_pf + rec.interest_cpf, 2)


class PFInterestDisburseLine(models.Model):
    _name = "pf.interest.disburse.line"
    _description = "PF Interest Disburse Line"

    pf_interest_id = fields.Many2one(comodel_name='pf.interest.disburse', string='PF Profit Disburse',
                                     ondelete='cascade')

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', required=True)
    pf_profile_id = fields.Many2one(comodel_name='pf.profile', string='PF Profile', required=True)
    balance_opening = fields.Float(string='Opening Balance', required=True)
    interest_emp = fields.Float(string='Employee Profit')
    interest_company = fields.Float(string='Company Profit')
