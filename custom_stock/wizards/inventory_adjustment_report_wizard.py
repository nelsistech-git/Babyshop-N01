from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
from datetime import datetime

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.helper import xlsxwriter

import base64
from io import BytesIO


class InventoryAdjustmentReportWizard(models.TransientModel):
    _name = "inventory.adjustment.report.wizard"
    _description = "Inventory Adjustment Report"

    file_data = fields.Binary('Inventory Adjustment Report')
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    category_id = fields.Many2one('product.category', string='Product Category')
    product_id = fields.Many2one('product.product', string='Product', help="Main Product",
                                 domain="[('state', '=', 'approve'), ('product_tmpl_id.categ_id', 'child_of', category_id)]")
    location_id = fields.Many2one('stock.location', string='Location',
                                  domain="[('usage', '=', 'internal'), ('state', '=', 'done')]")
    qty_type = fields.Selection([
        ('in_qty', 'In Quantity'),
        ('out_qty', 'Out Quantity'),
    ], string='Type')

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('End date cannot be greater than the start date.'))

    def inventory_adjust_report_excel(self):
        start_date = self.start_date
        end_date = self.end_date
        qty_type = self.qty_type
        category_id = self.category_id.id
        product_id = self.product_id.id
        location_id = self.location_id

        # get data from sql
        data = self.inventory_adjust_report_sql(start_date, end_date, category_id, product_id, location_id, qty_type)

        start_date = datetime.strptime(str(self.start_date), '%Y-%m-%d').strftime('%d-%b-%Y')
        end_date = datetime.strptime(str(self.end_date), '%Y-%m-%d').strftime('%d-%b-%Y')

        file_name = "Inventory Adjustment Report (%s - %s).xlsx" % (start_date, end_date)
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

        sheet = workbook.add_worksheet('Inventory Adjustment Report')

        t_in_qty = 0
        t_out_qty = 0


        if data['qty_type'] == 'in_qty':
            if data['loc_name'] == 'All Locations':
                sheet.merge_range(0, 0, 2, 2,
                                  "Inventory Adjustment Report (%s - %s)" % (start_date, end_date), format0)

                sheet.merge_range(3, 0, 3, 1, 'Category: {0}'.format(data['categ_name']), format1)
                sheet.write(3, 2, 'Location: {0}'.format(data['loc_name']), format3)

                sheet.write(4, 0, 'Location', format1)
                sheet.write(4, 1, 'Product', format1)
                sheet.write(4, 2, 'In Qty', format3)

                row = 5
                col = 0

                for rec in data['csr']:
                    if rec['in_qty'] != 0:
                        sheet.write(row, col, rec['location_name'], format4)
                        sheet.write(row, col + 1, rec['product_name'], format4)
                        sheet.write(row, col + 2, round(rec['in_qty'], 3), format6)
                        t_in_qty = t_in_qty + rec['in_qty']

                        row = row + 1

                final_row = row
                final_col = 0
                sheet.merge_range(final_row, final_col, final_row, final_col + 1, 'Total', format7)
                sheet.write(final_row, final_col + 2, round(t_in_qty, 3), format7)

            else:
                sheet.merge_range(0, 0, 2, 1,
                                  "Inventory Adjustment Report (%s - %s)" % (start_date, end_date), format0)

                sheet.write(3, 0, 'Category: {0}'.format(data['categ_name']), format1)
                sheet.write(3, 1, 'Location: {0}'.format(data['loc_name']), format3)

                sheet.write(4, 0, 'Product', format1)
                sheet.write(4, 1, 'In Qty', format3)

                row = 5
                col = 0

                for rec in data['csr']:
                    if rec['in_qty'] != 0:
                        sheet.write(row, col, rec['product_name'], format4)
                        sheet.write(row, col + 1, round(rec['in_qty'], 3), format6)
                        t_in_qty = t_in_qty + rec['in_qty']

                        row = row + 1

                final_row = row
                final_col = 0
                sheet.write(final_row, final_col, 'Total', format7)
                sheet.write(final_row, final_col + 1, round(t_in_qty, 3), format7)

        elif data['qty_type'] == 'out_qty':
            if data['loc_name'] == 'All Locations':
                sheet.merge_range(0, 0, 2, 2,
                                  "Inventory Adjustment Report (%s - %s)" % (start_date, end_date), format0)

                sheet.merge_range(3, 0, 3, 1, 'Category: {0}'.format(data['categ_name']), format1)
                sheet.write(3, 2, 'Location: {0}'.format(data['loc_name']), format3)

                sheet.write(4, 0, 'Location', format1)
                sheet.write(4, 1, 'Product', format1)
                sheet.write(4, 2, 'Out Qty', format3)

                row = 5
                col = 0

                for rec in data['csr']:
                    if rec['out_qty'] != 0:
                        sheet.write(row, col, rec['location_name'], format4)
                        sheet.write(row, col + 1, rec['product_name'], format4)
                        sheet.write(row, col + 2, round(rec['out_qty'], 3), format6)
                        t_out_qty = t_out_qty + rec['out_qty']

                        row = row + 1

                final_row = row
                final_col = 0
                sheet.merge_range(final_row, final_col, final_row, final_col + 1, 'Total', format7)
                sheet.write(final_row, final_col + 2, round(t_out_qty, 3), format7)

            else:
                sheet.merge_range(0, 0, 2, 1,
                                  "Inventory Adjustment Report (%s - %s)" % (start_date, end_date), format0)

                sheet.write(3, 0, 'Category: {0}'.format(data['categ_name']), format1)
                sheet.write(3, 1, 'Location: {0}'.format(data['loc_name']), format3)

                sheet.write(4, 0, 'Product', format1)
                sheet.write(4, 1, 'Out Qty', format3)

                row = 5
                col = 0

                for rec in data['csr']:
                    if rec['in_qty'] != 0:
                        sheet.write(row, col, rec['product_name'], format4)
                        sheet.write(row, col + 1, round(rec['out_qty'], 3), format6)
                        t_out_qty = t_out_qty + rec['out_qty']

                        row = row + 1

                final_row = row
                final_col = 0
                sheet.write(final_row, final_col, 'Total', format7)
                sheet.write(final_row, final_col + 1, round(t_out_qty, 3), format7)

        else:
            if data['loc_name'] == 'All Locations':
                sheet.merge_range(0, 0, 2, 3,
                                  "Inventory Adjustment Report (%s - %s)" % (start_date, end_date), format0)

                sheet.merge_range(3, 0, 3, 1, 'Category: {0}'.format(data['categ_name']), format1)
                sheet.merge_range(3, 2, 3, 3, 'Location: {0}'.format(data['loc_name']), format3)

                sheet.write(4, 0, 'Location', format1)
                sheet.write(4, 1, 'Product', format1)
                sheet.write(4, 2, 'In Qty', format3)
                sheet.write(4, 3, 'Out Qty', format3)

                row = 5
                col = 0

                for rec in data['csr']:
                    if rec['in_qty'] != 0 or rec['out_qty'] != 0:
                        sheet.write(row, col, rec['location_name'], format4)
                        sheet.write(row, col + 1, rec['product_name'], format4)
                        sheet.write(row, col + 2, round(rec['in_qty'], 3), format6)
                        t_in_qty = t_in_qty + rec['in_qty']
                        sheet.write(row, col + 3, round((-1) * rec['out_qty'], 3), format6)
                        t_out_qty = t_out_qty + ((-1) * rec['out_qty'])

                        row = row + 1

                final_row = row
                final_col = 0
                sheet.merge_range(final_row, final_col, final_row, final_col + 1, 'Total', format7)
                sheet.write(final_row, final_col + 2, round(t_in_qty, 3), format7)
                sheet.write(final_row, final_col + 3, round(t_out_qty, 3), format7)

            else:
                sheet.merge_range(0, 0, 2, 2,
                                  "Inventory Adjustment Report (%s - %s)" % (start_date, end_date), format0)

                sheet.merge_range(3, 0, 3, 1, 'Category: {0}'.format(data['categ_name']), format1)
                sheet.merge_range(3, 2, 3, 2, 'Location: {0}'.format(data['loc_name']), format3)

                sheet.write(4, 0, 'Product', format1)
                sheet.write(4, 1, 'In Qty', format3)
                sheet.write(4, 2, 'Out Qty', format3)

                row = 5
                col = 0

                for rec in data['csr']:
                    if rec['in_qty'] != 0 or rec['out_qty'] != 0:
                        sheet.write(row, col, rec['product_name'], format4)
                        sheet.write(row, col + 1, round(rec['in_qty'], 3), format6)
                        t_in_qty = t_in_qty + rec['in_qty']
                        sheet.write(row, col + 2, round((-1) * rec['out_qty'], 3), format6)
                        t_out_qty = t_out_qty + ((-1) * rec['out_qty'])

                        row = row + 1

                final_row = row
                final_col = 0
                sheet.write(final_row, final_col, 'Total', format7)
                sheet.write(final_row, final_col + 1, round(t_in_qty, 3), format7)
                sheet.write(final_row, final_col + 2, round(t_out_qty, 3), format7)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.encodestring(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Inventory Adjustment Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=inventory.adjustment.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def inventory_adjust_report_html(self):
        start_date = self.start_date
        end_date = self.end_date
        qty_type = self.qty_type
        category_id = self.category_id.id
        product_id = self.product_id.id
        location_id = self.location_id

        # get data from sql
        data = self.inventory_adjust_report_sql(start_date, end_date, category_id, product_id, location_id, qty_type)

        return self.env.ref('custom_stock.inventory_adjustment_report_html_id').with_context(
            landscape=False).report_action(self, data=data)

    def inventory_adjust_report_pdf(self):
        start_date = self.start_date
        end_date = self.end_date
        qty_type = self.qty_type
        category_id = self.category_id.id
        product_id = self.product_id.id
        location_id = self.location_id

        # get data from sql
        data = self.inventory_adjust_report_sql(start_date, end_date, category_id, product_id, location_id, qty_type)

        return self.env.ref('custom_stock.inventory_adjustment_report_id').with_context(
            landscape=False).report_action(self, data=data)

    def inventory_adjust_report_sql(self, start_date, end_date, category_id, product_id, location_id, qty_type):
        qty_type_filter = 'all'

        if qty_type:
            qty_type_filter = qty_type

        product_domain = [('state', '=', 'approve')]

        if category_id and not product_id:
            product_domain += [('product_tmpl_id.categ_id', 'child_of', category_id)]

        if category_id and product_id:
            product_domain += [('product_tmpl_id.categ_id', 'child_of', category_id), ('id', '=', product_id)]

        product_ids = tuple(self.env['product.product'].search(product_domain).ids)

        categ_name = ""

        if category_id:
            categ_name = self.category_id.name
        else:
            categ_name = "All Categories"

        productFilter = ""
        locationFilter = ""

        if len(product_ids) > 1:
            productFilter = "AND st_invl.product_id IN {0}".format(product_ids)
        else:
            if len(product_ids) > 1:
                productFilter = "AND st_invl.product_id IN {0}".format(product_ids)
            elif len(product_ids) == 1:
                productFilter = "AND st_invl.product_id = {0}".format(product_ids[0])
            else:
                raise ValidationError(_('No product(s) available.'))

        if location_id:
            locationFilter = "AND st_invl.location_id = %s" % location_id.id
            loc_name = self.env['stock.location'].browse(location_id.id).name
        else:
            loc_name = "All Locations"

        data_sql = """
                    SELECT sl.name AS loc_name, st_invl.product_id,
                    COALESCE(SUM(CASE
                        WHEN (st_invl.product_qty - st_invl.theoretical_qty) > 0 THEN COALESCE(st_invl.product_qty - st_invl.theoretical_qty, 0) ELSE 0
                    END),0) AS in_qty,
                    COALESCE(SUM(CASE
                        WHEN (st_invl.product_qty - st_invl.theoretical_qty) < 0 THEN COALESCE(st_invl.product_qty - st_invl.theoretical_qty, 0) ELSE 0
                    END),0) AS out_qty
                    FROM stock_inventory AS st_inv
                    JOIN stock_inventory_line AS st_invl ON st_invl.inventory_id = st_inv.id
                    LEFT JOIN stock_location sl ON sl.id=st_invl.location_id
                    WHERE st_inv.state='done' AND sl.usage='internal' AND sl.active='true' AND sl.state = 'done'
                    AND DATE(st_inv.date) BETWEEN '{0}' AND '{1}'
                    {2} {3}
                    GROUP BY sl.name, st_invl.product_id
                    ORDER BY sl.name, st_invl.product_id
                   """.format(start_date, end_date, productFilter, locationFilter)

        self.env.cr.execute(data_sql)
        data_dict = self.env.cr.dictfetchall()

        data_list = []

        for data in data_dict:
            vals = {
                'location_name': data['loc_name'],
                'product_name': self.env['product.product'].search([('id', '=', data['product_id'])], limit=1).display_name,
                'in_qty': data['in_qty'],
                'out_qty': data['out_qty']
            }
            data_list.append(vals)

        data = {
            'model': "inventory.adjustment.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'categ_name': categ_name,
            'loc_name': loc_name,
            'qty_type': qty_type_filter
        }
        return data
