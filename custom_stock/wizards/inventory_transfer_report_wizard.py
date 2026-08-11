from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
from datetime import datetime

import xlsxwriter

import base64
from io import BytesIO


class InventoryTransferReportWizard(models.TransientModel):
    _name = "inventory.transfer.report.wizard"
    _description = "Inventory Transfer Report"

    file_data = fields.Binary('Inventory Transfer Report')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date', default=fields.Date.context_today)
    transfer_number = fields.Char()
    category_id = fields.Many2one('product.category', string='Product Category')
    product_id = fields.Many2one('product.product', string='Product', help="Main Product",
                                 domain="[('state', '=', 'approve'), ('product_tmpl_id.categ_id', 'child_of', category_id)]")
    src_location_id = fields.Many2one('stock.location', string='Source Location',
                                  domain="[('usage', '=', 'internal'), ('state', '=', 'done')]")
    dest_location_id = fields.Many2one('stock.location', string='Destination Location',
                                  domain="[('usage', '=', 'internal'), ('state', '=', 'done')]")

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('Start date cannot be greater than the end date.'))

    def inventory_transfer_report_pdf(self):
        start_date = self.start_date
        end_date = self.end_date
        category_id = self.category_id
        product_id = self.product_id
        src_location_id = self.src_location_id
        dest_location_id = self.dest_location_id

        # get data from sql
        data = self.inventory_transfer_report_sql(start_date, end_date, category_id, product_id, src_location_id, dest_location_id)

        return self.env.ref('custom_stock.inventory_transfer_report_tmpl').with_context(
            landscape=False).report_action(self, data=data)

    def inventory_transfer_report_excel(self):
        start_date = self.start_date
        end_date = self.end_date
        category_id = self.category_id
        product_id = self.product_id
        src_location_id = self.src_location_id
        dest_location_id = self.dest_location_id

        # get data from sql
        data = self.inventory_transfer_report_sql(start_date, end_date, category_id, product_id, src_location_id, dest_location_id)

        start_date = datetime.strptime(str(start_date), '%Y-%m-%d').strftime('%d-%b-%Y')
        end_date = datetime.strptime(str(end_date), '%Y-%m-%d').strftime('%d-%b-%Y')

        file_name = "Inventory Transfer Report.xlsx"
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

        sheet = workbook.add_worksheet('Inventory Transfer Report')

        # table heading
        head_row = 5
        head_col = 0

        sheet.write(head_row, head_col, 'Sl. No.', format2)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Category Name', format1)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Barcode', format2)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Product Name', format1)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'UoM', format1)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Source Location', format1)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Destination Location', format1)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Qty.', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Sale Price', format3)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Total Sale Price', format3)

        # main heading
        sheet.merge_range(0, 0, 1, head_col, 'Inventory Transfer Report', format0)

        sheet.merge_range(2, 0, 2, int(head_col/2), 'Start Date: {0}'.format(start_date), format1)
        sheet.merge_range(3, 0, 3, int(head_col/2), 'End Date: {0}'.format(end_date), format1)
        sheet.merge_range(4, 0, 4, int(head_col/2), 'Transfer Number: {0}'.format(data['transfer_number']), format1)
        sheet.merge_range(2, int(head_col/2) + 1, 2, head_col, 'Source Location: {0}'.format(data['src_loc_name']), format3)
        sheet.merge_range(3, int(head_col/2) + 1, 3, head_col, 'Destination Location: {0}'.format(data['dest_loc_name']), format3)
        sheet.merge_range(4, int(head_col/2) + 1, 4, head_col, 'Category: {0}'.format(data['categ_name']), format3)

        sl_no = 1
        t_quantity = 0
        t_sales_price = 0
        total_sales_price = 0

        # table body
        row = head_row + 1
        col = 0

        for rec in data['csr']:
            sheet.write(row, col, sl_no, format5)
            col = col + 1
            sheet.write(row, col, rec['categ_name'], format4)
            col = col + 1
            sheet.write(row, col, rec['barcode'], format5)
            col = col + 1
            sheet.write(row, col, rec['product'], format4)
            col = col + 1
            sheet.write(row, col, rec['uom'], format4)
            col = col + 1
            sheet.write(row, col, rec['src_location'], format4)
            col = col + 1
            sheet.write(row, col, rec['dest_location'], format4)
            col = col + 1
            sheet.write(row, col, round(rec['qty'], 3), format6)
            t_quantity = t_quantity + rec['qty']
            col = col + 1
            sheet.write(row, col, round(rec['sale_price'], 2), format6)
            t_sales_price = t_sales_price + rec['sale_price']
            col = col + 1
            sheet.write(row, col, round(rec['total_sales'], 2), format6)
            total_sales_price = total_sales_price + rec['total_sales']

            sl_no = sl_no + 1
            row = row + 1
            col = 0

        # total section
        final_row = row
        final_col = 0
        sheet.merge_range(final_row, final_col, final_row, final_col + 6, 'Total', format7)
        final_col = final_col + 7
        sheet.write(final_row, final_col, round(t_quantity, 3), format7)
        final_col = final_col + 1
        sheet.write(final_row, final_col, round(t_sales_price, 2), format7)
        final_col = final_col + 1
        sheet.write(final_row, final_col, round(total_sales_price, 2), format7)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Inventory Transfer Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=inventory.transfer.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def inventory_transfer_report_sql(self, start_date, end_date, category_id, product_id, src_location_id, dest_location_id):
        transfer_number = ""

        product_domain = [('state', '=', 'approve')]
        domain = [('picking_id.state', '=', 'done'), ('picking_id.picking_type_id.code', '=', 'internal'), ('date', '>=', start_date), ('date', '<=', end_date)]

        if category_id:
            product_domain.append(('product_tmpl_id.categ_id', 'child_of', category_id.id))
            categ_name = category_id.name
        else:
            categ_name = "All"
        if product_id:
            product_domain.append(('id', '=', product_id.id))
        if src_location_id:
            domain = domain + [('location_id', '=', src_location_id.id)]
            src_loc_name = src_location_id.name
        else:
            src_loc_name = "All"
        if dest_location_id:
            domain = domain + [('location_dest_id', '=', dest_location_id.id)]
            dest_loc_name = dest_location_id.name
        else:
            dest_loc_name = "All"
            
        if self.transfer_number:
            domain = domain + [('picking_id.name', '=', self.transfer_number)]
            transfer_number = self.transfer_number

        product_ids = tuple(self.env['product.product'].search(product_domain).ids)

        if len(product_ids) > 1:
            domain = domain + [('product_id', 'in', product_ids)]
        elif len(product_ids) == 1:
            domain = domain + [('product_id', '=', product_ids[0])]
        else:
            domain = []

        data_list = []

        stock_obj = self.env['stock.move'].search(domain)

        for data in stock_obj:
            vals = {
                'categ_name': data.product_id.categ_id.name,
                'barcode': data.product_id.barcode,
                'product': data.product_id.name,
                'uom': data.product_id.uom_id.name,
                'src_location': data.picking_id.location_id.name,
                'dest_location': data.picking_id.location_dest_id.name,
                'qty': data.quantity,
                'sale_price': data.product_id.list_price,
                'total_sales': data.quantity * data.product_id.list_price,
            }
            data_list.append(vals)

        data = {
            'model': "inventory.transfer.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'categ_name': categ_name,
            'src_loc_name': src_loc_name,
            'dest_loc_name': dest_loc_name,
            'transfer_number': transfer_number
        }
        return data




