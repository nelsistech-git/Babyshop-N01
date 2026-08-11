from odoo import api, fields, models


class WPPFStatementWizard(models.TransientModel):
    _name = 'wppf.statement.wizard'
    _description = 'WPPF Statement Wizard'

    fiscalyear_id = fields.Many2one('account.fiscal.year', required=True, string='Fiscal Year')
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To", required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    @api.onchange('fiscalyear_id')
    def onchange_fiscalyear(self):
        if self.fiscalyear_id:
            self.date_from = self.fiscalyear_id.date_from
            self.date_to = self.fiscalyear_id.date_to
        else:
            self.date_from = None
            self.date_to = None

    def action_print_pdf(self):
        employee_id = self.employee_id
        date_from = self.date_from
        date_to = self.date_to

        from_year = str(date_from.year)
        from_month = str(date_from.month).zfill(2)
        to_year = str(date_to.year)
        to_month = str(date_to.month).zfill(2)

        opening_pf = 0
        opening_cpf = 0
        opening_data = self.env['hr.employee.wppf']._get_wppf_emp_balance_opening(self.date_from, self.employee_id)
        if opening_data:
            opening_pf = opening_data['wppf_pf'] + opening_data['profit_pf']
            opening_cpf = opening_data['wppf_cpf'] + opening_data['profit_cpf']


        # -------------------1
        during_pf_list = []
        from_year_month = date_from.strftime("%Y-%m")
        to_year_month = date_to.strftime("%Y-%m")
        data_sql1 = """
                    SELECT employee_id, year, month, pf_amount, cpf_amount
                    from hr_employee_wppf
                    WHERE employee_id={0} AND contribution_type='wppf' AND CONCAT(year,'-',month) BETWEEN '{1}' and '{2}'
                    ORDER BY year, month;
                """.format(employee_id.id, from_year_month, to_year_month)

        self.env.cr.execute(data_sql1)
        query_res1 = self.env.cr.dictfetchall()
        for res1 in query_res1:
            dur_data = {
                'year': res1['year'],
                'month': dict(self.env['hr.employee.wppf']._fields['month'].selection).get(res1['month']),
                'pf_amount': res1['pf_amount'],
                'cpf_amount': res1['cpf_amount']
            }
            during_pf_list.append(dur_data)

        # -------------2
        during_profit_list = []
        data_sql2 = """
                    SELECT employee_id, year, month, pf_amount, cpf_amount
                    from hr_employee_wppf
                    WHERE employee_id={0} AND contribution_type='profit' AND CONCAT(year,'-',month) BETWEEN '{1}' and '{2}'
                    ORDER BY year, month;
                """.format(employee_id.id, from_year_month, to_year_month)

        self.env.cr.execute(data_sql2)
        query_res2 = self.env.cr.dictfetchall()
        for res2 in query_res2:
            dur_data = {
                'year': res2['year'],
                'month': dict(self.env['hr.employee.wppf']._fields['month'].selection).get(res2['month']),
                'pf_amount': res2['pf_amount'],
                'cpf_amount': res2['cpf_amount']
            }
            during_profit_list.append(dur_data)
            # -------------------

        current_loan = 0


        data = {
            'model': "wppf.statement.wizard",
            'form': self.read()[0],
            'from_date': self.date_from,
            'to_date': self.date_to,
            'employee_name': self.employee_id.name,
            'opening_pf': opening_pf,
            'opening_cpf': opening_cpf,
            'during_pf_list': during_pf_list,
            'during_profit_list': during_profit_list,
            'current_loan': current_loan,
        }

        return self.env.ref(
            'wppf.wppf_statement_report_tmpl').with_context(landscape=False).report_action(self, data=data)
