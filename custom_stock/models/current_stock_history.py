from odoo import models, fields, api, _
from odoo.addons.helper import validator
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time


class CurrentStockHistoryHead(models.Model):
    _name = "current.stock.history.head"
    _description = "Current Stock History Head"
    _rec_name = 'date'
    _order = 'date desc'

    date = fields.Date('Date', required=True)
    history_ids = fields.One2many('current.stock.history', 'head_id', string='Stock History')
    generate_flag = fields.Boolean(default=False)

    @api.constrains('date')
    def _check_unique_constraint(self):
        msg1 = "Stock Date"

        envObj = self.env['current.stock.history.head']
        conditionList1 = [('date', '=', self.date)]
        validator.check_duplicate_value(self, envObj, conditionList1, msg1)

    def unlink(self):
        for r in self:
            if r.generate_flag == True:
                raise UserError(_("Record can't be deleted!"))

        return super(CurrentStockHistoryHead, self).unlink()

    def clear_stock_date(self):
        self.write({
            'history_ids': [(5, 0, 0)],
            'generate_flag': False
        })
        return True

    def auto_backup_current_stock(self):
        """Current stock history backup scheduler"""

        backup_datetime = datetime.now() - timedelta(hours=6)
        # backup_datetime = datetime.now() - relativedelta(hours=6) #+ relativedelta(days=-1)
        current_date = backup_datetime.strftime('%Y-%m-%d')

        stock_obj = self.env['current.stock.history.head']
        stock_row = stock_obj.search([('date', '=', current_date)], limit=1)
        if stock_row:
            # print 'already created'
            return "already created"
        else:
            insert_vals = {'date': current_date}

            try:
                head_obj = stock_obj.create(insert_vals)
                head_obj.generate_data_backup()
            except:
                return 'Data not available'
            return "Success"

    def generate_data_backup(self):
        if self.date and self.generate_flag == False:
            head_id = self.id
            stock_date = self.date

            history_obj = self.env['current.stock.history']
            count = 0
            quant_rows = self.env['stock.quant'].search([])
            for row in quant_rows:
                location_id = row.location_id.id
                product_id = row.product_id.id
                in_date = row.in_date
                quantity = row.quantity
                unit_cost = row.product_id.standard_price
                unit_cost_quant = row.value
                unit_other_cost_quant = row.total_cost_rate
                unit_other_cost = row.product_id.other_cost
                unit_sale_price = row.product_id.list_price

                history_obj.create({
                    'head_id': head_id,
                    'date': stock_date,
                    'location_id': location_id,
                    'product_id': product_id,
                    'in_date': in_date,
                    'quantity': quantity,
                    'unit_cost': unit_cost,
                    'unit_cost_quant': unit_cost_quant,
                    'unit_other_cost': unit_other_cost,
                    'unit_other_cost_quant': unit_other_cost_quant,
                    'unit_sale_price': unit_sale_price
                })

                count += 1
                if count % 500 == 0:
                    time.sleep(2)
                    # count = 0
                    #print('count-------------', count)

            # end loop
            self.generate_flag = True


class CurrentStockHistory(models.Model):
    _name = "current.stock.history"
    _description = "Current Stock History"
    _rec_name = 'product_id'

    head_id = fields.Many2one('current.stock.history.head', ondelete="cascade", string='Current Stock', readonly=True)

    date = fields.Date('Date', readonly=True)
    location_id = fields.Many2one('stock.location', 'Location', required=True, readonly=True, index=True)
    product_id = fields.Many2one('product.product', 'Product', required=True, readonly=True, index=True)

    product_tmpl_id = fields.Many2one('product.template', string='Product Template',
                                      related='product_id.product_tmpl_id', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True, related='product_id.uom_id')
    in_date = fields.Datetime('Incoming Date', readonly=True)

    quantity = fields.Float('Quantity', readonly=True)
    unit_cost = fields.Float(string='Unit Cost', default=0)
    unit_cost_quant = fields.Float(string='Total Cost', default=0)
    unit_other_cost = fields.Float(string='Unit Other Cost', default=0)
    unit_other_cost_quant = fields.Float(string='Total Other Cost', default=0)
    unit_sale_price = fields.Float(string='Unit Sale Price', default=0)
