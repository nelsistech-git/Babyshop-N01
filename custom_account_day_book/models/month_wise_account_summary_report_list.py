from odoo import fields, models, api, tools
from datetime import datetime, date
from calendar import monthrange


class MonthwiseAccountSummaryReportList(models.Model):
    """ List View of Month wise Account Summary Report List """
    _name = 'month.wise.account.summary.report.list'
    _description = 'Month wise Account Summary Report List'
    _auto = False
    _order = 'account_type_id asc'

    # account_type_id = fields.Many2one('account.account.type', string='Account Type',
    #                                help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries.")

    selection_value = [
        ("asset_receivable", "Receivable"),
        ("asset_cash", "Bank and Cash"),
        ("asset_current", "Current Assets"),
        ("asset_non_current", "Non-current Assets"),
        ("asset_prepayments", "Prepayments"),
        ("asset_fixed", "Fixed Assets"),
        ("liability_payable", "Payable"),
        ("liability_credit_card", "Credit Card"),
        ("liability_current", "Current Liabilities"),
        ("liability_non_current", "Non-current Liabilities"),
        ("equity", "Equity"),
        ("equity_unaffected", "Current Year Earnings"),
        ("income", "Income"),
        ("income_other", "Other Income"),
        ("expense", "Expenses"),
        ("expense_depreciation", "Depreciation"),
        ("expense_direct_cost", "Cost of Revenue"),
        ("off_balance", "Off-Balance Sheet"),
        ("view", "View"),
    ]

    account_type_id = fields.Selection(selection_value, string='Account Type')

    account_id = fields.Many2one('account.account', string='Account')

    rate_jan = fields.Float(string='Rate (Jan)')
    opening_jan = fields.Float(string='Opening (Jan)')
    during_jan = fields.Float(string='During (Jan)')
    closing_jan = fields.Float(string='Closing (Jan)')
    closing_jan_usd = fields.Float(string='Closing (Jan)(USD)')
    rate_feb = fields.Float(string='Rate (Feb)')
    opening_feb = fields.Float(string='Opening (Feb)')
    during_feb = fields.Float(string='During (Feb)')
    closing_feb = fields.Float(string='Closing (Feb)')
    closing_feb_usd = fields.Float(string='Closing (Feb)(USD)')
    rate_mar = fields.Float(string='Rate (Mar)')
    opening_mar = fields.Float(string='Opening (Mar)')
    during_mar = fields.Float(string='During (Mar)')
    closing_mar = fields.Float(string='Closing (Mar)')
    closing_mar_usd = fields.Float(string='Closing (Mar)(USD)')
    rate_apr = fields.Float(string='Rate (Apr)')
    opening_apr = fields.Float(string='Opening (Apr)')
    during_apr = fields.Float(string='During (Apr)')
    closing_apr = fields.Float(string='Closing (Apr)')
    closing_apr_usd = fields.Float(string='Closing (Apr)(USD)')
    rate_may = fields.Float(string='Rate (May)')
    opening_may = fields.Float(string='Opening (May)')
    during_may = fields.Float(string='During (May)')
    closing_may = fields.Float(string='Closing (May)')
    closing_may_usd = fields.Float(string='Closing (May)(USD)')
    rate_jun = fields.Float(string='Rate (Jun)')
    opening_jun = fields.Float(string='Opening (Jun)')
    during_jun = fields.Float(string='During (Jun)')
    closing_jun = fields.Float(string='Closing (Jun)')
    closing_jun_usd = fields.Float(string='Closing (Jun)(USD)')
    rate_jul = fields.Float(string='Rate (Jul)')
    opening_jul = fields.Float(string='Opening (Jul)')
    during_jul = fields.Float(string='During (Jul)')
    closing_jul = fields.Float(string='Closing (Jul)')
    closing_jul_usd = fields.Float(string='Closing (Jul)(USD)')
    rate_aug = fields.Float(string='Rate (Aug)')
    opening_aug = fields.Float(string='Opening (Aug)')
    during_aug = fields.Float(string='During (Aug)')
    closing_aug = fields.Float(string='Closing (Aug)')
    closing_aug_usd = fields.Float(string='Closing (Aug)(USD)')
    rate_sep = fields.Float(string='Rate (Sep)')
    opening_sep = fields.Float(string='Opening (Sep)')
    during_sep = fields.Float(string='During (Sep)')
    closing_sep = fields.Float(string='Closing (Sep)')
    closing_sep_usd = fields.Float(string='Closing (Sep)(USD)')
    rate_oct = fields.Float(string='Rate (Oct)')
    opening_oct = fields.Float(string='Opening (Oct)')
    during_oct = fields.Float(string='During (Oct)')
    closing_oct = fields.Float(string='Closing (Oct)')
    closing_oct_usd = fields.Float(string='Closing (Oct)(USD)')
    rate_nov = fields.Float(string='Rate (Nov)')
    opening_nov = fields.Float(string='Opening (Nov)')
    during_nov = fields.Float(string='During (Nov)')
    closing_nov = fields.Float(string='Closing (Nov)')
    closing_nov_usd = fields.Float(string='Closing (Nov)(USD)')
    rate_dec = fields.Float(string='Rate (Dec)')
    opening_dec = fields.Float(string='Opening (Dec)')
    during_dec = fields.Float(string='During (Dec)')
    closing_dec = fields.Float(string='Closing (Dec)')
    closing_dec_usd = fields.Float(string='Closing (Dec)(USD)')

    # def init(self):
    #     tools.drop_view_if_exists(self._cr, 'month_wise_account_summary_report_list')
    #     rate = 1.00
    #     if self._context.get('rate'):
    #         rate = self._context.get('rate')
    #     if self._context.get('year'):
    #         y = int(self._context.get('year'))
    #     else:
    #         y = datetime.today().year
    #     date_list = []
    #     for rec in range(1, 13):
    #         ndays = monthrange(y, rec)[1]
    #         start_date = date(y, rec, 1)
    #         end_date = date(y, rec, ndays)
    #         date_list.append(start_date)
    #         date_list.append(end_date)
    #
    #     print(self._context.get('other_currency_id'))
    #
    #     if self._context.get('is_multi_currency'):
    #         currency_filter = "%s" % self._context.get('other_currency_id')
    #     else:
    #         currency_filter = "%s" % self._context.get('currency_id')
    #
    #     if self._context.get('is_list_view'):
    #         if self._context.get('is_multi_currency'):
    #             self._cr.execute("""
    #                 CREATE OR REPLACE VIEW month_wise_account_summary_report_list AS (
    #                 SELECT row_number() OVER () as id, main_tbl.acc_name, main_tbl.type, main_tbl.code,
    #                 SUM(rate_jan) AS rate_jan, SUM(op_jan) AS opening_jan, SUM(dur_jan) AS during_jan, SUM(op_jan+dur_jan) AS closing_jan, SUM((op_jan+dur_jan)/rate_jan) AS closing_jan_usd, SUM(rate_feb) AS rate_feb, SUM(op_feb) AS opening_feb, SUM(dur_feb) AS during_feb, SUM(op_feb+dur_feb) AS closing_feb, SUM((op_feb+dur_feb)/rate_feb) AS closing_feb_usd, SUM(rate_mar) AS rate_mar, SUM(op_mar) AS opening_mar, SUM(dur_mar) AS during_mar, SUM(op_mar+dur_mar) AS closing_mar, SUM((op_mar+dur_mar)/rate_mar) AS closing_mar_usd, SUM(rate_apr) AS rate_apr, SUM(op_apr) AS opening_apr, SUM(dur_apr) AS during_jan, SUM(op_apr+dur_apr) AS closing_apr, SUM((op_apr+dur_apr)/rate_apr) AS closing_apr_usd, SUM(rate_may) AS rate_may, SUM(op_may) AS opening_may, SUM(dur_may) AS during_may, SUM(op_may+dur_may) AS closing_may, SUM((op_may+dur_may)/rate_may) AS closing_may_usd, SUM(rate_jun) AS rate_jun, SUM(op_jun) AS opening_jun, SUM(dur_jun) AS during_jan, SUM(op_jun+dur_jun) AS closing_jun, SUM((op_jun+dur_jun)/rate_jun) AS closing_jun_usd, SUM(rate_jul) AS rate_jul, SUM(op_jul) AS opening_jul, SUM(dur_jul) AS during_jul, SUM(op_jul+dur_jul) AS closing_jul, SUM((op_jul+dur_jul)/rate_jul) AS closing_jul_usd, SUM(rate_aug) AS rate_aug, SUM(op_aug) AS opening_aug, SUM(dur_aug) AS during_jan, SUM(op_aug+dur_aug) AS closing_aug, SUM((op_aug+dur_aug)/rate_aug) AS closing_aug_usd, SUM(rate_sep) AS rate_sep, SUM(op_sep) AS opening_sep, SUM(dur_sep) AS during_sep, SUM(op_sep+dur_sep) AS closing_sep, SUM((op_sep+dur_sep)/rate_sep) AS closing_sep_usd, SUM(rate_oct) AS rate_oct, SUM(op_oct) AS opening_oct, SUM(dur_oct) AS during_jan, SUM(op_oct+dur_oct) AS closing_oct, SUM((op_oct+dur_oct)/rate_oct) AS closing_oct_usd, SUM(rate_nov) AS rate_nov, SUM(op_nov) AS opening_nov, SUM(dur_nov) AS during_nov, SUM(op_nov+dur_nov) AS closing_nov, SUM((op_nov+dur_nov)/rate_nov) AS closing_nov_usd, SUM(rate_dec) AS rate_dec, SUM(op_dec) AS opening_dec, SUM(dur_dec) AS during_jan, SUM(op_dec+dur_dec) AS closing_dec, SUM((op_dec+dur_dec)/rate_dec) AS closing_dec_usd,
    #                 FROM (
    #                     SELECT coa.name AS acc_name, acct.name AS type, coa.code,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{1}' AND '{2}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_jan,
    #                     SUM(CASE WHEN amvl.date < '{1}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jan,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{1}' AND '{2}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jan,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{3}' AND '{4}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_feb,
    #                     SUM(CASE WHEN amvl.date < '{3}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_feb,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{3}' AND '{4}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_feb,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{5}' AND '{6}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_sep,
    #                     SUM(CASE WHEN amvl.date < '{5}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_mar,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{5}' AND '{6}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_mar,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{7}' AND '{8}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_apr,
    #                     SUM(CASE WHEN amvl.date < '{7}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_apr,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{7}' AND '{8}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_apr,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{9}' AND '{10}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_may,
    #                     SUM(CASE WHEN amvl.date < '{9}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_may,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{9}' AND '{10}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_may,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{11}' AND '{12}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_jun,
    #                     SUM(CASE WHEN amvl.date < '{11}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jun,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{11}' AND '{12}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jun,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{13}' AND '{14}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_jul,
    #                     SUM(CASE WHEN amvl.date < '{13}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jul,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{13}' AND '{14}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jul,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{15}' AND '{16}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_aug,
    #                     SUM(CASE WHEN amvl.date < '{15}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_aug,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{15}' AND '{16}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_aug,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{17}' AND '{18}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_sep,
    #                     SUM(CASE WHEN amvl.date < '{17}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_sep,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{17}' AND '{18}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_sep,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{19}' AND '{20}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_oct,
    #                     SUM(CASE WHEN amvl.date < '{19}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_oct,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{19}' AND '{20}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_oct,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{21}' AND '{22}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_nov,
    #                     SUM(CASE WHEN amvl.date < '{21}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_nov,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{21}' AND '{22}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_nov,
    #                     COALESCE((SELECT rate FROM currency_conversion_rate WHERE date BETWEEN '{23}' AND '{24}' AND currency_id = {25} ORDER BY date DESC LIMIT 1), 1) AS rate_dec,
    #                     SUM(CASE WHEN amvl.date < '{23}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_dec,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{23}' AND '{24}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_dec
    #                     FROM account_move_line amvl
    #                     LEFT JOIN account_account coa ON coa.id = amvl.account_id
    #                     LEFT JOIN account_account_type acct ON acct.id = coa.user_type_id
    #                     WHERE amvl.parent_state = 'posted'
    #                     GROUP BY coa.name, acct.name, coa.code
    #                     ORDER BY acct.name, coa.code
    #                     ) main_tbl
    #                     GROUP BY main_tbl.acc_name, main_tbl.type, main_tbl.code
    #                     ORDER BY main_tbl.type, main_tbl.code
    #             """.format(rate, date_list[0], date_list[1], date_list[2], date_list[3], date_list[4], date_list[5], date_list[6], date_list[7], date_list[8], date_list[9], date_list[10], date_list[11], date_list[12], date_list[13], date_list[14], date_list[15], date_list[16], date_list[17], date_list[18], date_list[19], date_list[20], date_list[21], date_list[22], date_list[23], currency_filter))
    #         else:
    #             self._cr.execute("""
    #                 CREATE OR REPLACE VIEW month_wise_account_summary_report_list AS (
    #                 SELECT row_number() OVER () as id, main_tbl.acc_name, main_tbl.type, main_tbl.code,
    #                 SUM(op_jan) AS opening_jan, SUM(dur_jan) AS during_jan, SUM(op_jan+dur_jan) AS closing_jan, SUM(op_feb) AS opening_feb, SUM(dur_feb) AS during_feb, SUM(op_feb+dur_feb) AS closing_feb, SUM(op_mar) AS opening_mar, SUM(dur_mar) AS during_mar, SUM(op_mar+dur_mar) AS closing_mar, SUM(op_apr) AS opening_apr, SUM(dur_apr) AS during_jan, SUM(op_apr+dur_apr) AS closing_apr, SUM(op_may) AS opening_may, SUM(dur_may) AS during_may, SUM(op_may+dur_may) AS closing_may, SUM(op_jun) AS opening_jun, SUM(dur_jun) AS during_jan, SUM(op_jun+dur_jun) AS closing_jun, SUM(op_jul) AS opening_jul, SUM(dur_jul) AS during_jul, SUM(op_jul+dur_jul) AS closing_jul,  SUM(op_aug) AS opening_aug, SUM(dur_aug) AS during_jan, SUM(op_aug+dur_aug) AS closing_aug, SUM(op_sep) AS opening_sep, SUM(dur_sep) AS during_sep, SUM(op_sep+dur_sep) AS closing_sep, SUM(op_oct) AS opening_oct, SUM(dur_oct) AS during_jan, SUM(op_oct+dur_oct) AS closing_oct, SUM(op_nov) AS opening_nov, SUM(dur_nov) AS during_nov, SUM(op_nov+dur_nov) AS closing_nov, SUM(op_dec) AS opening_dec, SUM(dur_dec) AS during_jan, SUM(op_dec+dur_dec) AS closing_dec
    #                 FROM (
    #                     SELECT coa.name AS acc_name, acct.name AS type, coa.code,
    #                     SUM(CASE WHEN amvl.date < '{1}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jan,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{1}' AND '{2}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jan,
    #                     SUM(CASE WHEN amvl.date < '{3}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_feb,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{3}' AND '{4}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_feb,
    #                     SUM(CASE WHEN amvl.date < '{5}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_mar,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{5}' AND '{6}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_mar,
    #                     SUM(CASE WHEN amvl.date < '{7}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_apr,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{7}' AND '{8}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_apr,
    #                     SUM(CASE WHEN amvl.date < '{9}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_may,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{9}' AND '{10}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_may,
    #                     SUM(CASE WHEN amvl.date < '{11}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jun,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{11}' AND '{12}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jun,
    #                     SUM(CASE WHEN amvl.date < '{13}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_jul,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{13}' AND '{14}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_jul,
    #                     SUM(CASE WHEN amvl.date < '{15}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_aug,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{15}' AND '{16}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_aug,
    #                     SUM(CASE WHEN amvl.date < '{17}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_sep,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{17}' AND '{18}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_sep,
    #                     SUM(CASE WHEN amvl.date < '{19}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_oct,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{19}' AND '{20}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_oct,
    #                     SUM(CASE WHEN amvl.date < '{21}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_nov,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{21}' AND '{22}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_nov,
    #                     SUM(CASE WHEN amvl.date < '{23}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS op_dec,
    #                     SUM(CASE WHEN amvl.date BETWEEN '{23}' AND '{24}' THEN COALESCE((amvl.debit - amvl.credit)/{0}, 0) ELSE 0 END) AS dur_dec
    #                     FROM account_move_line amvl
    #                     LEFT JOIN account_account coa ON coa.id = amvl.account_id
    #                     LEFT JOIN account_account_type acct ON acct.id = coa.user_type_id
    #                     WHERE amvl.parent_state = 'posted'
    #                     GROUP BY coa.name, acct.name, coa.code
    #                     ORDER BY acct.name, coa.code
    #                     ) main_tbl
    #                     GROUP BY main_tbl.acc_name, main_tbl.type, main_tbl.code
    #                     ORDER BY main_tbl.type, main_tbl.code
    #             """.format(rate, date_list[0], date_list[1], date_list[2], date_list[3], date_list[4], date_list[5],
    #                        date_list[6], date_list[7], date_list[8], date_list[9], date_list[10], date_list[11],
    #                        date_list[12], date_list[13], date_list[14], date_list[15], date_list[16], date_list[17],
    #                        date_list[18], date_list[19], date_list[20], date_list[21], date_list[22], date_list[23]))

    @api.model
    def action_month_wise_account_summary_report_list(self, y, currency_id, other_currency_id, is_multi_currency, rate):
        #print('1111111111111')
        """ Action Method """
        tools.drop_view_if_exists(self._cr, 'month_wise_account_summary_report_list')
        if y:
            y = int(y)
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
            currency_filter = "%s" % other_currency_id
        else:
            currency_filter = "%s" % currency_id
        if is_multi_currency:
            self._cr.execute("""
                CREATE OR REPLACE VIEW month_wise_account_summary_report_list AS (
                SELECT row_number() OVER () as id, main_tbl.type_id AS account_type_id, main_tbl.acc_id AS account_id, 
                SUM(rate_jan) AS rate_jan, SUM(op_jan) AS opening_jan, SUM(dur_jan) AS during_jan, SUM(op_jan+dur_jan) AS closing_jan, SUM((op_jan+dur_jan)/rate_jan) AS closing_jan_usd, SUM(rate_feb) AS rate_feb, SUM(op_feb) AS opening_feb, SUM(dur_feb) AS during_feb, SUM(op_feb+dur_feb) AS closing_feb, SUM((op_feb+dur_feb)/rate_feb) AS closing_feb_usd, SUM(rate_mar) AS rate_mar, SUM(op_mar) AS opening_mar, SUM(dur_mar) AS during_mar, SUM(op_mar+dur_mar) AS closing_mar, SUM((op_mar+dur_mar)/rate_mar) AS closing_mar_usd, SUM(rate_apr) AS rate_apr, SUM(op_apr) AS opening_apr, SUM(dur_apr) AS during_apr, SUM(op_apr+dur_apr) AS closing_apr, SUM((op_apr+dur_apr)/rate_apr) AS closing_apr_usd, SUM(rate_may) AS rate_may, SUM(op_may) AS opening_may, SUM(dur_may) AS during_may, SUM(op_may+dur_may) AS closing_may, SUM((op_may+dur_may)/rate_may) AS closing_may_usd, SUM(rate_jun) AS rate_jun, SUM(op_jun) AS opening_jun, SUM(dur_jun) AS during_jun, SUM(op_jun+dur_jun) AS closing_jun, SUM((op_jun+dur_jun)/rate_jun) AS closing_jun_usd, SUM(rate_jul) AS rate_jul, SUM(op_jul) AS opening_jul, SUM(dur_jul) AS during_jul, SUM(op_jul+dur_jul) AS closing_jul, SUM((op_jul+dur_jul)/rate_jul) AS closing_jul_usd, SUM(rate_aug) AS rate_aug, SUM(op_aug) AS opening_aug, SUM(dur_aug) AS during_aug, SUM(op_aug+dur_aug) AS closing_aug, SUM((op_aug+dur_aug)/rate_aug) AS closing_aug_usd, SUM(rate_sep) AS rate_sep, SUM(op_sep) AS opening_sep, SUM(dur_sep) AS during_sep, SUM(op_sep+dur_sep) AS closing_sep, SUM((op_sep+dur_sep)/rate_sep) AS closing_sep_usd, SUM(rate_oct) AS rate_oct, SUM(op_oct) AS opening_oct, SUM(dur_oct) AS during_oct, SUM(op_oct+dur_oct) AS closing_oct, SUM((op_oct+dur_oct)/rate_oct) AS closing_oct_usd, SUM(rate_nov) AS rate_nov, SUM(op_nov) AS opening_nov, SUM(dur_nov) AS during_nov, SUM(op_nov+dur_nov) AS closing_nov, SUM((op_nov+dur_nov)/rate_nov) AS closing_nov_usd, SUM(rate_dec) AS rate_dec, SUM(op_dec) AS opening_dec, SUM(dur_dec) AS during_dec, SUM(op_dec+dur_dec) AS closing_dec, SUM((op_dec+dur_dec)/rate_dec) AS closing_dec_usd
                FROM (
                    SELECT coa.id AS acc_id, coa.account_type AS type_id,
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
                    --LEFT JOIN account_account_type acct ON acct.id = coa.account_type
                    WHERE amvl.parent_state = 'posted'
                    GROUP BY coa.id, coa.account_type
                    ORDER BY coa.account_type, coa.id
                ) main_tbl
                GROUP BY main_tbl.acc_id, main_tbl.type_id
                ORDER BY main_tbl.type_id, main_tbl.acc_id
                )
            """.format(rate, date_list[0], date_list[1], date_list[2], date_list[3], date_list[4], date_list[5], date_list[6], date_list[7], date_list[8], date_list[9], date_list[10], date_list[11], date_list[12], date_list[13], date_list[14], date_list[15], date_list[16], date_list[17], date_list[18], date_list[19], date_list[20], date_list[21], date_list[22], date_list[23], currency_filter))
        else:
            self._cr.execute("""
                CREATE OR REPLACE VIEW month_wise_account_summary_report_list AS (
                SELECT row_number() OVER () as id, main_tbl.type_id AS account_type_id, main_tbl.acc_id AS account_id, 
                0 AS rate_jan, SUM(op_jan) AS opening_jan, SUM(dur_jan) AS during_jan, SUM(op_jan+dur_jan) AS closing_jan, 0 AS closing_jan_usd, 0 AS rate_feb, SUM(op_feb) AS opening_feb, SUM(dur_feb) AS during_feb, SUM(op_feb+dur_feb) AS closing_feb, 0 AS closing_feb_usd, 0 AS rate_mar, SUM(op_mar) AS opening_mar, SUM(dur_mar) AS during_mar, SUM(op_mar+dur_mar) AS closing_mar, 0 AS closing_mar_usd, 0 AS rate_apr, SUM(op_apr) AS opening_apr, SUM(dur_apr) AS during_apr, SUM(op_apr+dur_apr) AS closing_apr, 0 AS closing_apr_usd, 0 AS rate_may, SUM(op_may) AS opening_may, SUM(dur_may) AS during_may, SUM(op_may+dur_may) AS closing_may, 0 AS closing_may_usd, 0 AS rate_jun, SUM(op_jun) AS opening_jun, SUM(dur_jun) AS during_jun, SUM(op_jun+dur_jun) AS closing_jun, 0 AS closing_jun_usd, 0 AS rate_jul, SUM(op_jul) AS opening_jul, SUM(dur_jul) AS during_jul, SUM(op_jul+dur_jul) AS closing_jul, 0 AS closing_jul_usd, 0 AS rate_aug, SUM(op_aug) AS opening_aug, SUM(dur_aug) AS during_aug, SUM(op_aug+dur_aug) AS closing_aug, 0 AS closing_aug_usd, 0 AS rate_sep, SUM(op_sep) AS opening_sep, SUM(dur_sep) AS during_sep, SUM(op_sep+dur_sep) AS closing_sep, 0 AS closing_sep_usd, 0 AS rate_oct, SUM(op_oct) AS opening_oct, SUM(dur_oct) AS during_oct, SUM(op_oct+dur_oct) AS closing_oct, 0 AS closing_oct_usd, 0 AS rate_nov, SUM(op_nov) AS opening_nov, SUM(dur_nov) AS during_nov, SUM(op_nov+dur_nov) AS closing_nov, 0 AS closing_nov_usd, 0 AS rate_dec, SUM(op_dec) AS opening_dec, SUM(dur_dec) AS during_dec, SUM(op_dec+dur_dec) AS closing_dec, 0 AS closing_dec_usd
                FROM (
                    SELECT coa.id AS acc_id, coa.account_type AS type_id,
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
                    --LEFT JOIN account_account_type acct ON acct.id = coa.account_type
                    WHERE amvl.parent_state = 'posted'
                    GROUP BY coa.id, coa.account_type
                    ORDER BY coa.account_type, coa.id
                    ) main_tbl
                    GROUP BY main_tbl.acc_id, main_tbl.type_id
                    ORDER BY main_tbl.type_id, main_tbl.acc_id
                )
                """.format(rate, date_list[0], date_list[1], date_list[2], date_list[3], date_list[4], date_list[5],
                       date_list[6], date_list[7], date_list[8], date_list[9], date_list[10], date_list[11],
                       date_list[12], date_list[13], date_list[14], date_list[15], date_list[16], date_list[17],
                       date_list[18], date_list[19], date_list[20], date_list[21], date_list[22], date_list[23]))

        IrModelData = self.env['ir.model.data']
        tree_view_id = IrModelData._xmlid_to_res_id('custom_account_day_book.view_month_wise_account_summary_report_list_tree')
        #actionObject = IrModelData.xmlid_to_object('custom_account_day_book.action_month_wise_account_summary_report_list')
        actionObject = self.env.ref('custom_account_day_book.action_month_wise_account_summary_report_list')

        action = actionObject.sudo().read(
            ['name', 'help', 'res_model', 'target', 'domain', 'context', 'search_view_id'])
        if not action:
            action = {}
        else:
            action = action[0]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Month wise Account Summary Report',
            'view_mode': 'tree',
            'res_model': 'month.wise.account.summary.report.list',
            'views': [(tree_view_id, 'tree')],
            'search_view_id': self.env.ref('custom_account_day_book.view_month_wise_account_summary_report_list_search').id,
            'context': {'is_multi_currency': is_multi_currency},
            'target': 'current'
        }
