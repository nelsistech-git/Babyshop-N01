from odoo import fields, models,_
import datetime
from odoo.exceptions import UserError


class StockMRRReport(models.TransientModel):
    _name = "stock.mrr.report.wizard"
    _description = "MRR Report"

    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")

    def mrr_report_pdf(self):
        from_date = self.from_date
        to_date = self.to_date

        delta = to_date - from_date
        if delta.days < 0:
            raise UserError(
                _("From date can't be greater than To Date.")
            )

        # get data from sql
        data = self.get_report_sql(from_date, to_date)
        return self.env.ref('custom_stock.stock_mrr_report_id').with_context(
            landscape=True).report_action(self, data=data)

    def get_report_sql(self, from_date, to_date):
        fromDate = str(from_date)
        fromDateStr  = "'"+fromDate+"'"

        toDate = str(to_date)
        toDateStr = "'" + toDate + "'"

        self._cr.execute(('''select sm.product_id, pt.name,pp.barcode,sum(pol.price_unit) as list_price,
                            0 AS bonus_qty,
                            0 AS qty
                            from stock_picking sp
                            left join stock_move sm on sm.picking_id= sp.id
                            left join purchase_order_line pol on sm.purchase_line_id= pol.id
                            left join stock_picking_type spt on sp.picking_type_id= spt.id
                            left join product_product pp on sm.product_id= pp.id
                            left join product_template pt on pp.product_tmpl_id = pt.id
                            where spt.sequence_code='IN' and date(sp.date) between %s and %s
                            group by sm.product_id, pt.name,pp.barcode            
                                ''') % (fromDateStr,toDateStr))
        sql_result = self.env.cr.dictfetchall()
        customer_invoice_list = []
        # -----------
        sl = 1
        total_bonus_qty = 0
        total_qty = 0
        total_amount = 0
        for data in sql_result:
            pro_obj = self.env['product.product'].browse(data['product_id'])
            product_name = pro_obj.display_name
            list_price = 0
            if data['list_price'] != None:
                list_price = data['list_price']
            qty = data['qty']
            bonus_qty = data['bonus_qty']
            total_qty = qty + bonus_qty
            amount = total_qty * list_price
            amount_format_float = "{:.2f}".format(amount)
            vals = {
                'sl': sl,
                'name': product_name,
                'barcode': data['barcode'],
                'bonus_qty': bonus_qty,
                'qty': qty ,
                'price_unit': list_price,
                'total_amount': amount_format_float
            }
            total_amt = 0
            if data['list_price'] != None:
                total_amt = list_price * (data['qty']+data['bonus_qty'])
            customer_invoice_list.append(vals)
            sl = sl+1
            total_bonus_qty += data['bonus_qty']
            total_qty += data['qty']
            total_amount += total_amt



        data = {
            'model': "stock.mrr.report.wizard",
            'form': self.read()[0],
            'total_bonus_qty': total_bonus_qty,
            'total_qty': total_qty,
            'total_amount': total_amount,
            'csr': customer_invoice_list,
            'from_date': datetime.datetime.strptime(str(from_date), '%Y-%m-%d').strftime('%d-%b-%Y'),
            'to_date': datetime.datetime.strptime(str(to_date), '%Y-%m-%d').strftime('%d-%b-%Y'),
        }
        return data




