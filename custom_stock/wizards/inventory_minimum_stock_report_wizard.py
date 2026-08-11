from odoo import fields, models, _
from datetime import datetime
import xlsxwriter

import base64
from io import BytesIO


def get_years():
    year_list = []
    crn_year = datetime.now().year
    for i in range(2021, crn_year + 10):
        year_list.append((str(i), str(i)))
    return year_list


class InventoryReserveStockReportWizard(models.TransientModel):
    _name = "inventory.minimum.stock.report.wizard"
    _description = "Inventory Minimum Stock Report Wizard"

    file_data = fields.Binary('Inventory Minimum Stock Report')
    product_id = fields.Many2one('product.product', string='Product', help="Product",
                                 domain="[('state', '=', 'approve')]")
    location_id = fields.Many2one('stock.location', string='Location',
                                  domain="[('usage', '=', 'internal'), ('state', '=', 'done')]")

    def inventory_minimum_stock_report_excel(self):

        product_id = self.product_id
        location_id = self.location_id

        # get data from sql
        data = self.inventory_minimum_stock_report_sql(product_id, location_id)

        file_name = "Inventory Minimum Stock Report.xlsx"
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
        format10 = workbook.add_format({'font_size': 10, 'align': 'center', 'font_color': 'red'})
        format10.set_border()

        sheet = workbook.add_worksheet('Inventory Minimum Stock Report')

        sheet.merge_range(0, 0, 1, 6, "Inventory Minimum Stock Report", format0)

        sheet.merge_range(2, 0, 2, 1, 'Location: {0}'.format(data['locationName']), format3)
        sheet.merge_range(2, 2, 2, 6, 'Product: {0}'.format(data['productName']), format3)

        sheet.write(3, 0, 'Sl.', format2)
        sheet.write(3, 1, 'Category', format1)
        sheet.write(3, 2, 'Product', format1)
        sheet.write(3, 3, 'UOM', format1)
        sheet.write(3, 4, 'On Hand Stock', format1)
        sheet.write(3, 5, 'Minimum Qty.', format2)
        sheet.write(3, 6, 'Diff.', format2)

        row = 4
        col = 0
        sl_no = 1

        for line in data['csr']:
            row_style = format5
            if line['diff'] < 0:
                row_style = format10

            sheet.write(row, col, sl_no, row_style)
            col = col + 1
            sheet.write(row, col, line['category'], row_style)
            col = col + 1
            sheet.write(row, col, line['product'], row_style)
            col = col + 1
            sheet.write(row, col, line['uom_name'], row_style)
            col = col + 1
            sheet.write(row, col, line['on_hand_stock'], row_style)
            col = col + 1
            sheet.write(row, col, line['minimum_stock'], row_style)
            col = col + 1
            sheet.write(row, col, line['diff'], row_style)

            row = row + 1
            col = 0
            sl_no = sl_no + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Inventory Minimum Stock Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=inventory.minimum.stock.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def inventory_minimum_stock_report_pdf(self):
        product_id = self.product_id
        location_id = self.location_id

        # get data from sql
        data = self.inventory_minimum_stock_report_sql(product_id, location_id)

        return self.env.ref(
            'custom_stock.inventory_minimum_stock_report_tmpl').with_context(landscape=False).report_action(self, data=data)

    def inventory_minimum_stock_report_sql(self, product_id, location_id):
        productFilter = ""
        locationFilter = ""
        locationName = "All"
        productName = "All"

        if product_id:
            productFilter = "AND pp.id = '{0}'".format(product_id.id)
            productName = product_id.name

        if location_id:
            locationFilter = "AND stq.location_id = {0}".format(location_id.id)
            locationName = location_id.name

        # if category_id and not product_id:
        #     product_domain += [('product_tmpl_id.categ_id', 'child_of', category_id)]

        data_sql = """                    
                    SELECT tbl1.product_name AS product, tbl1.uom_name AS uom_name, tbl1.cat_name AS category, COALESCE(SUM(tbl2.on_hand_stock), 0) AS on_hand_stock, COALESCE(SUM(tbl1.minimum_stock), 0) AS minimum_stock 
                    FROM(
                        SELECT 
                            pp.id AS product_id,
                            pt.name AS product_name,
                            um.name AS uom_name,
                            pcat.name AS cat_name,
                            COALESCE(SUM(pt.minimum_stock_qty), 0) AS minimum_stock
                            FROM
                                product_product AS pp
                            JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
                            JOIN uom_uom AS um ON um.id = pt.uom_id
                            JOIN product_category AS pcat ON pt.categ_id = pcat.id
                            WHERE pt.minimum_stock_qty > 0 {0}
                            GROUP BY pp.id, pt.name, um.name, pcat.name
                        ) tbl1
                        LEFT JOIN (
                            SELECT stq.product_id, COALESCE(SUM(stq.quantity), 0) AS on_hand_stock
                            FROM
                                stock_quant stq
                            JOIN
                                stock_location stl ON stl.id = stq.location_id
                            WHERE
                                stl.usage = 'internal' AND stl.state='done' {1}
                            GROUP BY
                                stq.product_id							
                        ) tbl2 ON tbl2.product_id = tbl1.product_id                        
                        GROUP BY tbl1.product_id, tbl1.product_name, tbl1.uom_name, tbl1.cat_name
                        ORDER BY tbl1.cat_name, tbl1.product_name
                    """.format(productFilter, locationFilter)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        data_list = []

        for rec in data_res:
            vals = {
                # 'location': rec['location'],
                'category': rec['category'],
                'product': rec['product'],
                'uom_name': rec['uom_name'],
                'on_hand_stock': rec['on_hand_stock'],
                'minimum_stock': rec['minimum_stock'],
                'diff': rec['on_hand_stock'] - rec['minimum_stock']
            }
            data_list.append(vals)

        # data_list = sorted(data_list, key=lambda d: (d['location'], d['product']))

        data = {
            'model': 'inventory.minimum.stock.report.wizard',
            'form': self.read()[0],
            'csr': data_list,
            'locationName': locationName,
            'productName': productName,
        }

        return data

    def x_old_inventory_minimum_stock_report_sql(self, product_id, location_id):
        productFilter = ""
        locationFilter = ""
        locationName = "All"
        productName = "All"

        if product_id:
            productFilter = "AND stq.product_id = '{0}'".format(product_id.id)
            productName = product_id.name

        if location_id:
            locationFilter = "AND stq.location_id = {0}".format(location_id.id)
            locationName = location_id.name

        # if category_id and not product_id:
        #     product_domain += [('product_tmpl_id.categ_id', 'child_of', category_id)]

        data_sql = """                    
                    SELECT tbl2.product_name AS product, tbl2.uom_name AS uom_name, tbl2.cat_name AS category, COALESCE(SUM(tbl1.on_hand_stock), 0) AS on_hand_stock, COALESCE(SUM(tbl2.minimum_stock), 0) AS minimum_stock 
                    FROM
                        (SELECT stq.product_id, COALESCE(SUM(stq.quantity), 0) AS on_hand_stock
                        FROM
                            stock_quant stq
                        LEFT JOIN
                            stock_location stl ON stl.id = stq.location_id
                        WHERE
                            stl.usage = 'internal' AND stl.state='done' {0} {1}
                        GROUP BY
                            stq.product_id
                        ) tbl1
                        LEFT JOIN (
                            SELECT 
                            pp.id AS product_id,
                            pt.name AS product_name,
                            um.name AS uom_name,
                            pcat.name AS cat_name,
                            COALESCE(SUM(pt.minimum_stock_qty), 0) AS minimum_stock
                            FROM
                                product_product AS pp
                            LEFT JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
                            LEFT JOIN uom_uom AS um ON um.id = pt.uom_id
                            LEFT JOIN product_category AS pcat ON pt.categ_id = pcat.id
                            GROUP BY pp.id, pt.name, um.name, pcat.name
                        ) tbl2 ON tbl2.product_id = tbl1.product_id
                        WHERE tbl2.minimum_stock > 0
                        GROUP BY tbl1.product_id, tbl2.product_name, tbl2.uom_name, tbl2.cat_name
                        ORDER BY tbl2.cat_name, tbl2.product_name
                    """.format(productFilter, locationFilter)
        self.env.cr.execute(data_sql)
        data_res = self.env.cr.dictfetchall()

        data_list = []

        for rec in data_res:
            vals = {
                # 'location': rec['location'],
                'category': rec['category'],
                'product': rec['product'],
                'uom_name': rec['uom_name'],
                'on_hand_stock': rec['on_hand_stock'],
                'minimum_stock': rec['minimum_stock'],
                'diff': rec['on_hand_stock'] - rec['minimum_stock']
            }
            data_list.append(vals)

        # data_list = sorted(data_list, key=lambda d: (d['location'], d['product']))

        data = {
            'model': 'inventory.minimum.stock.report.wizard',
            'form': self.read()[0],
            'csr': data_list,
            'locationName': locationName,
            'productName': productName,
        }

        return data