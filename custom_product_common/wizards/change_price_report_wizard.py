from odoo import fields, models, api, _
from odoo.exceptions import  ValidationError
import datetime


class ChangePriceReportWizard(models.TransientModel):
    _name = "change.price.report.wizard"
    _description = "Sale Price Change Report Wizard"

    start_date = fields.Date(string='From Date', required=True)
    end_date = fields.Date(string='To Date', required=True, default=fields.Date.context_today)

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('End date cannot be greater than the start date.'))

    def change_price_report_pdf(self):
        start_date = self.start_date
        end_date = self.end_date

        # get data from sql
        data = self.change_price_report_sql(start_date, end_date)

        return self.env.ref(
            'custom_product_common.change_price_report_tmpl').with_context().report_action(self, data=data)

    def change_price_report_sql(self, start_date, end_date):
        start_date = datetime.datetime.strptime(str(start_date), '%Y-%m-%d').strftime('%d-%b-%Y')
        end_date = datetime.datetime.strptime(str(end_date), '%Y-%m-%d').strftime('%d-%b-%Y')
        data_sql = """
                    SELECT DATE(create_date) as create_date, product_id, old_sales_price, new_sales_price, create_uid, approved_by_id
                    FROM sales_price_update
                    WHERE DATE(create_date) BETWEEN '%s' and '%s';
                    """ % (start_date, end_date)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        data_list = []

        for d in data_res:
            vals = {
                'create_date': datetime.datetime.strptime(str(d['create_date']), '%Y-%m-%d').strftime('%d-%b-%Y'),
                'code': self.env['product.template'].browse(d['product_id']).product_code,
                'product_name': self.env['product.template'].browse(d['product_id']).name,
                'old_sales_price': d['old_sales_price'],
                'new_sales_price': d['new_sales_price'],
                'created_by': self.env['res.users'].browse(d['create_uid']).name,
                'approved_by': self.env['res.users'].browse(d['approved_by_id']).name
            }
            data_list.append(vals)

        data = {
            'model': "change.price.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'start_date': start_date,
            'end_date': end_date,
        }
        return data
