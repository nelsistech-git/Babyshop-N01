from odoo import fields, models, _, api
from odoo.exceptions import ValidationError, UserError

import xlsxwriter

import base64
from io import BytesIO


class BarcodeWiseCurrentStockReport(models.TransientModel):
    _name = "barcode.wise.current.stock.report.wizard"
    _description = "Barcode wise Current Stock Report"

    file_data = fields.Binary()
    category_id = fields.Many2one('product.category', string='Product Category')
    category_ids = fields.Many2many('product.category', string='Product Category')
    product_id = fields.Many2one('product.product', string='Product', help="Main Product", domain="[('state', '=', 'approve'), ('product_tmpl_id.categ_id', 'child_of', category_id)]")
    product_ids = fields.Many2many('product.product', string='Products', help="Main Product", domain="[('state', '=', 'approve')]")
    location_id = fields.Many2one('stock.location', string='Location',
                                  domain="[('usage', '=', 'internal'), ('state', '=', 'done')]")
    vendor_id = fields.Many2one('res.partner', string="Vendor", domain="[('supplier_rank', '>', '0')]")
    report_type = fields.Selection([
        ('01', 'Location wise'),
        ('02', 'Product wise'),
    ], string='Report Type', required=True, default='01')
    sale_type = fields.Selection([
        ('01', 'Saleable'),
        ('02', 'Non Saleable')
    ], string='Sale Type')
    location_type = fields.Selection([
        ('all', "All"),
        ('ho', "Head Office"),  # Head office
        ('branch', "Branch/Site Office"),  # Branch/Site office
        ('project', "Project"),  # Project
        ('factory', "Factory"),  # Factory
        ('shop', "Shop"),  # Shop/Is Retail
        ('cdc', "CDC"),  # CDC Shop
        ('guarantee', "Guarantee"),  # Guarantee/Warranty Shop
        ('ecommerce', "E-commerce"),  # Ecommerce Shop
        ('corporate', "Corporate"),  # Corporate Shop
        ('whole_sale', "Whole Sale"),  # Whole Sale Shop
        ('defective_supp', "Defective Supplier")], string='Location Type', default='all')  # Defective Supplier Shop

    @api.onchange('location_type')
    def _onchange_location_type(self):
        if self.location_type == 'all':
            return {'location_id': None, 'domain': {'location_id': [('usage', '=', 'internal'), ('state', '=', 'done')]}}
        elif self.location_type:
            return {'location_id': None, 'domain': {'location_id': [('type', '=', self.location_type), ('usage', '=', 'internal'), ('state', '=', 'done')]}}
        else:
            return {'location_id': None, 'domain': {'location_id': [('type', '=', None)]}}

    @api.onchange('sale_type')
    def _onchange_sale_type(self):
        if self.sale_type == '01':
            return {'category_id': None, 'domain': {'category_id': [('is_saleable', '=', True)]}}
        elif self.sale_type == '02':
            return {'category_id': None, 'domain': {'category_id': [('is_saleable', '!=', True)]}}
        else:
            return {'category_id': None}

    @api.onchange('category_ids')
    def _get_product(self):
        for rec in self:
            cat_ids = [r._origin.id for r in rec.category_ids]
            if not cat_ids:
                return {'domain': {'product_ids': [('state', '=', 'approve')]}}
            else:
                return {'domain': {'product_ids': [('state', '=', 'approve'),  ('product_tmpl_id.categ_id', 'child_of', cat_ids)]}}

    def barcode_wise_current_stock_report_pdf(self):
        category_id = self.category_ids
        product_id = self.product_ids
        location_id = self.location_id
        vendor_id = self.vendor_id
        cost_context = self.env.context.get('is_without_cost')
        supplier_context = self.env.context.get('is_supplier_cost')

        if cost_context: 
            #  W/O cost
            #  get data from sql --- Barcode wise Current Stock Report without Cost
            if not (location_id or category_id or product_id or vendor_id):
                raise UserError(_('Location or Category or Product or Vendor filter required for PDF report.'))
            else:
                data = {
                    'ftr_id': self.id,
                    'cost_context': cost_context,
                    'supplier_context': supplier_context,
                }
                return self.env.ref('custom_stock.barcode_wise_current_stock_report_without_cost').with_context(
                    landscape=False).report_action(self, data=data)

        else:
            # with cost and supplier
            #  get data from sql --- Barcode wise Current Stock Report with Cost
            if not (location_id or category_id or product_id or vendor_id):
                raise UserError(_('Location or Category or Product or Vendor filter required for PDF report.'))
            else:
                data = {
                    'ftr_id': self.id,
                    'cost_context': cost_context,
                    'supplier_context': supplier_context,
                }
            return self.env.ref('custom_stock.barcode_wise_current_stock_report').with_context(
                landscape=False).report_action(self, data=data)

    def barcode_wise_current_stock_report_excel(self):
        report_type = self.report_type
        cost_context = self.env.context.get('is_without_cost')
        supplier_context = self.env.context.get('is_supplier_cost')
        file_pointer = BytesIO()
        print(cost_context)
        if cost_context: # without cost
            file_name = "Barcode wise Current Stock Report without Cost.xlsx"
            
            #  get data from sql
            data = self.get_report_sql(cost_context, supplier_context)
            workbook = xlsxwriter.Workbook(file_pointer)

            #  main header formatting
            format0 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
            format0.set_align('center')
            format0.set_border()

            #  column header formatting
            format1 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
            format1.set_align('left')
            format1.set_border()
            format2 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
            format2.set_align('center')
            format2.set_border()
            format3 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
            format3.set_align('right')
            format3.set_border()

            #  body formatting
            format4 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
            format4.set_align('left')
            format4.set_border()
            format5 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
            format5.set_align('center')
            format5.set_border()
            format6 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
            format6.set_align('right')
            format6.set_border()

            #  grand total formatting
            format7 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True})
            format7.set_border()
            format8 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
            format8.set_border()
            format9 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
            format9.set_border()

            sheet = workbook.add_worksheet('Barcode wise Current Stock Report without Cost')

            if report_type == '01':
                # location wise
                if data['loc_name'] == 'All Locations':
                    sheet.merge_range(0, 0, 1, 8, 'Barcode & Location wise Current Stock Report without Cost', format0)

                    sheet.merge_range(2, 0, 2, 3, 'Location: {0}'.format(data['loc_name']), format1)
                    sheet.merge_range(2, 4, 2, 8, 'Vendor: {0}'.format(data['vendor_name']), format3)
                    sheet.merge_range(3, 0, 3, 8, 'Category: {0}'.format(data['categ_name']), format1)

                    sheet.write(4, 0, 'Location', format1)
                    sheet.write(4, 1, 'Category Name', format1)
                    sheet.write(4, 2, 'Barcode', format2)
                    sheet.write(4, 3, 'Product Name', format1)
                    sheet.write(4, 4, 'Attribute Name', format1)
                    sheet.write(4, 5, 'UoM', format1)
                    sheet.write(4, 6, 'Quantity', format3)
                    sheet.write(4, 7, 'Sale Price', format3)
                    sheet.write(4, 8, 'Total Sale Price', format3)

                    t_quantity = 0
                    total_sales_price = 0

                    row = 5
                    col = 0

                    for rec in data['csr']:
                        product_name = rec['product_name']['en_US'] if rec['product_name'] else ''
                        sheet.write(row, col, rec['location_name'], format4)
                        sheet.write(row, col + 1, rec['categ_name'], format4)
                        sheet.write(row, col + 2, rec['barcode'], format5)
                        sheet.write(row, col + 3, rec['product_tmpl_name']['en_US'], format4)
                        sheet.write(row, col + 4, product_name, format4)
                        sheet.write(row, col + 5, rec['uom_name']['en_US'], format4)
                        sheet.write(row, col + 6, round(rec['quantity'], 3), format6)
                        t_quantity = t_quantity + rec['quantity']
                        sheet.write(row, col + 7, round(rec['sales_price'], 2), format6)

                        sale_total = round(rec['quantity'] * rec['sales_price'], 2)
                        sheet.write(row, col + 8, sale_total, format6)
                        total_sales_price = total_sales_price + sale_total

                        row = row + 1

                    final_row = row
                    final_col = 0
                    sheet.merge_range(final_row, final_col, final_row, final_col + 5, 'Total', format7)
                    sheet.write(final_row, final_col + 6, round(t_quantity, 3), format7)
                    sheet.write(final_row, final_col + 7, '', format7)
                    sheet.write(final_row, final_col + 8, round(total_sales_price, 2), format7)

                else:
                    sheet.merge_range(0, 0, 1, 7, 'Barcode & Location wise Current Stock Report without Cost', format0)

                    sheet.merge_range(2, 0, 2, 3, 'Location: {0}'.format(data['loc_name']), format1)
                    sheet.merge_range(2, 4, 2, 7, 'Vendor: {0}'.format(data['vendor_name']) , format3)
                    sheet.merge_range(3, 0, 3, 7,  'Category: {0}'.format(data['categ_name']), format1)

                    sheet.write(4, 0, 'Category Name', format1)
                    sheet.write(4, 1, 'Barcode', format2)
                    sheet.write(4, 2, 'Product Name', format1)
                    sheet.write(4, 3, 'Attribute Name', format1)
                    sheet.write(4, 4, 'UoM', format1)
                    sheet.write(4, 5, 'Quantity', format3)
                    sheet.write(4, 6, 'Sale Price', format3)
                    sheet.write(4, 7, 'Total Sale Price', format3)

                    t_quantity = 0
                    total_sales_price = 0

                    row = 5
                    col = 0

                    for rec in data['csr']:
                        sheet.write(row, col, rec['categ_name'], format4)
                        sheet.write(row, col + 1, rec['barcode'], format5)
                        sheet.write(row, col + 2, rec['product_tmpl_name']['en_US'], format4)
                        sheet.write(row, col + 3, rec['product_name'], format4)
                        sheet.write(row, col + 4, rec['uom_name']['en_US'], format4)
                        sheet.write(row, col + 5, round(rec['quantity'], 3), format6)
                        t_quantity = t_quantity + rec['quantity']
                        sheet.write(row, col + 6, round(rec['sales_price'], 2), format6)

                        sale_total = round(rec['quantity'] * rec['sales_price'], 2)
                        sheet.write(row, col + 7, sale_total, format6)
                        total_sales_price = total_sales_price + sale_total

                        row = row + 1

                    final_row = row
                    final_col = 0
                    sheet.merge_range(final_row, final_col, final_row, final_col + 4, 'Total', format7)
                    sheet.write(final_row, final_col + 5, round(t_quantity, 3), format7)
                    sheet.write(final_row, final_col + 6, '', format7)
                    sheet.write(final_row, final_col + 7, round(total_sales_price, 2), format7)

            else:
                # Product wise
                sheet.merge_range(0, 0, 1, 7, 'Barcode & Product wise Current Stock Report without Cost', format0)

                sheet.merge_range(2, 0, 2, 4, 'Location: {0}'.format(data['loc_name']), format1)
                sheet.merge_range(2, 5, 2, 7, 'Vendor: {0}'.format(data['vendor_name']), format3)
                sheet.merge_range(3, 0, 3, 7, 'Category: {0}'.format(data['categ_name']), format1)

                sheet.write(4, 0, 'Category Name', format1)
                sheet.write(4, 1, 'Barcode', format1)
                sheet.write(4, 2, 'Product Name', format1)
                sheet.write(4, 3, 'Attribute Name', format1)
                sheet.write(4, 4, 'UoM', format1)
                sheet.write(4, 5, 'Quantity', format2)
                sheet.write(4, 6, 'Sale Price', format3)
                sheet.write(4, 7, 'Total Sale Price', format3)

                t_quantity = 0
                total_sales_price = 0

                row = 5
                col = 0

                for rec in data['csr']:
                    print(rec['product_name'])
                    sheet.write(row, col, rec['categ_name'], format4)
                    sheet.write(row, col + 1, rec['barcode'], format4)
                    sheet.write(row, col + 2, rec['product_tmpl_name']['en_US'], format4)
                    sheet.write(row, col + 3, rec['product_name'], format4)
                    sheet.write(row, col + 4, rec['uom_name']['en_US'], format4)
                    sheet.write(row, col + 5, round(rec['quantity'], 3), format6)
                    t_quantity = t_quantity + rec['quantity']
                    sheet.write(row, col + 6, round(rec['sales_price'], 2), format6)
                    sale_total = round(rec['quantity'] * rec['sales_price'], 2)
                    sheet.write(row, col + 7, sale_total, format6)
                    total_sales_price = total_sales_price + sale_total

                    row = row + 1

                final_row = row
                final_col = 0
                sheet.merge_range(final_row, final_col, final_row, final_col + 4, 'Total', format7)
                sheet.write(final_row, final_col + 5, round(t_quantity, 3), format7)
                sheet.write(final_row, final_col + 6,'', format7)
                sheet.write(final_row, final_col + 7, round(total_sales_price, 2), format7)

            workbook.close()
            file_pointer.seek(0)
            file_data = base64.b64encode(file_pointer.read())
            self.write({'file_data': file_data})
            file_pointer.close()

            return {
                'name': 'Barcode wise Current Stock Report without Cost',
                'type': 'ir.actions.act_url',
                'url': '/web/content?model=barcode.wise.current.stock.report.wizard&field=file_data&id=%s&filename=%s' % (
                    self.id, file_name),
                'target': 'self',
            }

        else: 
            #  with cost- Current stock and Supplier
            file_name = "Barcode wise Current Stock Report with Cost.xlsx"
            #  get data from sql
            data = self.get_report_sql(cost_context, supplier_context)
            workbook = xlsxwriter.Workbook(file_pointer)

            #  main header formatting
            format0 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
            format0.set_align('center')
            format0.set_border()

            #  column header formatting
            format1 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
            format1.set_align('left')
            format1.set_border()
            format2 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
            format2.set_align('center')
            format2.set_border()
            format3 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
            format3.set_align('right')
            format3.set_border()

            #  body formatting
            format4 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
            format4.set_align('left')
            format4.set_border()
            format5 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
            format5.set_align('center')
            format5.set_border()
            format6 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
            format6.set_align('right')
            format6.set_border()

            #  grand total formatting
            format7 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True})
            format7.set_border()
            format8 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
            format8.set_border()
            format9 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
            format9.set_border()

            sheet = workbook.add_worksheet('Barcode wise Current Stock Report with Cost')

            if report_type == '01':
                # location wise
                if data['loc_name'] == 'All Locations':
                    sheet.merge_range(0, 0, 1, 12, 'Barcode & Location wise Current Stock Report with Cost', format0)

                    sheet.merge_range(2, 0, 2, 5,'Location: {0}'.format(data['loc_name']), format1)
                    sheet.merge_range(2, 6, 2, 12, 'Vendor: {0}'.format(data['vendor_name']), format3)
                    sheet.merge_range(3, 0, 3, 12, 'Category: {0}'.format(data['categ_name']), format1)

                    sheet.write(4, 0, 'Location', format1)
                    sheet.write(4, 1, 'Category Name', format1)
                    sheet.write(4, 2, 'Barcode', format2)
                    sheet.write(4, 3, 'Product Name', format1)
                    sheet.write(4, 4, 'Attribute Name', format1)
                    sheet.write(4, 5, 'UoM', format1)
                    sheet.write(4, 6, 'Quantity', format3)
                    sheet.write(4, 7, 'Cost Price', format3)
                    sheet.write(4, 8, 'Other Cost Price', format3)
                    sheet.write(4, 9, 'Total Cost', format3)
                    sheet.write(4, 10, 'Sale Price', format3)
                    sheet.write(4, 11, 'Total Sale Price', format3)
                    sheet.write(4, 12, 'Vendor', format1)

                    t_quantity = 0
                    t_net_value = 0
                    total_sales_price = 0

                    row = 5
                    col = 0
                    for rec in data['csr']:
                        product_obj = self.env['product.product'].sudo().search([('id', '=', rec['product_id'])], limit=1)
                        cost = round(product_obj.standard_price, 4)
                        other_cost = round(product_obj.other_cost, 4)
                        vendor_info = product_obj.vendor_id.name or None

                        sheet.write(row, col, rec['location_name'], format4)
                        sheet.write(row, col + 1, rec['categ_name'], format4)
                        sheet.write(row, col + 2, rec['barcode'], format5)
                        product_tmpl_name = rec['product_tmpl_name']['en_US']
                        product_name = rec['product_name']['en_US']
                        uom_name = rec['uom_name']['en_US']
                        sheet.write(row, col + 3, product_tmpl_name, format4)
                        sheet.write(row, col + 4, product_name, format4)
                        sheet.write(row, col + 5, uom_name, format4)
                        sheet.write(row, col + 6, round(rec['quantity'], 3), format6)
                        t_quantity = t_quantity + rec['quantity']
                        sheet.write(row, col + 7, cost, format6)
                        sheet.write(row, col + 8, other_cost, format6)
                        net_cost = round(rec['net_value'], 4)
                        sheet.write(row, col + 9, net_cost, format6)
                        t_net_value = t_net_value + net_cost

                        sheet.write(row, col + 10, round(rec['sales_price'], 2), format6)
                        sale_total = round(rec['quantity'] * rec['sales_price'], 2)
                        sheet.write(row, col + 11, sale_total, format6)
                        total_sales_price = total_sales_price + sale_total
                        sheet.write(row, col + 12, vendor_info, format6)

                        row = row + 1

                    final_row = row
                    final_col = 0
                    sheet.merge_range(final_row, final_col, final_row, final_col + 5, 'Total', format7)
                    sheet.write(final_row, final_col + 6, round(t_quantity, 3), format7)
                    sheet.write(final_row, final_col + 7, '', format7)
                    sheet.write(final_row, final_col + 8, '', format7)
                    sheet.write(final_row, final_col + 9, round(t_net_value, 2), format7)
                    sheet.write(final_row, final_col + 10, '', format7)
                    sheet.write(final_row, final_col + 11, round(total_sales_price, 2), format7)
                    sheet.write(final_row, final_col + 12, '', format4)

                else:
                    sheet.merge_range(0, 0, 1, 11, 'Barcode & Location wise Current Stock Report with Cost', format0)

                    sheet.merge_range(2, 0, 2, 4, 'Location: {0}'.format(data['loc_name']), format1)
                    sheet.merge_range(2, 5, 2, 11, 'Vendor: {0}'.format(data['vendor_name']), format3)
                    sheet.merge_range(3, 0, 3, 11, 'Category: {0}'.format(data['categ_name']), format1)

                    sheet.write(4, 0, 'Category Name', format1)
                    sheet.write(4, 1, 'Barcode', format2)
                    sheet.write(4, 2, 'Product Name', format1)
                    sheet.write(4, 3, 'Attribute Name', format1)
                    sheet.write(4, 4, 'UoM', format1)
                    sheet.write(4, 5, 'Quantity', format3)
                    sheet.write(4, 6, 'Cost Price', format3)
                    sheet.write(4, 7, 'Other Cost Price', format3)
                    sheet.write(4, 8, 'Total Cost', format3)
                    sheet.write(4, 9, 'Sale Price', format3)
                    sheet.write(4, 10, 'Total Sale Price', format3)
                    sheet.write(4, 11, 'Vendor', format1)

                    t_quantity = 0
                    t_net_value = 0
                    total_sales_price = 0

                    row = 5
                    col = 0

                    for rec in data['csr']:
                        product_obj = self.env['product.product'].sudo().search([('id', '=', rec['product_id'])], limit=1)
                        cost = round(product_obj.standard_price, 4)
                        other_cost = round(product_obj.other_cost, 4)
                        vendor_info = product_obj.vendor_id.name or None

                        product_tmpl_name = rec['product_tmpl_name']['en_US']
                        product_name = rec['product_name']
                        uom_name = rec['uom_name']['en_US']

                        sheet.write(row, col, rec['categ_name'], format4)
                        sheet.write(row, col + 1, rec['barcode'], format5)
                        sheet.write(row, col + 2, product_tmpl_name, format4)
                        sheet.write(row, col + 3, product_name, format4)
                        sheet.write(row, col + 4, uom_name, format4)
                        sheet.write(row, col + 5, round(rec['quantity'], 3), format6)
                        t_quantity = t_quantity + rec['quantity']
                        sheet.write(row, col + 6, cost, format6)
                        sheet.write(row, col + 7, other_cost, format6)

                        net_cost = round(rec['net_value'], 4)
                        sheet.write(row, col + 8, net_cost, format6)
                        t_net_value = t_net_value + net_cost

                        sheet.write(row, col + 9, round(rec['sales_price'], 2), format6)
                        sale_total = round(rec['quantity'] * rec['sales_price'], 2)
                        sheet.write(row, col + 10, sale_total, format6)
                        total_sales_price = total_sales_price + sale_total
                        sheet.write(row, col + 11, vendor_info, format4)

                        row = row + 1

                    final_row = row
                    final_col = 0
                    sheet.merge_range(final_row, final_col, final_row, final_col + 4, 'Total', format7)
                    sheet.write(final_row, final_col + 5, round(t_quantity, 3), format7)
                    sheet.write(final_row, final_col + 6, '', format7)
                    sheet.write(final_row, final_col + 7, '', format7)
                    sheet.write(final_row, final_col + 8, round(t_net_value, 2), format7)
                    sheet.write(final_row, final_col + 9, '', format7)
                    sheet.write(final_row, final_col + 10, round(total_sales_price, 2), format7)
                    sheet.write(final_row, final_col + 11, '', format7)

            else:
                print('222------',data['csr'])
                #  Product wise
                sheet.merge_range(0, 0, 1, 11, 'Barcode & Product wise Current Stock Report with Cost', format0)
                sheet.merge_range(2, 0, 2, 4, 'Location: {0}'.format(data['loc_name']), format1)
                sheet.merge_range(2, 5, 2, 11, 'Vendor: {0}'.format(data['vendor_name']), format3)
                sheet.merge_range(3, 0, 3, 11, 'Category: {0}'.format(data['categ_name']), format1)

                sheet.write(4, 0, 'Category Name', format1)
                sheet.write(4, 1, 'Barcode', format1)
                sheet.write(4, 2, 'Product Name', format1)
                sheet.write(4, 3, 'Attribute Name', format1)
                sheet.write(4, 4, 'UoM', format1)
                sheet.write(4, 5, 'Quantity', format2)
                sheet.write(4, 6, 'Cost Price', format3)
                sheet.write(4, 7, 'Other Cost Price', format3)
                sheet.write(4, 8, 'Total Cost', format3)
                sheet.write(4, 9, 'Sale Price', format3)
                sheet.write(4, 10, 'Total Sale Price', format3)
                sheet.write(4, 11, 'Vendor', format1)

                t_quantity = 0
                t_net_value = 0
                total_sales_price = 0

                row = 5
                col = 0
                for rec in data['csr']:
                    product_obj = self.env['product.product'].sudo().search([('id', '=', rec['product_id'])], limit=1)
                    cost= round(product_obj.standard_price, 4)
                    other_cost = round(product_obj.other_cost, 4)
                    vendor_info = product_obj.vendor_id.name or None
                    sheet.write(row, col, rec['categ_name'], format4)
                    sheet.write(row, col + 1, rec['barcode'], format4)
                    sheet.write(row, col + 2, rec['product_tmpl_name']['en_US'], format4)
                    sheet.write(row, col + 3, rec['product_name'], format4)
                    sheet.write(row, col + 4, rec['uom_name']['en_US'], format4)
                    sheet.write(row, col + 5, round(rec['quantity'], 3), format6)
                    t_quantity = t_quantity + rec['quantity']
                    sheet.write(row, col + 6, cost, format6)
                    sheet.write(row, col + 7, other_cost, format6)

                    net_cost = round(rec['net_value'], 4)

                    sheet.write(row, col + 8, net_cost, format6)
                    t_net_value = t_net_value + net_cost

                    sheet.write(row, col + 9, round(rec['sales_price'], 2), format6)
                    sale_total = round(rec['quantity'] * rec['sales_price'], 2)
                    sheet.write(row, col + 10, sale_total, format6)
                    total_sales_price = total_sales_price + sale_total
                    sheet.write(row, col + 11, vendor_info, format4)

                    row = row + 1

                final_row = row
                final_col = 0
                sheet.merge_range(final_row, final_col, final_row, final_col + 4, 'Total', format7)
                sheet.write(final_row, final_col + 5, round(t_quantity, 3), format7)
                sheet.write(final_row, final_col + 6, '', format7)
                sheet.write(final_row, final_col + 7, '', format7)
                sheet.write(final_row, final_col + 8, round(t_net_value, 2), format7)
                sheet.write(final_row, final_col + 9, '', format7)
                sheet.write(final_row, final_col + 10, round(total_sales_price, 2), format7)
                sheet.write(final_row, final_col + 11, '', format7)

            workbook.close()
            file_pointer.seek(0)
            file_data = base64.b64encode(file_pointer.read())
            self.write({'file_data': file_data})
            file_pointer.close()

            return {
                'name': 'Barcode wise Current Stock Report with Cost',
                'type': 'ir.actions.act_url',
                'url': '/web/content?model=barcode.wise.current.stock.report.wizard&field=file_data&id=%s&filename=%s' % (
                    self.id, file_name),
                'target': 'self',
            }


    def get_report_sql(self, cost_context, supplier_context):
        category_id = self.category_ids
        product_id = self.product_ids
        location_id = self.location_id
        report_type = self.report_type
        location_type = self.location_type
        vendor_id = self.vendor_id
        sale_type = self.sale_type

        categoryFilter = ""
        categ_name = ""
        vendor_name = "ALL"
        productFilter = ""
        locationFilter = ""
        locationTypeFilter = ""
        vendorFilter = ""

        # -------------
        categ_id_list=[]
        if category_id:
            categ_ids = category_id.ids
            for cat_id in categ_ids:
                categ_rows = self.env['product.category'].sudo().search(['|', ('id', '=', cat_id), ('parent_id', 'child_of', cat_id)]).ids
                for cat_rec in categ_rows:
                    categ_id_list.append(cat_rec)

            categ_id_list = list(set(categ_id_list))
            if len(categ_id_list) == 1:
                categoryFilter = "AND pt.categ_id = {0}".format(categ_id_list[0])
            elif len(categ_id_list) > 1:
                categoryFilter = "AND pt.categ_id IN {0}".format(tuple(categ_id_list))

            for r in category_id:
                categ_name += r.name if not categ_name else ', ' + r.name
        else:
            categ_name = "All Categories"
            if sale_type == '01':
                categ_name = "Saleable Categories"

                categ_rows = self.env['product.category'].sudo().search([('is_saleable', '=', True)]).ids
                for cat_rec in categ_rows:
                    categ_id_list.append(cat_rec)

                categ_id_list = list(set(categ_id_list))
                if len(categ_id_list) == 1:
                    categoryFilter = "AND pt.categ_id = {0}".format(categ_id_list[0])
                elif len(categ_id_list) > 1:
                    categoryFilter = "AND pt.categ_id IN {0}".format(tuple(categ_id_list))

            elif sale_type == '02':
                categ_name = "Non-Saleable Categories"
                categ_rows = self.env['product.category'].sudo().search([('is_saleable', '=', False)]).ids
                for cat_rec in categ_rows:
                    categ_id_list.append(cat_rec)

                categ_id_list = list(set(categ_id_list))
                if len(categ_id_list) == 1:
                    categoryFilter = "AND pt.categ_id = {0}".format(categ_id_list[0])
                elif len(categ_id_list) > 1:
                    categoryFilter = "AND pt.categ_id IN {0}".format(tuple(categ_id_list))

        #  -------------
        if product_id:
            product_ids = product_id.ids
            if len(product_ids) == 1:
                productFilter = "AND sq.product_id = {0}".format(product_ids[0])
            elif len(product_ids) > 1:
                productFilter = "AND sq.product_id IN {0}".format(tuple(product_ids))
        #  -------------
        if vendor_id:
            vendorFilter = "AND pt.vendor_id = %s" % vendor_id.id
            vendor_name = vendor_id.name

        #  -------------
        if location_id:
            locationFilter = "AND sq.location_id = %s" % location_id.id
            loc_name = self.env['stock.location'].browse(location_id.id).name
        else:
            loc_name = "All Locations"

        if location_type != 'all':
            locationTypeFilter = "AND sl.type = '%s'" % location_type

        if report_type == '01':
            # location wise
            loc_summary_sql = """
                            SELECT sl.name AS location_name,
                            pt.categ_id,
                            pc.complete_name AS categ_name,
                            sq.product_id,
                            pt.product_code AS product_code,
                            pp.barcode,
                            pt.name AS product_tmpl_name,
                            pt.name AS product_name,
                            uom.name AS uom_name,
                            pt.list_price as sales_price,
                            0 as cost,
                            '' as supplier_name,
                            
                            COALESCE(SUM(sq.quantity), 0) AS quantity,
                            COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, 
                            COALESCE(SUM(sq.net_value), 0) AS net_value
                            FROM stock_quant sq
                            JOIN stock_location sl ON sl.id=sq.location_id
                            JOIN product_product pp ON pp.id=sq.product_id
                            JOIN product_template pt ON pt.id=pp.product_tmpl_id
                            JOIN product_category pc ON pc.id = pt.categ_id
                            JOIN uom_uom uom ON uom.id = pt.uom_id
                            --LEFT JOIN product_attribute_value_product_product_rel pavr  ON sq.product_id = pavr.product_product_id 
                            --LEFT JOIN product_attribute_value pav ON pavr.product_attribute_value_id = pav.id 
                                
                            WHERE sl.usage='internal'  AND sl.active='True' AND sl.state = 'done' AND pt.active = 'True' AND pt.state = 'approve'
                            {0} {1} {2} {3} {4}
                            GROUP BY sl.name, pt.categ_id, pc.complete_name, uom.name, sq.product_id, pt.name, pt.product_code, pp.barcode, pt.list_price
                            ORDER BY pt.name, sl.name
                            """.format(productFilter, locationFilter, locationTypeFilter, vendorFilter, categoryFilter)
            self.env.cr.execute(loc_summary_sql)
            data_list = self.env.cr.dictfetchall()

        else:
            # Product wise
            product_summary_sql = """
                    SELECT pt.categ_id,
                    pc.complete_name AS categ_name,
                    sq.product_id,
                    pt.product_code AS product_code,
                    pp.barcode,
                    pt.name AS product_tmpl_name,
                    --pt.name AS product_name,
                    uom.name AS uom_name,
                    pt.list_price as sales_price,
                    0 as cost,
                    CONCAT(pb.name,' ',ps.name,' ',ptc.name,' ') as product_name,
                    '' as supplier_name,
                    
                    COALESCE(SUM(sq.quantity), 0) AS quantity,
                    COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, 
                    COALESCE(SUM(sq.net_value), 0) AS net_value
                    FROM stock_quant sq
                    JOIN stock_location sl ON sl.id=sq.location_id
                    JOIN product_product pp ON pp.id=sq.product_id
                    JOIN product_template pt ON pt.id=pp.product_tmpl_id
                    JOIN product_category pc ON pc.id = pt.categ_id
                    JOIN uom_uom uom ON uom.id = pt.uom_id
                    LEFT JOIN product_brand pb on pt.brand = pb.id
                    LEFT JOIN product_style ps on pt.style_id = ps.id
                    LEFT JOIN product_color ptc on pt.color_id = ptc.id
                    WHERE sl.usage='internal' AND sl.active='True' AND sl.state = 'done' AND pt.active = 'True' AND pt.state = 'approve'
                    {0} {1} {2} {3} {4}
                    GROUP BY pt.categ_id, pc.complete_name, uom.name, sq.product_id, pt.name, pt.product_code, pp.barcode, pt.list_price,pb.name,ps.name,ptc.name
                    ORDER BY pc.complete_name, pt.name
                    """.format(productFilter, locationFilter, locationTypeFilter, vendorFilter, categoryFilter)

            self.env.cr.execute(product_summary_sql)
            data_list = self.env.cr.dictfetchall()

        data = {
            'model': "barcode.wise.current.stock.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'categ_name': categ_name,
            'loc_name': loc_name,
            'vendor_name': vendor_name,
            'cost_context': cost_context,
            'supplier_context': supplier_context
        }
        return data

    def old_get_report_sql(self, category_id, product_id, location_id, report_type, location_type, cost_context,
                       supplier_context, vendor_id):
        product_domain = [('state', '=', 'approve')]
        if category_id:
            product_domain.append(('product_tmpl_id.categ_id', 'child_of', category_id.ids))
        if product_id:
            product_domain.append(('id', 'in', product_id.ids))
        product_ids = tuple(self.env['product.product'].search(product_domain).ids)
        categ_name = ""

        if category_id:
            for r in category_id:
                categ_name += r.name if not categ_name else ', ' + r.name
        else:
            categ_name = "All Categories"

        locationFilter = ""
        locationTypeFilter = ""
        vendorFilter = ""

        if len(product_ids) > 1:
            productFilter = "AND sq.product_id IN {0}".format(product_ids)
        else:
            if len(product_ids) > 1:
                productFilter = "AND sq.product_id IN {0}".format(product_ids)
            elif len(product_ids) == 1:
                productFilter = "AND sq.product_id = {0}".format(product_ids[0])
            else:
                raise ValidationError(_('No product(s) available.'))

        if vendor_id:
            vendorFilter = "AND pt.vendor_id = %s" % vendor_id.id

        if location_id:
            locationFilter = "AND sq.location_id = %s" % location_id.id
            loc_name = self.env['stock.location'].browse(location_id.id).name
        else:
            loc_name = "All Locations"

        if location_type != 'all':
            locationTypeFilter = "AND sl.type = '%s'" % location_type

        data_list = []

        if report_type == '01':
            loc_summary_sql = """
                            SELECT main_tbl.product_id, main_tbl.loc_name, pc.name AS categ_name, main_tbl.product_code, main_tbl.barcode, main_tbl.product_name, uom.name AS uom_name, COALESCE(SUM(quantity), 0) AS quantity,
                            COALESCE(SUM(total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(net_value), 0) AS net_value
                            FROM (
                                SELECT pt.categ_id, sq.product_id, sl.name AS loc_name, pt.product_code AS product_code, pp.barcode, pt.name AS product_name, pt.uom_id, COALESCE(SUM(sq.quantity), 0) AS quantity, 
                                COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(sq.net_value), 0) AS net_value
                                FROM stock_quant sq
                                LEFT JOIN product_product pp ON pp.id=sq.product_id
                                LEFT JOIN product_template pt ON pt.id=pp.product_tmpl_id
                                LEFT JOIN stock_location sl ON sl.id=sq.location_id
                                WHERE sl.usage='internal'  AND sl.active='True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                             	{0} {1} {2} {3}
                                GROUP BY sl.name, sq.product_id, pt.name, pt.product_code, pp.barcode, pt.uom_id, pt.categ_id
                                ORDER BY pt.name, sl.name
                            ) main_tbl
                            LEFT JOIN product_category pc ON pc.id = main_tbl.categ_id
                            LEFT JOIN uom_uom uom ON uom.id = main_tbl.uom_id
                            GROUP BY main_tbl.loc_name, pc.name, main_tbl.product_id, main_tbl.product_name, uom.name, main_tbl.product_code, main_tbl.barcode
                            ORDER BY main_tbl.product_name, main_tbl.loc_name
                            """.format(productFilter, locationFilter, locationTypeFilter, vendorFilter)
            self.env.cr.execute(loc_summary_sql)
            loc_summary_dict = self.env.cr.dictfetchall()

            for data in loc_summary_dict:
                product_obj = self.env['product.product'].sudo().search([('id', '=', data['product_id'])], limit=1)
                vals = {
                    'categ_name': product_obj.categ_id.display_name,
                    'location_name': data['loc_name'],
                    'product_tmpl_name': data['product_name'],
                    'product_code': data['product_code'],
                    'barcode': data['barcode'],
                    'product_name': product_obj.name,
                    'uom_name': data['uom_name'],
                    'quantity': data['quantity'],
                    'total_cost_rate': data['total_cost_rate'],
                    'sales_price': product_obj.lst_price,
                    'cost': product_obj.standard_price,
                    'net_value': data['net_value'],
                    'supplier_name': product_obj.vendor_id.name or None,
                }
                data_list.append(vals)

        else:
            product_summary_sql = """
                                SELECT main_tbl.product_id,main_tbl.brand,main_tbl.style,main_tbl.color, pc.name AS categ_name, main_tbl.product_code, main_tbl.barcode, main_tbl.product_name,CONCAT(main_tbl.brand,' ',main_tbl.style,' ',main_tbl.color,' ') as product_info, main_tbl.brand, main_tbl.style, main_tbl.color, uom.name AS uom_name,
                                COALESCE(SUM(quantity), 0) AS quantity,
                                COALESCE(SUM(total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(net_value), 0) AS net_value
                                FROM (
                                    SELECT pt.categ_id, sq.product_id, pt.product_code AS product_code, pp.barcode, pt.name AS product_name,pb.name as brand, ps.name as style, pc.name as color, pt.uom_id, COALESCE(SUM(sq.quantity), 0) AS quantity, 
                                    COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(sq.net_value), 0) AS net_value
                                    FROM stock_quant sq
                                    LEFT JOIN product_product pp ON pp.id=sq.product_id
                                    LEFT JOIN product_template pt ON pt.id=pp.product_tmpl_id
									Left join product_brand pb on pt.brand = pb.id
									Left join product_style ps on pt.style_id = ps.id
									Left join product_color pc on pt.color_id = pc.id
                                    LEFT JOIN stock_location sl ON sl.id=sq.location_id
                                    WHERE sl.usage='internal'  AND sl.active='True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                                    {0} {1}
                                    GROUP BY sq.product_id, pt.name, pt.product_code, pp.barcode, pb.name, ps.name, pc.name,pt.uom_id, pt.categ_id
                                    ORDER BY pt.name
                                ) main_tbl
                                LEFT JOIN product_category pc ON pc.id = main_tbl.categ_id
                                LEFT JOIN uom_uom uom ON uom.id = main_tbl.uom_id
                                GROUP BY main_tbl.product_id, main_tbl.product_name, uom.name, pc.name, main_tbl.product_code, main_tbl.barcode, main_tbl.brand,main_tbl.style,main_tbl.color
                                ORDER BY pc.name, main_tbl.product_name

                            """.format(productFilter, vendorFilter)
            self.env.cr.execute(product_summary_sql)
            product_summary_dict = self.env.cr.dictfetchall()

            for data in product_summary_dict:
                product_obj = self.env['product.product'].sudo().search([('id', '=', data['product_id'])], limit=1)
                vals = {
                    'categ_name': product_obj.categ_id.display_name,
                    'product_tmpl_name': data['product_name'],
                    'product_code': data['product_code'],
                    'barcode': data['barcode'],
                    'product_name': data['product_info'],
                    'uom_name': data['uom_name'],
                    'quantity': data['quantity'],
                    'total_cost_rate': data['total_cost_rate'],
                    'sales_price': product_obj.lst_price,
                    'cost': product_obj.standard_price,
                    'net_value': data['net_value'],
                    'supplier_name': product_obj.vendor_id.name or None,
                }
                data_list.append(vals)

        data = {
            'model': "barcode.wise.current.stock.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'categ_name': categ_name,
            'loc_name': loc_name,
            'cost_context': cost_context,
            'supplier_context': supplier_context
        }
        return data



