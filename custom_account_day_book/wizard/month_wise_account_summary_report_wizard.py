from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, date
from calendar import monthrange

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.helper import xlsxwriter

import base64
from io import BytesIO


class MonthWiseAccountSummaryReportWizard(models.TransientModel):
    _name = "month.wise.account.summary.report.wizard"
    _description = "Month wise Account Summary Report"

    def _get_year(self):
        """ Get company start year and display_year from res_company """
        year_list = []
        company = self.env.company
        if company.start_date:
            # start_year = int(str(company.start_date).split("-")[0])
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

    file_data = fields.Binary('Month wise Account Summary Report')
    year = fields.Selection(_get_year, string="Year", default=str(datetime.today().year))
    is_multi_currency = fields.Boolean(string='Allow Multi-Currency')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                          domain="['|', ('active', '=', True), ('active', '=', False), ('name', 'in', ('BDT', 'USD'))]",
                                          default=lambda self: self.env['res.currency'].search([('name', '=', 'BDT')]))
    currency = fields.Char('Currency Name', related='currency_id.name')
    other_currency_id = fields.Many2one('res.currency', 'Other Currency',
                                          domain="['|', ('active', '=', True), ('active', '=', False), ('name', '=', 'USD')]",
                                          default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')]))
    other_currency = fields.Char('Currency Name', related='currency_id.name')
    rate = fields.Float(string='Rate', default=1.00, digits=(16, 2))

    @api.onchange('is_multi_currency')
    def _onchange_is_multi_currency(self):
        if self.is_multi_currency:
            return {'domain': {'currency_id': ['|', ('active', '=', True), ('active', '=', False), ('name', '=', 'BDT')]},
                    'value': {'currency_id': self.env['res.currency'].search([('name', '=', 'BDT')]), 'rate': 1.00}}
        else:
            return {
                'domain': {'currency_id': ['|', ('active', '=', True), ('active', '=', False), ('name', 'in', ('BDT', 'USD'))]}, 'value': {'currency_id': self.env['res.currency'].search([('name', '=', 'BDT')]), 'rate': 1.00}}

    @api.onchange('year', 'currency_id')
    def _onchange_currency(self):
        start_date = None
        end_date = None
        if self.year:
            y = int(self.year)
            start_date = date(y, 1, 1)
            end_date = date(y, 12, 31)
        if self.currency_id.name != 'BDT':
            currency_rate_obj = self.env['currency.conversion.rate'].search([('date', '>=', start_date), ('date', '<=', end_date), ('currency_id', '=', self.currency_id.id)], order='date DESC', limit=1)
            # try:
            #     currency_rate = sum(currency_rate_obj.mapped('rate'))/len(currency_rate_obj)
            # except:
            #     currency_rate = 1.00
            currency_rate = currency_rate_obj.rate
            if currency_rate_obj:
                return {'value': {'rate': currency_rate}}
            else:
                currency_rate_obj = self.env['currency.conversion.rate'].search(
                    [('date', '<=', start_date), ('currency_id', '=', self.currency_id.id)], order='date DESC', limit=1)
                # try:
                #     currency_rate = sum(currency_rate_obj.mapped('rate')) / len(currency_rate_obj)
                # except:
                #     currency_rate = 1.00
                currency_rate = currency_rate_obj.rate
                if currency_rate_obj:
                    return {'value': {'rate': currency_rate}}
                else:
                    return {'value': {'rate': 1.00}}
        else:
            return {'value': {'rate': 1.00}}

    @api.onchange('rate')
    def _onchange_rate(self):
        for rec in self:
            if rec.currency_id.name != 'BDT':
                if rec.rate < 0:
                    rec.rate = rec.rate * (-1)
                elif rec.rate == 0:
                    raise UserError('Input Foreign Rate that is greater than zero.')

    def month_wise_account_summary_report_excel(self):
        year = self.year
        is_multi_currency = self.is_multi_currency
        currency_id = self.currency_id
        other_currency_id = self.other_currency_id
        rate = self.rate

        # get data from sql
        data = self.month_wise_account_summary_report_sql(year, currency_id, rate, is_multi_currency, other_currency_id)

        file_name = "Month wise Account Summary Report - %s.xlsx" % year
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
        format6 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format6.set_align('right')
        format6.set_border()

        # grand total formatting
        format7 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True})
        format7.set_border()
        format8 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
        format8.set_border()
        format9 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
        format9.set_border()

        sheet = workbook.add_worksheet('Month wise Account Summary-%s' % year)

        head_row = 3
        head_col = 0

        sheet.write(head_row, head_col, 'Account Type', format1)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Parent Hierarchy', format1)
        head_col = head_col + 1

        sheet.write(head_row, head_col, 'Account Code', format2)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Account Name', format1)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Rate (Jan)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (Jan)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (Jan)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (Jan)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Jan)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (Feb)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (Feb)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (Feb)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (Feb)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Feb)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (Mar)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (Mar)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (Mar)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (Mar)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Mar)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (Apr)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (Apr)', format3)
        head_col = head_col + 1
        sheet.write(3, head_col, 'During (Apr)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (Apr)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Apr)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (May)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (May)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (May)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (May)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (May)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (Jun)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (Jun)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (Jun)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (Jun)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Jun)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (Jul)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (Jul)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (Jul)', format3)
        head_col = head_col + 1
        sheet.write(3, head_col, 'Closing (Jul)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Jul)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (Aug)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (Aug)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (Aug)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (Aug)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Aug)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (Sep)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (Sep)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (Sep)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (Sep)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Sep)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (Oct)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (Oct)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (Oct)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (Oct)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Oct)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (Nov)', format2)
            head_col = head_col + 1
        sheet.write(3, head_col, 'Opening (Nov)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (Nov)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (Nov)', format3)
        head_col = head_col + 1
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Nov)(USD)', format2)
            head_col = head_col + 1
            sheet.write(head_row, head_col, 'Rate (Dec)', format2)
            head_col = head_col + 1
        sheet.write(head_row, head_col, 'Opening (Dec)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'During (Dec)', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Closing (Dec)', format3)
        if is_multi_currency:
            sheet.write(head_row, head_col, 'Closing (Dec)(USD)', format2)

        sheet.merge_range(0, 0, 2, head_col,
                          "Month wise Account Summary Report - {0}".format(year), format0)

        row = 4
        col = 0

        for rec in data['csr']:
            sheet.write(row, col, rec['type'], format4)
            col = col + 1
            sheet.write(row, col, rec['parent_hierarchy'], format4)
            col = col + 1
            sheet.write(row, col, rec['code'], format5)
            col = col + 1
            sheet.write(row, col, rec['acc_name'], format4)
            col = col + 1
            # january
            if is_multi_currency:
                sheet.write(row, col, round(rec['rate_jan'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_jan'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_jan'], 2), format6)
            col = col + 1
            closing_jan = rec['op_jan'] + rec['dur_jan']
            sheet.write(row, col, round(closing_jan, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_jan/rec['rate_jan'], 2), format6)
                col = col + 1
            # february
                sheet.write(row, col, round(rec['rate_feb'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_feb'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_feb'], 2), format6)
            col = col + 1
            closing_feb = rec['op_feb'] + rec['dur_feb']
            sheet.write(row, col, round(closing_feb, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_feb/rec['rate_feb'], 2), format6)
                col = col + 1
            # march
                sheet.write(row, col, round(rec['rate_mar'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_mar'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_mar'], 2), format6)
            col = col + 1
            closing_mar = rec['op_mar'] + rec['dur_mar']
            sheet.write(row, col, round(closing_mar, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_mar/rec['rate_mar'], 2), format6)
                col = col + 1
            # april
                sheet.write(row, col, round(rec['rate_apr'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_apr'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_apr'], 2), format6)
            col = col + 1
            closing_apr = rec['op_apr'] + rec['dur_apr']
            sheet.write(row, col, round(closing_apr, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_apr/rec['rate_apr'], 2), format6)
                col = col + 1
            # may
                sheet.write(row, col, round(rec['rate_may'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_may'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_may'], 2), format6)
            col = col + 1
            closing_may = rec['op_may'] + rec['dur_may']
            sheet.write(row, col, round(closing_may, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_may/rec['rate_may'], 2), format6)
                col = col + 1
            # june
                sheet.write(row, col, round(rec['rate_jun'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_jun'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_jun'], 2), format6)
            col = col + 1
            closing_jun = rec['op_jun'] + rec['dur_jun']
            sheet.write(row, col, round(closing_jun, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_jun/rec['rate_jun'], 2), format6)
                col = col + 1
            # july
                sheet.write(row, col, round(rec['rate_jul'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_jul'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_jul'], 2), format6)
            col = col + 1
            closing_jul = rec['op_jul'] + rec['dur_jul']
            sheet.write(row, col, round(closing_jul, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_jul/rec['rate_jul'], 2), format6)
                col = col + 1
            # august
                sheet.write(row, col, round(rec['rate_aug'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_aug'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_aug'], 2), format6)
            col = col + 1
            closing_aug = rec['op_aug'] + rec['dur_aug']
            sheet.write(row, col, round(closing_aug, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_aug/rec['rate_aug'], 2), format6)
                col = col + 1
            # september
                sheet.write(row, col, round(rec['rate_sep'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_sep'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_sep'], 2), format6)
            col = col + 1
            closing_sep = rec['op_sep'] + rec['dur_sep']
            sheet.write(row, col, round(closing_sep, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_sep/rec['rate_sep'], 2), format6)
                col = col + 1
            # october
                sheet.write(row, col, round(rec['rate_oct'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_oct'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_oct'], 2), format6)
            col = col + 1
            closing_oct = rec['op_oct'] + rec['dur_oct']
            sheet.write(row, col, round(closing_oct, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_oct/rec['rate_oct'], 2), format6)
                col = col + 1
            # november
                sheet.write(row, col, round(rec['rate_nov'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_nov'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_nov'], 2), format6)
            col = col + 1
            closing_nov = rec['op_nov'] + rec['dur_nov']
            sheet.write(row, col, round(closing_nov, 2), format6)
            col = col + 1
            if is_multi_currency:
                sheet.write(row, col, round(closing_nov/rec['rate_nov'], 2), format6)
                col = col + 1
            # december
                sheet.write(row, col, round(rec['rate_dec'], 2), format6)
                col = col + 1
            sheet.write(row, col, round(rec['op_dec'], 2), format6)
            col = col + 1
            sheet.write(row, col, round(rec['dur_dec'], 2), format6)
            col = col + 1
            closing_dec = rec['op_dec'] + rec['dur_dec']
            sheet.write(row, col, round(closing_dec, 2), format6)
            if is_multi_currency:
                sheet.write(row, col, round(closing_dec/rec['rate_dec'], 2), format6)

            row = row + 1
            col = 0

        workbook.close()
        file_pointer.seek(0)
        #file_data = base64.encodestring(file_pointer.read())
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Month wise Account Summary Report',
            'type': 'ir.actions.act_url',
            # 'url': '/web/binary/download_document?model=month.wise.account.summary.report.wizard&field=file_data&id=%s&filename=%s' % (
            #     self.id, file_name),
            'url': '/web/content?model=month.wise.account.summary.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),

            'target': 'self',
        }

    def month_wise_account_summary_report_sql(self, year, currency_id, rate, is_multi_currency, other_currency_id):
        if year:
            y = int(year)
        else:
            y = datetime.today().year
        date_list = []
        for rec in range(1, 13):
            ndays = monthrange(y, rec)[1]
            start_date = date(y, rec, 1)
            end_date = date(y, rec, ndays)
            date_list.append(start_date)
            date_list.append(end_date)

        if is_multi_currency:
            currency_filter = "%s" % other_currency_id.id
        else:
            currency_filter = "%s" % currency_id.id
        #lang = f"'{self.env.context['lang']}'"
        if is_multi_currency:
            data_sql = """
                        SELECT coa.name->>'en_US' AS acc_name, coa.account_type AS type, coa.code,coa.parent_hierarchy,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{1}' AND '{2}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_jan,
                        SUM(CASE WHEN amvl.date < '{1}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jan,
                        SUM(CASE WHEN amvl.date BETWEEN '{1}' AND '{2}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jan,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{3}' AND '{4}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_feb,
                        SUM(CASE WHEN amvl.date < '{3}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_feb,
                        SUM(CASE WHEN amvl.date BETWEEN '{3}' AND '{4}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_feb,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{5}' AND '{6}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_mar,
                        SUM(CASE WHEN amvl.date < '{5}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_mar,
                        SUM(CASE WHEN amvl.date BETWEEN '{5}' AND '{6}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_mar,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{7}' AND '{8}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_apr,
                        SUM(CASE WHEN amvl.date < '{7}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_apr,
                        SUM(CASE WHEN amvl.date BETWEEN '{7}' AND '{8}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_apr,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{9}' AND '{10}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_may,
                        SUM(CASE WHEN amvl.date < '{9}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_may,
                        SUM(CASE WHEN amvl.date BETWEEN '{9}' AND '{10}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_may,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{11}' AND '{12}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_jun,
                        SUM(CASE WHEN amvl.date < '{11}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jun,
                        SUM(CASE WHEN amvl.date BETWEEN '{11}' AND '{12}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jun,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{13}' AND '{14}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_jul,
                        SUM(CASE WHEN amvl.date < '{13}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jul,
                        SUM(CASE WHEN amvl.date BETWEEN '{13}' AND '{14}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jul,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{15}' AND '{16}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_aug,
                        SUM(CASE WHEN amvl.date < '{15}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_aug,
                        SUM(CASE WHEN amvl.date BETWEEN '{15}' AND '{16}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_aug,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{17}' AND '{18}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_sep,
                        SUM(CASE WHEN amvl.date < '{17}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_sep,
                        SUM(CASE WHEN amvl.date BETWEEN '{17}' AND '{18}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_sep,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{19}' AND '{20}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_oct,
                        SUM(CASE WHEN amvl.date < '{19}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_oct,
                        SUM(CASE WHEN amvl.date BETWEEN '{19}' AND '{20}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_oct,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{21}' AND '{22}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_nov,
                        SUM(CASE WHEN amvl.date < '{21}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_nov,
                        SUM(CASE WHEN amvl.date BETWEEN '{21}' AND '{22}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_nov,
                        COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{23}' AND '{24}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_dec,
                        SUM(CASE WHEN amvl.date < '{23}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_dec,
                        SUM(CASE WHEN amvl.date BETWEEN '{23}' AND '{24}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_dec
                        FROM account_move_line amvl
                        LEFT JOIN account_account coa ON coa.id = amvl.account_id
                        --LEFT JOIN account_account_type acct ON acct.id = coa.user_type_id
                        WHERE amvl.parent_state = 'posted'
                        GROUP BY coa.name, coa.account_type, coa.code, coa.parent_hierarchy
                        ORDER BY coa.account_type, coa.code
                        """.format(rate, date_list[0], date_list[1], date_list[2], date_list[3], date_list[4], date_list[5], date_list[6], date_list[7], date_list[8], date_list[9], date_list[10], date_list[11], date_list[12], date_list[13], date_list[14], date_list[15], date_list[16], date_list[17], date_list[18], date_list[19], date_list[20], date_list[21], date_list[22], date_list[23], currency_filter)
            self.env.cr.execute(data_sql)
            data_list = self.env.cr.dictfetchall()
        else:
            data_sql = """
                        SELECT coa.name->>'en_US' AS acc_name, coa.account_type AS type, coa.code, coa.parent_hierarchy,
                        SUM(CASE WHEN amvl.date < '{1}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jan,
                        SUM(CASE WHEN amvl.date BETWEEN '{1}' AND '{2}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jan,
                        SUM(CASE WHEN amvl.date < '{3}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_feb,
                        SUM(CASE WHEN amvl.date BETWEEN '{3}' AND '{4}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_feb,
                        SUM(CASE WHEN amvl.date < '{5}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_mar,
                        SUM(CASE WHEN amvl.date BETWEEN '{5}' AND '{6}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_mar,
                        SUM(CASE WHEN amvl.date < '{7}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_apr,
                        SUM(CASE WHEN amvl.date BETWEEN '{7}' AND '{8}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_apr,
                        SUM(CASE WHEN amvl.date < '{9}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_may,
                        SUM(CASE WHEN amvl.date BETWEEN '{9}' AND '{10}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_may,
                        SUM(CASE WHEN amvl.date < '{11}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jun,
                        SUM(CASE WHEN amvl.date BETWEEN '{11}' AND '{12}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jun,
                        SUM(CASE WHEN amvl.date < '{13}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jul,
                        SUM(CASE WHEN amvl.date BETWEEN '{13}' AND '{14}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jul,
                        SUM(CASE WHEN amvl.date < '{15}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_aug,
                        SUM(CASE WHEN amvl.date BETWEEN '{15}' AND '{16}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_aug,
                        SUM(CASE WHEN amvl.date < '{17}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_sep,
                        SUM(CASE WHEN amvl.date BETWEEN '{17}' AND '{18}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_sep,
                        SUM(CASE WHEN amvl.date < '{19}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_oct,
                        SUM(CASE WHEN amvl.date BETWEEN '{19}' AND '{20}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_oct,
                        SUM(CASE WHEN amvl.date < '{21}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_nov,
                        SUM(CASE WHEN amvl.date BETWEEN '{21}' AND '{22}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_nov,
                        SUM(CASE WHEN amvl.date < '{23}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_dec,
                        SUM(CASE WHEN amvl.date BETWEEN '{23}' AND '{24}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_dec
                        FROM account_move_line amvl
                        LEFT JOIN account_account coa ON coa.id = amvl.account_id
                        --LEFT JOIN account_account_type acct ON acct.id = coa.user_type_id
                        WHERE amvl.parent_state = 'posted'
                        GROUP BY coa.name, coa.account_type, coa.code, coa.parent_hierarchy
                        ORDER BY coa.account_type, coa.code
                        """.format(rate, date_list[0], date_list[1], date_list[2], date_list[3], date_list[4],
                                   date_list[5], date_list[6], date_list[7], date_list[8], date_list[9],
                                   date_list[10], date_list[11], date_list[12], date_list[13], date_list[14],
                                   date_list[15], date_list[16], date_list[17], date_list[18], date_list[19],
                                   date_list[20], date_list[21], date_list[22], date_list[23])
            self.env.cr.execute(data_sql)
            data_list = self.env.cr.dictfetchall()

        data = {
            'model': 'month.wise.account.summary.report.wizard',
            'form': self.read()[0],
            'csr': data_list,
        }

        return data
