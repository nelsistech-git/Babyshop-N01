from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from calendar import monthrange
import datetime
from datetime import date

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.helper import xlsxwriter

import base64
from io import BytesIO


class BudgetParticularReportWizard(models.TransientModel):
    _name = "budget.particular.report.wizard"
    _description = "Budget Particular Report Wizard"

    file_data = fields.Binary('Budget Particular Report')
    fiscal_year = fields.Many2one('account.fiscal.year', string='Fiscal Year')
    report_type = fields.Selection([
        ('income', 'Income Budget'),
        ('expense', 'Expense Budget')], string='Report Type')
    budget_head_id = fields.Many2one('budget.particular.settings', string='Budget Head', domain=[('particular_type', 'in', ('parent', 'sub_parent'))])
    type = fields.Selection([
        ('detail', 'Details'),
        ('summary', 'Summary')], string='Type', default='summary')

    @api.constrains('fiscal_year')
    def _fiscal_year_constrains(self):
        for rec in self:
            if rec.fiscal_year.date_to <= rec.fiscal_year.date_from:
                raise ValidationError(_('Fiscal year start date cannot be greater than or equal to the end date.'))

    def budget_particular_report_pdf(self):
        fiscal_year = self.fiscal_year
        report_type = self.report_type
        type = self.type
        budget_head_id = self.budget_head_id

        # get data from sql
        data = self.budget_particular_report_sql(fiscal_year, report_type, type, budget_head_id)

        if type == 'summary':
            return self.env.ref('custom_account_day_book.budget_particular_summary_report_tmpl').with_context(landscape=False).report_action(self, data=data)
        else:
            return self.env.ref('custom_account_day_book.budget_particular_details_report_tmpl').with_context(
                landscape=False).report_action(self, data=data)

    def budget_particular_report_sql(self, fiscal_year, report_type, type, budget_head_id):
        start_date = fiscal_year.date_from
        end_date = fiscal_year.date_to

        date_today = date.today()

        ndays = monthrange(date_today.year, date_today.month)[1]
        this_month_start = date(date_today.year, date_today.month, 1)
        this_month_end = date(date_today.year, date_today.month, ndays)

        report_type_filter = ""
        budget_head_filter = ""

        if fiscal_year:
            fiscal_year_filter = "AND bph.fiscal_year = %s" % fiscal_year.id

        if report_type:
            report_type_filter = "AND bps.report_type = '%s'" % report_type

        budget_head_obj = self.env['budget.particular.settings'].search([('id', 'child_of', budget_head_id.ids)])

        if len(budget_head_obj) > 1:
            budget_head_filter = "AND bps.id IN {0}".format(tuple(budget_head_obj.ids))
        elif len(budget_head_obj) == 1:
            budget_head_filter = "AND bps.id = {0}".format(budget_head_obj[0])
        else:
            pass

        data_list = []
        if type == 'summary':
            data_sql = """
                        SELECT ftbl.budget_head, COALESCE(SUM(ftbl.current_amt), 0) AS current_amt, COALESCE(SUM(ftbl.upto_amt), 0) AS upto_amt, COALESCE(SUM(ftbl.budget_amt), 0) AS budget_amt
                        FROM (
                            SELECT bps.name AS budget_head, SUM(CASE WHEN DATE(amvl.date) BETWEEN '{1}' AND '{2}' THEN COALESCE(amvl.debit - amvl.credit, 0) ELSE 0 END) AS current_amt,
                            SUM(CASE WHEN DATE(amvl.date) BETWEEN '{3}' AND '{4}' THEN COALESCE(amvl.debit - amvl.credit, 0) ELSE 0 END) AS upto_amt,
                            COALESCE(mtbl.budget_amt, 0) AS budget_amt
                            FROM (
                                SELECT bpl.sub_parent_id, bpl.budget_parti_child_id, bpl.account_id, COALESCE(SUM(bpl.budget_amount), 0) AS budget_amt
                                FROM budget_particular_head bph
                                JOIN budget_particular_line bpl ON bpl.head_id = bph.id
                                WHERE bph.state = 'approve' {6}
                                GROUP BY bpl.sub_parent_id, bpl.budget_parti_child_id, bpl.account_id
                            ) mtbl
                            LEFT JOIN budget_particular_settings bps ON bps.id = mtbl.sub_parent_id
                            LEFT JOIN account_move_line amvl ON amvl.account_id = mtbl.account_id
                            WHERE amvl.parent_state = 'posted' {0} {5}
                            GROUP BY bps.name, mtbl.budget_amt
                        ) ftbl
                        GROUP BY ftbl.budget_head
                        ORDER BY ftbl.budget_head
                        """.format(report_type_filter, this_month_start, this_month_end, start_date, date_today, budget_head_filter, fiscal_year_filter)
            self.env.cr.execute(data_sql)
            data_list = self.env.cr.dictfetchall()

        if type == 'detail':
            data_sql = """
                        SELECT bps.id AS budget_head_id, bps.name AS budget_head, bpsp.name AS budget_child, SUM(CASE WHEN DATE(amvl.date) BETWEEN '{1}' AND '{2}' THEN COALESCE(amvl.debit - amvl.credit, 0) ELSE 0 END) AS current_amt,
                            SUM(CASE WHEN DATE(amvl.date) BETWEEN '{3}' AND '{4}' THEN COALESCE(amvl.debit - amvl.credit, 0) ELSE 0 END) AS upto_amt,
                            COALESCE(mtbl.budget_amt, 0) AS budget_amt
                        FROM (
                            SELECT bpl.sub_parent_id, bpl.budget_parti_child_id, bpl.account_id, COALESCE(SUM(bpl.budget_amount), 0) AS budget_amt
                            FROM budget_particular_head bph
                            JOIN budget_particular_line bpl ON bpl.head_id = bph.id
                            WHERE bph.state = 'approve' {6}
                            GROUP BY bpl.sub_parent_id, bpl.budget_parti_child_id, bpl.account_id
                        ) mtbl
                        LEFT JOIN budget_particular_settings bps ON bps.id = mtbl.sub_parent_id
                        LEFT JOIN budget_particular_settings bpsp ON bpsp.id = mtbl.budget_parti_child_id
                        LEFT JOIN account_move_line amvl ON amvl.account_id = mtbl.account_id
                        WHERE amvl.parent_state = 'posted' {0} {5}
                        GROUP BY bps.id, bps.name, bpsp.name, mtbl.budget_amt
                        ORDER BY bps.name, bpsp.name
                        """.format(report_type_filter, this_month_start, this_month_end, start_date, date_today, budget_head_filter, fiscal_year_filter)
            self.env.cr.execute(data_sql)
            data_list = self.env.cr.dictfetchall()

        data = {
            'model': "budget.particular.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'start_date': start_date,
            'end_date': end_date,
            'report_type': dict(self._fields['report_type'].selection).get(self.report_type),
        }
        return data