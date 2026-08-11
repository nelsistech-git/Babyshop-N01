from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
from calendar import monthrange
from datetime import date, datetime

import xlsxwriter

import base64
from io import BytesIO


class OnDateStockReport(models.TransientModel):
    _name = "on.date.stock.report.wizard"
    _description = "On Date Stock Report"

    def get_years(self):
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

    file_data = fields.Binary('On Date Stock Report')
    category_id = fields.Many2one('product.category', string='Product Category')
    product_id = fields.Many2one('product.product', string='Product', help="Main Product",
                                 domain="[('state', '=', 'approve'), ('product_tmpl_id.categ_id', 'child_of', category_id)]")
    location_id = fields.Many2one('stock.location', string='Location',
                                  domain="[('usage', '=', 'internal'), ('state', '=', 'done')]")
    report_type = fields.Selection([
        ('01', 'Location wise'),
        ('02', 'Category wise'),
        ('03', 'Product wise'),
    ], string='Report Type', required=True, default='01')
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
    # on_date = fields.Datetime('Inventory at Date', required=True, default=fields.Datetime.now)
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month', required=True)
    current_stock_history_id = fields.Many2one('current.stock.history.head', string='Date')

    @api.onchange('year', 'month')
    def _onchange_current_stock_history(self):
        if self.month and self.year:
            m = int(self.month)
            y = int(self.year)
            ndays = monthrange(y, m)[1]
            start_date = date(y, m, 1)
            end_date = date(y, m, ndays)
            return {'domain': {'current_stock_history_id': [('date', '>=', start_date), ('date', '<=', end_date)]}}
        else:
            return {'domain': {'current_stock_history_id': [('date', '>=', None), ('date', '<=', None)]}, 'value': {'current_stock_history_id': None}}

    @api.onchange('location_type')
    def _onchange_location_type(self):
        if self.location_type == 'all':
            return {'location_id': None, 'domain': {'location_id': []}}
        elif self.location_type:
            return {'location_id': None, 'domain': {'location_id': [('type', '=', self.location_type)]}}
        else:
            return {'location_id': None, 'domain': {'location_id': [('type', '=', None)]}}

    def on_date_stock_report_pdf(self):
        category_id = self.category_id
        product_id = self.product_id
        location_id = self.location_id
        report_type = self.report_type
        location_type = self.location_type
        current_stock_history_id = self.current_stock_history_id

        # get data from sql
        data = self.get_report_sql(category_id, product_id, location_id, report_type, location_type, current_stock_history_id)
        return self.env.ref('custom_stock.on_date_stock_report').with_context(
            landscape=False).report_action(self, data=data)

    def on_date_stock_report_excel(self):
        category_id = self.category_id
        product_id = self.product_id
        location_id = self.location_id
        report_type = self.report_type
        location_type = self.location_type
        current_stock_history_id = self.current_stock_history_id

        file_name = "On Date Stock Report.xlsx"
        file_pointer = BytesIO()

        # get data from sql
        data = self.get_report_sql(category_id, product_id, location_id, report_type, location_type, current_stock_history_id)
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

        sheet = workbook.add_worksheet('On Date Stock Report')

        if report_type == '01':
            if data['loc_name'] == 'All Locations':
                sheet.merge_range(0, 0, 2, 11, 'Product wise On Date Stock Report', format0)

                sheet.merge_range(3, 0, 3, 5, 'Category: {0}'.format(data['categ_name']), format1)
                sheet.merge_range(3, 6, 3, 11, 'Location: {0}'.format(data['loc_name']), format3)

                sheet.write(4, 0, 'Location', format1)
                sheet.write(4, 1, 'Category Name', format1)
                sheet.write(4, 2, 'Barcode', format2)
                sheet.write(4, 3, 'Product Name', format1)
                sheet.write(4, 4, 'Attribute Name', format1)
                sheet.write(4, 5, 'UoM', format1)
                sheet.write(4, 6, 'Quantity', format3)
                sheet.write(4, 7, 'Cost', format3)
                sheet.write(4, 8, 'Other Cost', format3)
                sheet.write(4, 9, 'Total Cost', format3)
                sheet.write(4, 10, 'Sale Price', format3)
                sheet.write(4, 11, 'Total Sale Price', format3)

                t_quantity = 0
                t_cost = 0
                t_total_cost_rate = 0
                t_net_value = 0
                total_sales_price = 0
                t_sales_price = 0

                row = 5
                col = 0

                for rec in data['csr']:
                    product_obj = self.env['product.product'].search([('id', '=', rec['product_id'])], limit=1)
                    sheet.write(row, col, rec['location_name'], format4)
                    sheet.write(row, col + 1, product_obj.categ_id.display_name, format4)
                    sheet.write(row, col + 2, product_obj.product_code, format4)
                    sheet.write(row, col + 3, product_obj.name, format4)
                    sheet.write(row, col + 4, product_obj.product_tmpl_id.display_name, format4)
                    sheet.write(row, col + 5, rec['uom_name'], format4)
                    sheet.write(row, col + 6, round(rec['quantity'], 3), format6)
                    t_quantity = t_quantity + rec['quantity']
                    sheet.write(row, col + 7, round(rec['cost'], 2), format6)
                    t_cost = t_cost + rec['cost']
                    sheet.write(row, col + 8, round(rec['total_cost_rate'], 2), format6)
                    t_total_cost_rate = t_total_cost_rate + rec['total_cost_rate']
                    sheet.write(row, col + 9, round(rec['net_value'], 2), format6)
                    t_net_value = t_net_value + rec['net_value']
                    sheet.write(row, col + 10, round(product_obj.lst_price, 2), format6)
                    t_sales_price = t_sales_price + product_obj.lst_price
                    sheet.write(row, col + 11, round(rec['quantity'] * product_obj.lst_price, 2), format6)
                    total_sales_price = total_sales_price + (rec['quantity'] * product_obj.lst_price)

                    row = row + 1

                final_row = row
                final_col = 0
                sheet.merge_range(final_row, final_col, final_row, final_col + 5, 'Total', format3)
                sheet.write(final_row, final_col + 6, round(t_quantity, 3), format3)
                sheet.write(final_row, final_col + 7, round(t_cost, 2), format3)
                sheet.write(final_row, final_col + 8, round(t_total_cost_rate, 2), format3)
                sheet.write(final_row, final_col + 9, round(t_net_value, 2), format3)
                sheet.write(final_row, final_col + 10, round(t_sales_price, 2), format3)
                sheet.write(final_row, final_col + 11, round(total_sales_price, 2), format3)

            else:
                sheet.merge_range(0, 0, 2, 10, 'Product wise On Date Stock Report', format0)

                sheet.merge_range(3, 0, 3, 5, 'Category: {0}'.format(data['categ_name']), format1)
                sheet.merge_range(3, 6, 3, 10, 'Location: {0}'.format(data['loc_name']), format3)

                sheet.write(4, 0, 'Category Name', format1)
                sheet.write(4, 1, 'Barcode', format2)
                sheet.write(4, 2, 'Product Name', format1)
                sheet.write(4, 3, 'Attribute Name', format1)
                sheet.write(4, 4, 'UoM', format1)
                sheet.write(4, 5, 'Quantity', format3)
                sheet.write(4, 6, 'Cost', format3)
                sheet.write(4, 7, 'Other Cost', format3)
                sheet.write(4, 8, 'Total Cost', format3)
                sheet.write(4, 9, 'Sale Price', format3)
                sheet.write(4, 10, 'Total Sale Price', format3)

                t_quantity = 0
                t_cost = 0
                t_total_cost_rate = 0
                t_net_value = 0
                t_sales_price = 0
                total_sales_price = 0

                row = 5
                col = 0

                for rec in data['csr']:
                    product_obj = self.env['product.product'].search([('id', '=', rec['product_id'])], limit=1)
                    sheet.write(row, col, product_obj.categ_id.display_name, format4)
                    sheet.write(row, col + 1, product_obj.product_code, format4)
                    sheet.write(row, col + 2, product_obj.name, format4)
                    sheet.write(row, col + 3, product_obj.product_tmpl_id.display_name, format4)
                    sheet.write(row, col + 4, rec['uom_name'], format4)
                    sheet.write(row, col + 5, round(rec['quantity'], 3), format6)
                    t_quantity = t_quantity + rec['quantity']
                    sheet.write(row, col + 6, round(rec['cost'], 2), format6)
                    t_cost = t_cost + rec['cost']
                    sheet.write(row, col + 7, round(rec['total_cost_rate'], 2), format6)
                    t_total_cost_rate = t_total_cost_rate + rec['total_cost_rate']
                    sheet.write(row, col + 8, round(rec['net_value'], 2), format6)
                    t_net_value = t_net_value + rec['net_value']
                    sheet.write(row, col + 9, round(product_obj.lst_price, 2), format6)
                    t_sales_price = t_sales_price + product_obj.lst_price
                    sheet.write(row, col + 10, round(rec['quantity'] * product_obj.lst_price, 2), format6)
                    total_sales_price = total_sales_price + (rec['quantity'] * product_obj.lst_price)

                    row = row + 1

                final_row = row
                final_col = 0

                sheet.merge_range(final_row, final_col, final_row, final_col + 4, 'Total', format3)
                sheet.write(final_row, final_col + 5, round(t_quantity, 3), format3)
                sheet.write(final_row, final_col + 6, round(t_cost, 2), format3)
                sheet.write(final_row, final_col + 7, round(t_total_cost_rate, 2), format3)
                sheet.write(final_row, final_col + 8, round(t_net_value, 2), format3)
                sheet.write(final_row, final_col + 9, round(t_sales_price, 2), format3)
                sheet.write(final_row, final_col + 10, round(total_sales_price, 2), format3)

        elif report_type == '02':
            if data['loc_name'] == 'All Locations':
                sheet.merge_range(0, 0, 2, 3, 'Category wise On Date Stock Report', format0)

                sheet.merge_range(3, 0, 3, 1, 'Category: {0}'.format(data['categ_name']), format1)
                sheet.merge_range(3, 2, 3, 3, 'Location: {0}'.format(data['loc_name']), format3)

                sheet.write(4, 0, 'Location', format1)
                sheet.write(4, 1, 'Category Name', format1)
                sheet.write(4, 2, 'Quantity', format2)
                sheet.write(4, 3, 'Total Cost', format3)

                t_quantity = 0
                t_net_value = 0

                row = 5
                col = 0

                for rec in data['csr']:
                    sheet.write(row, col, rec['location_name'], format4)
                    sheet.write(row, col + 1, rec['categ_name'], format4)
                    sheet.write(row, col + 2, round(rec['quantity'], 3), format6)
                    t_quantity = t_quantity + rec['quantity']
                    sheet.write(row, col + 3, round(rec['net_value'], 2), format6)
                    t_net_value = t_net_value + rec['net_value']

                    row = row + 1

                final_row = row
                final_col = 0
                sheet.merge_range(final_row, final_col, final_row, final_col + 1, 'Total', format5)
                sheet.write(final_row, final_col + 2, round(t_quantity, 3), format5)
                sheet.write(final_row, final_col + 3, round(t_net_value, 2), format5)

            else:
                sheet.merge_range(0, 0, 2, 2, 'Category wise On Date Stock Report', format0)

                sheet.merge_range(3, 0, 3, 1, 'Category: {0}'.format(data['categ_name']), format1)
                sheet.merge_range(3, 2, 3, 2, 'Location: {0}'.format(data['loc_name']), format3)

                sheet.write(4, 0, 'Category Name', format1)
                sheet.write(4, 1, 'Quantity', format2)
                sheet.write(4, 2, 'Total Cost', format3)

                t_quantity = 0
                t_net_value = 0

                row = 5
                col = 0

                for rec in data['csr']:
                    sheet.write(row, col, rec['categ_name'], format4)
                    sheet.write(row, col + 1, round(rec['quantity'], 3), format6)
                    t_quantity = t_quantity + rec['quantity']
                    sheet.write(row, col + 2, round(rec['net_value'], 2), format6)
                    t_net_value = t_net_value + rec['net_value']

                    row = row + 1

                final_row = row
                final_col = 0
                sheet.write(final_row, final_col, 'Total', format7)
                sheet.write(final_row, final_col + 1, round(t_quantity, 3), format7)
                sheet.write(final_row, final_col + 2, round(t_net_value, 2), format7)
        else:
            sheet.merge_range(0, 0, 2, 6, 'Product wise On Date Stock Report', format0)

            sheet.merge_range(3, 0, 3, 6, 'Category: {0}'.format(data['categ_name']), format1)

            sheet.write(4, 0, 'Category Name', format1)
            sheet.write(4, 1, 'Product Name', format1)
            sheet.write(4, 2, 'UoM', format1)
            sheet.write(4, 3, 'Quantity', format2)
            sheet.write(4, 4, 'Cost', format3)
            sheet.write(4, 5, 'Other Cost', format3)
            sheet.write(4, 6, 'Total Cost', format3)

            t_quantity = 0
            t_cost = 0
            t_total_cost_rate = 0
            t_net_value = 0

            row = 5
            col = 0

            for rec in data['csr']:
                sheet.write(row, col, rec['categ_name'], format4)
                sheet.write(row, col + 1, rec['product_name'], format4)
                sheet.write(row, col + 2, rec['uom_name'], format4)
                sheet.write(row, col + 3, round(rec['quantity'], 3), format6)
                t_quantity = t_quantity + rec['quantity']
                sheet.write(row, col + 4, round(rec['cost'], 2), format6)
                t_cost = t_cost + rec['cost']
                sheet.write(row, col + 5, round(rec['total_cost_rate'], 2), format6)
                t_total_cost_rate = t_total_cost_rate + rec['total_cost_rate']
                sheet.write(row, col + 6, round(rec['net_value'], 2), format6)
                t_net_value = t_net_value + rec['net_value']

                row = row + 1

            final_row = row
            final_col = 0
            sheet.merge_range(final_row, final_col, final_row, final_col + 2, 'Total', format7)
            sheet.write(final_row, final_col + 3, round(t_quantity, 3), format7)
            sheet.write(final_row, final_col + 4, round(t_cost, 2), format7)
            sheet.write(final_row, final_col + 5, round(t_total_cost_rate, 2), format7)
            sheet.write(final_row, final_col + 6, round(t_net_value, 2), format7)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.encodestring(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'On Date Stock Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=on.date.stock.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def get_report_sql(self, category_id, product_id, location_id, report_type, location_type, current_stock_history_id):
        product_domain = [('state', '=', 'approve')]

        if category_id:
            product_domain.append(('product_tmpl_id.categ_id', 'child_of', category_id.id))
        if product_id:
            product_domain.append(('id', '=', product_id.id))

        product_ids = tuple(self.env['product.product'].search(product_domain).ids)

        categoryFilter = ""
        categ_name = ""

        if category_id:
            categ_name = category_id.name
            categoryFilter = "AND pt.categ_id = {0}".format(category_id.id)
        else:
            categ_name = "All Categories"

        locationFilter = ""
        locationTypeFilter = ""

        if len(product_ids) > 1:
            productFilter = "AND sq.product_id IN {0}".format(product_ids)
        else:
            if len(product_ids) > 1:
                productFilter = "AND sq.product_id IN {0}".format(product_ids)
            elif len(product_ids) == 1:
                productFilter = "AND sq.product_id = {0}".format(product_ids[0])
            else:
                raise ValidationError(_('No product(s) available.'))

        if location_id:
            locationFilter = "AND sq.location_id = %s" % location_id.id
            loc_name = location_id.name
        else:
            loc_name = "All Locations"

        if location_type != 'all':
            locationTypeFilter = "AND sl.type = '%s'" % location_type

        if report_type == '01':
            self.env.cr.execute("""
                                SELECT main_tbl.product_id, main_tbl.loc_name AS location_name, pc.name AS categ_name, main_tbl.product_name, uom.name AS uom_name, COALESCE(SUM(quantity), 0) AS quantity,
                                COALESCE(SUM(main_tbl.cost), 0) AS cost, COALESCE(SUM(total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(net_value), 0) AS net_value
                                FROM (
                                    SELECT pt.categ_id, sq.product_id, sl.name AS loc_name, pt.name AS product_name, pt.uom_id, COALESCE(SUM(sq.quantity), 0) AS quantity, COALESCE(SUM(sq.cost), 0) AS cost,
                                    COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(sq.net_value), 0) AS net_value
                                    FROM(
                                        SELECT ct.location_id, ct.product_id, COALESCE(SUM(ct.quantity), 0) AS quantity, COALESCE(SUM(ct.unit_cost_quant), 0) AS cost, COALESCE(SUM(ct.unit_other_cost_quant), 0) AS total_cost_rate,
                                            COALESCE(SUM(unit_cost_quant + unit_other_cost_quant), 0) AS net_value
                                        FROM current_stock_history_head cth
                                        JOIN current_stock_history ct ON ct.head_id = cth.id
                                        WHERE cth.generate_flag = 'True' AND cth.id = {3}
                                        GROUP BY ct.location_id, ct.product_id
                                        ORDER BY ct.location_id, ct.product_id
                                    ) sq
                                    LEFT JOIN product_product pp ON pp.id=sq.product_id
                                    LEFT JOIN product_template pt ON pt.id=pp.product_tmpl_id
                                    LEFT JOIN stock_location sl ON sl.id=sq.location_id
                                    WHERE sl.usage='internal'  AND sl.active='True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                                 	{0} {1} {2}
                                    GROUP BY sl.name, sq.product_id, pt.name, pt.uom_id, pt.categ_id
                                    ORDER BY pt.name, sl.name
                                ) main_tbl
                                LEFT JOIN product_category pc ON pc.id = main_tbl.categ_id
                                LEFT JOIN uom_uom uom ON uom.id = main_tbl.uom_id
                                GROUP BY main_tbl.loc_name, pc.name, main_tbl.product_id, main_tbl.product_name, uom.name
                                ORDER BY main_tbl.product_name, main_tbl.loc_name
                                """.format(productFilter, locationFilter, locationTypeFilter, current_stock_history_id.id))
            data_list = self.env.cr.dictfetchall()

        elif report_type == '02':
            categ_summary_sql = """
                                SELECT main_tbl.categ_id, main_tbl.loc_name AS location_name, pc.name AS categ_name, COALESCE(SUM(quantity), 0) AS quantity,
                                COALESCE(SUM(net_value), 0) AS net_value
                                FROM (
                                    SELECT pt.categ_id, sl.name AS loc_name, COALESCE(SUM(sq.quantity), 0) AS quantity, COALESCE(SUM(sq.net_value), 0) AS net_value
                                    FROM (
                                        SELECT ct.location_id, ct.product_id, COALESCE(SUM(ct.quantity), 0) AS quantity, COALESCE(SUM(ct.unit_cost_quant + ct.unit_other_cost_quant), 0) AS net_value
                                        FROM current_stock_history_head cth
                                        JOIN current_stock_history ct ON ct.head_id = cth.id
                                        WHERE cth.generate_flag = 'True' AND cth.id = {2}
                                        GROUP BY ct.location_id, ct.product_id
                                        ORDER BY ct.location_id, ct.product_id
                                    ) sq
                                    LEFT JOIN product_product pp ON pp.id = sq.product_id
                                    LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                                    LEFT JOIN stock_location sl ON sl.id = sq.location_id
                                    WHERE sl.usage='internal' AND sl.active='True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                                 	{0} {1}
                                    GROUP BY sl.name, pt.categ_id
                                    ORDER BY sl.name
                                ) main_tbl
                                LEFT JOIN product_category pc ON pc.id = main_tbl.categ_id
                                GROUP BY main_tbl.categ_id, main_tbl.loc_name, pc.name
                                ORDER BY pc.name, main_tbl.loc_name
                                """.format(categoryFilter, locationFilter, current_stock_history_id.id)
            self.env.cr.execute(categ_summary_sql)
            data_list = self.env.cr.dictfetchall()

        else:
            product_summary_sql = """
                                SELECT main_tbl.product_id, pc.name AS categ_name, main_tbl.product_name, uom.name AS uom_name,
                                COALESCE(SUM(quantity), 0) AS quantity, COALESCE(SUM(main_tbl.cost), 0) AS cost,
                                COALESCE(SUM(total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(net_value), 0) AS net_value
                                FROM (
                                    SELECT pt.categ_id, sq.product_id, pt.name AS product_name, pt.uom_id, COALESCE(SUM(sq.quantity), 0) AS quantity, COALESCE(SUM(sq.cost), 0) AS cost,
                                    COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(sq.net_value), 0) AS net_value
                                    FROM (
                                        SELECT ct.location_id, ct.product_id, COALESCE(SUM(ct.quantity), 0) AS quantity, COALESCE(SUM(ct.unit_cost_quant), 0) AS cost, COALESCE(SUM(ct.unit_other_cost_quant), 0) AS total_cost_rate, COALESCE(SUM(ct.unit_cost_quant + ct.unit_other_cost_quant), 0) AS net_value
                                        FROM current_stock_history_head cth
                                        JOIN current_stock_history ct ON ct.head_id = cth.id
                                        WHERE cth.generate_flag = 'True' AND cth.id = {1}
                                        GROUP BY ct.location_id, ct.product_id
                                        ORDER BY ct.location_id, ct.product_id
                                    ) sq
                                    LEFT JOIN product_product pp ON pp.id=sq.product_id
                                    LEFT JOIN product_template pt ON pt.id=pp.product_tmpl_id
                                    LEFT JOIN stock_location sl ON sl.id=sq.location_id
                                    WHERE sl.usage='internal' AND sl.active='True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                                 	{0}
                                    GROUP BY sq.product_id, pt.name, pt.uom_id, pt.categ_id
                                    ORDER BY pt.name
                                ) main_tbl
                                LEFT JOIN product_category pc ON pc.id = main_tbl.categ_id
                                LEFT JOIN uom_uom uom ON uom.id = main_tbl.uom_id
                                GROUP BY main_tbl.product_id, main_tbl.product_name, uom.name, pc.name
                                ORDER BY pc.name, main_tbl.product_name
                                """.format(productFilter, current_stock_history_id.id)
            self.env.cr.execute(product_summary_sql)
            data_list = self.env.cr.dictfetchall()

        data = {
            'model': "on.date.stock.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'categ_name': categ_name,
            'loc_name': loc_name,
            'loc_type': dict(self._fields['location_type'].selection).get(location_type),
        }
        return data
