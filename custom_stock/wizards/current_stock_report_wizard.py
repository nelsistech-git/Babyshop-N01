from odoo import fields, models, _, api
from odoo.exceptions import ValidationError

import xlsxwriter

import base64
from io import BytesIO


class CurrentStockReport(models.TransientModel):
    _name = "current.stock.report.wizard"
    _description = "Current Stock Report"

    file_data = fields.Binary('Current Stock Report')
    is_all_product = fields.Boolean(default=False)
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
            return {'location_id': None,
                    'domain': {'location_id': [('usage', '=', 'internal'), ('state', '=', 'done'), ('type', '!=', 'project')]}}
        elif self.location_type == 'project':
            return {'location_id': None, 'domain': {
                'location_id': [('type', '=', self.location_type), ('usage', '=', 'internal'), ('state', '=', 'done'), ('type', '=', 'project')]}}
        elif self.location_type:
            return {'location_id': None, 'domain': {
                'location_id': [('type', '=', self.location_type), ('usage', '=', 'internal'), ('state', '=', 'done'), ('type', '!=', 'project')]}}
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

    def current_stock_report_pdf(self):
        category_id = self.category_id
        product_id = self.product_id
        location_id = self.location_id
        report_type = self.report_type
        location_type = self.location_type
        sale_type = self.sale_type

        # get data from sql
        data = self.get_report_sql(category_id, product_id, location_id, report_type, location_type, sale_type)
        return self.env.ref('custom_stock.current_stock_report').with_context(
            landscape=True).report_action(self, data=data)

    def current_stock_report_excel(self):
        category_id = self.category_id
        product_id = self.product_id
        location_id = self.location_id
        report_type = self.report_type
        location_type = self.location_type
        sale_type = self.sale_type

        file_name = "Current Stock Report.xlsx"
        file_pointer = BytesIO()

        # get data from sql
        data = self.get_report_sql(category_id, product_id, location_id, report_type, location_type, sale_type)
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
        format7.set_align('right')
        format8 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
        format8.set_border()
        format9 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
        format9.set_border()

        sheet = workbook.add_worksheet('Current Stock Report')

        if report_type == '01':
            sheet.merge_range(0, 0, 2, 10, 'Product wise Current Stock Report', format0)

            sheet.merge_range(3, 0, 3, 3, 'Category: {0}'.format(data['categ_name']), format1)
            sheet.merge_range(3, 4, 3, 10, 'Location: {0}'.format(data['loc_name']), format3)

            sheet.write(4, 0, 'Location', format1)
            sheet.write(4, 1, 'Category Name', format1)
            sheet.write(4, 2, 'Product Name', format1)
            sheet.write(4, 3, 'UoM', format1)
            sheet.write(4, 4, 'Quantity', format2)
            sheet.write(4, 5, 'Price Unit', format3)
            sheet.write(4, 6, 'Total Price', format3)
            sheet.write(4, 7, 'Unit Other Cost', format3)
            sheet.write(4, 8, 'Total Other Cost', format3)
            sheet.write(4, 9, 'Total Unit Price', format3)
            sheet.write(4, 10, 'Total Cost', format3)

            t_quantity = 0
            t_cost = 0
            t_other_cost_rate = 0
            t_total_cost_rate = 0
            t_t_u_p = 0
            t_t_p = 0
            t_net_value = 0

            row = 5
            col = 0

            for rec in data['csr']:
                sheet.write(row, col, rec['location_name'], format4)
                sheet.write(row, col + 1, rec['categ_name'], format4)
                sheet.write(row, col + 2, rec['product_name'], format4)
                sheet.write(row, col + 3, rec['uom_name'], format4)

                sheet.write(row, col + 4, round(rec['quantity'], 3), format6)
                t_p = rec['quantity'] * rec['cost']
                t_c = t_p + rec['total_cost_rate']
                t_quantity = t_quantity + rec['quantity']
                other_cost_rate = 0
                if rec['quantity']:
                    other_cost_rate = rec['total_cost_rate'] / rec['quantity']
                t_u_p = other_cost_rate + rec['cost']

                sheet.write(row, col + 5, round(rec['cost'], 2), format6)
                t_cost = t_cost + rec['cost']

                sheet.write(row, col + 6, round(t_p, 2), format6)
                t_t_p += t_p

                sheet.write(row, col + 7, round(other_cost_rate, 2), format6)
                t_other_cost_rate += other_cost_rate

                sheet.write(row, col + 8, round(rec['total_cost_rate'], 2), format6)
                t_total_cost_rate = t_total_cost_rate + rec['total_cost_rate']

                sheet.write(row, col + 9, round(t_u_p, 2), format6)
                t_t_u_p += t_u_p

                sheet.write(row, col + 10, round(t_c, 2), format6)
                t_net_value = t_net_value + t_c

                row = row + 1

            final_row = row
            final_col = 0
            sheet.merge_range(final_row, final_col, final_row, final_col + 3, 'Total', format7)
            sheet.write(final_row, final_col + 4, round(t_quantity, 3), format7)
            sheet.write(final_row, final_col + 5, round(t_cost, 2), format7)
            sheet.write(final_row, final_col + 6, round(t_t_p, 2), format7)
            sheet.write(final_row, final_col + 7, round(t_other_cost_rate, 2), format7)
            sheet.write(final_row, final_col + 8, round(t_total_cost_rate, 2), format7)
            sheet.write(final_row, final_col + 9, round(t_t_u_p, 2), format7)
            sheet.write(final_row, final_col + 10, round(t_net_value, 2), format7)

        elif report_type == '02':
            if data['loc_name'] == 'All Locations':
                sheet.merge_range(0, 0, 2, 3, 'Category wise Current Stock Report', format0)

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
                sheet.merge_range(0, 0, 2, 2, 'Category wise Current Stock Report', format0)

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
            sheet.merge_range(0, 0, 2, 9, 'Product wise Current Stock Report', format0)

            sheet.merge_range(3, 0, 3, 9, 'Category: {0}'.format(data['categ_name']), format1)

            sheet.write(4, 0, 'Category Name', format1)
            sheet.write(4, 1, 'Product Name', format1)
            sheet.write(4, 2, 'UoM', format1)
            sheet.write(4, 3, 'Quantity', format2)
            sheet.write(4, 4, 'Price Unit', format3)
            sheet.write(4, 5, 'Total Price', format3)
            sheet.write(4, 6, 'Unit Other Cost', format3)
            sheet.write(4, 7, 'Total Other Cost', format3)
            sheet.write(4, 8, 'Total Unit Price', format3)
            sheet.write(4, 9, 'Total Cost', format3)

            t_quantity = 0
            t_cost = 0
            t_other_cost_rate = 0
            t_total_cost_rate = 0
            t_t_u_p = 0
            t_t_p = 0
            t_net_value = 0

            row = 5
            col = 0

            for rec in data['csr']:
                sheet.write(row, col, rec['categ_name'], format4)
                sheet.write(row, col + 1, rec['product_name'], format4)
                sheet.write(row, col + 2, rec['uom_name'], format4)

                sheet.write(row, col + 3, round(rec['quantity'], 3), format6)
                t_p = rec['quantity'] * rec['cost']

                t_quantity = t_quantity + rec['quantity']
                other_cost_rate = 0
                total_cost_rate = 0
                if rec['quantity']:
                    other_cost_rate = rec['total_cost_rate'] / rec['quantity']
                    total_cost_rate = rec['total_cost_rate']
                t_u_p = other_cost_rate + rec['cost']
                t_c = t_p + total_cost_rate

                sheet.write(row, col + 4, round(rec['cost'], 2), format6)
                t_cost = t_cost + rec['cost']

                sheet.write(row, col + 5, round(t_p, 2), format6)
                t_t_p += t_p

                sheet.write(row, col + 6, round(other_cost_rate, 2), format6)
                t_other_cost_rate += other_cost_rate

                sheet.write(row, col + 7, round(total_cost_rate, 2), format6)
                t_total_cost_rate = t_total_cost_rate + total_cost_rate

                sheet.write(row, col + 8, round(t_u_p, 2), format6)
                t_t_u_p += t_u_p

                sheet.write(row, col + 9, round(t_c, 2), format6)
                t_net_value = t_net_value + t_c

                row = row + 1

            final_row = row
            final_col = 0
            sheet.merge_range(final_row, final_col, final_row, final_col + 2, 'Total', format7)
            sheet.write(final_row, final_col + 3, round(t_quantity, 3), format7)
            sheet.write(final_row, final_col + 4, round(t_cost, 2), format7)
            sheet.write(final_row, final_col + 5, round(t_t_p, 2), format7)
            sheet.write(final_row, final_col + 6, round(t_other_cost_rate, 2), format7)
            sheet.write(final_row, final_col + 7, round(t_total_cost_rate, 2), format7)
            sheet.write(final_row, final_col + 8, round(t_t_u_p, 2), format7)
            sheet.write(final_row, final_col + 9, round(t_net_value, 2), format7)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.b64encode(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Current Stock Report',
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=current.stock.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def get_report_sql(self, category_id, product_id, location_id, report_type, location_type, sale_type):
        product_domain = [('state', '=', 'approve')]

        # if category_id and not product_id:
        #     product_domain += [('product_tmpl_id.categ_id', 'child_of', category_id.id)]
        # if category_id and product_id:
        #     product_domain += [('product_tmpl_id.categ_id', 'child_of', category_id.id), ('id', '=', product_id.id)]

        if category_id:
            product_domain.append(('product_tmpl_id.categ_id', 'child_of', category_id.id))
        if product_id:
            product_domain.append(('id', '=', product_id.id))

        if sale_type == '01':
            product_domain.append(('sale_ok', '=', True))
        elif sale_type == '02':
            product_domain.append(('sale_ok', '=', False))

        product_ids = tuple(self.env['product.product'].search(product_domain).ids)

        categoryFilter = ""
        categ_name = ""

        if category_id:
            categ_name = category_id.name
            categoryFilter = "AND pt.categ_id = {0}".format(category_id.id)
        else:
            categ_name = "All Categories"

        productFilter = ""
        locationFilter = ""
        locationTypeFilter = ""

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
        else:
            pass
            #locationTypeFilter = "AND (sl.usage = 'internal')"
            #locationTypeFilter = "AND (sl.type is null or sl.type != 'project')"
        data_list = []

        if report_type == '01':
            if self.is_all_product:
                self.env.cr.execute("""
                                    -- Query for products with stock
                                    SELECT main_tbl.product_id  AS product_id, main_tbl.loc_name as loc_name, pc.name AS categ_name, main_tbl.product_name as product_name,
                                           uom.name AS uom_name,
                                           COALESCE(SUM(quantity), 0) AS quantity,
                                           COALESCE(SUM(total_cost_rate), 0) AS total_cost_rate,
                                           COALESCE(SUM(net_value), 0) AS net_value
                                    FROM (
                                        SELECT pt.categ_id, sq.product_id, sl.name AS loc_name, pt.name AS product_name, pt.uom_id,
                                               COALESCE(SUM(sq.quantity), 0) AS quantity,
                                               COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate,
                                               COALESCE(SUM(sq.net_value), 0) AS net_value
                                        FROM stock_quant sq
                                        LEFT JOIN product_product pp ON pp.id = sq.product_id
                                        LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                                        LEFT JOIN stock_location sl ON sl.id = sq.location_id
                                        WHERE sl.usage = 'internal' AND sl.active = 'True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                                        {0} {1} {2}
                                        GROUP BY sl.name, sq.product_id, pt.name, pt.uom_id, pt.categ_id
                                        ORDER BY pt.name, sl.name
                                    ) main_tbl
                                    LEFT JOIN product_category pc ON pc.id = main_tbl.categ_id
                                    LEFT JOIN uom_uom uom ON uom.id = main_tbl.uom_id
                                    GROUP BY main_tbl.loc_name, pc.name, main_tbl.product_id, main_tbl.product_name, uom.name
                                    UNION ALL
                                    -- Query for products without stock
                                    SELECT pp.id AS product_id, '' AS loc_name, pc.name AS categ_name, pt.name AS product_name, uom.name AS uom_name,
                                           0 AS quantity, 0 AS total_cost_rate, 0 AS net_value
                                    FROM product_product pp
                                    LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                                    LEFT JOIN product_category pc ON pc.id = pt.categ_id
                                    LEFT JOIN uom_uom uom ON uom.id = pt.uom_id
                                    WHERE pt.state = 'approve'
                                          AND pp.active = 'True'
                                          AND pp.id NOT IN (
                                              SELECT DISTINCT sq.product_id
                                              FROM stock_quant sq
                                              WHERE sq.location_id IN (
                                                  SELECT id
                                                  FROM stock_location
                                                  WHERE usage = 'internal' AND active = 'True' AND state = 'done'
                                              )
                                          )
                                    
                                    ORDER BY quantity desc ;
                                    """.format(productFilter, locationFilter, locationTypeFilter))
                quant_result = self.env.cr.dictfetchall()
            else:
                self.env.cr.execute("""
                                        SELECT main_tbl.product_id, main_tbl.loc_name, pc.name AS categ_name, main_tbl.product_name, uom.id AS uom_id, COALESCE(SUM(quantity), 0) AS quantity,
                                        COALESCE(SUM(total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(net_value), 0) AS net_value
                                        FROM (
                                            SELECT pt.categ_id, sq.product_id, sl.name AS loc_name, pt.name AS product_name, pt.uom_id, COALESCE(SUM(sq.quantity), 0) AS quantity, 
                                            COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(sq.net_value), 0) AS net_value
                                            FROM stock_quant sq
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
                                        GROUP BY main_tbl.loc_name, pc.name, main_tbl.product_id, main_tbl.product_name, uom.id
                                        ORDER BY main_tbl.product_name, main_tbl.loc_name
                                        """.format(productFilter, locationFilter, locationTypeFilter))
                quant_result = self.env.cr.dictfetchall()
            for data in quant_result:
                product_obj = self.env['product.product'].search([('id', '=', data['product_id'])], limit=1)
                uom_obj = self.env['uom.uom'].search([('id', '=', data['uom_id'])], limit=1)
                cost = product_obj.standard_price
                t_p = data['quantity'] * cost
                t_c = t_p + data['total_cost_rate']
                other_cost_rate = 0
                if data['quantity'] > 0:
                    other_cost_rate = data['total_cost_rate'] / data['quantity']
                t_u_p = other_cost_rate + cost
                vals = {
                    'categ_name': data['categ_name'],
                    'location_name': data['loc_name'],
                    'product_name': product_obj.display_name,
                    'uom_name': uom_obj.display_name,
                    'quantity': data['quantity'],
                    't_p': t_p,
                    't_c': t_c,
                    'other_cost_rate': other_cost_rate,
                    't_u_p': t_u_p,
                    'total_cost_rate': data['total_cost_rate'],
                    'net_value': data['net_value'],
                    'cost': cost
                }
                data_list.append(vals)

        elif report_type == '02':
            if self.is_all_product:
                self.env.cr.execute("""
                                    -- Query for products with stock
                                    SELECT main_tbl.categ_id, main_tbl.loc_name, pc.name AS categ_name, COALESCE(SUM(quantity), 0) AS quantity,
                                    COALESCE(SUM(net_value), 0) AS net_value
                                    FROM (
                                        SELECT pt.categ_id, sl.name AS loc_name, COALESCE(SUM(sq.quantity), 0) AS quantity,
                                        COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(sq.net_value), 0) AS net_value
                                        FROM stock_quant sq
                                        LEFT JOIN product_product pp ON pp.id = sq.product_id
                                        LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                                        LEFT JOIN stock_location sl ON sl.id = sq.location_id
                                        WHERE sl.usage='internal' AND sl.active='True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                                        {0} {1} {2}
                                        GROUP BY sl.name, pt.categ_id
                                        ORDER BY sl.name
                                    ) main_tbl
                                    LEFT JOIN product_category pc ON pc.id = main_tbl.categ_id
                                    GROUP BY main_tbl.categ_id, main_tbl.loc_name, pc.name
                                    UNION ALL
                                    -- Query for products without stock
                                    SELECT pc.id AS categ_id, '' AS loc_name, pc.name AS categ_name, 0 AS quantity, 0 AS net_value
                                    FROM product_category pc
                                    WHERE pc.id NOT IN (
                                        SELECT DISTINCT pt.categ_id
                                        FROM stock_quant sq
                                        LEFT JOIN product_product pp ON pp.id = sq.product_id
                                        LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                                        LEFT JOIN stock_location sl ON sl.id = sq.location_id
                                        WHERE sl.usage = 'internal' AND sl.active = 'True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                                    )
                                    ORDER BY quantity desc;
                                    """.format(productFilter, locationFilter, locationTypeFilter))
                categ_summary_dict = self.env.cr.dictfetchall()

            else:
                categ_summary_sql = """
                                    SELECT main_tbl.categ_id, main_tbl.loc_name, pc.name AS categ_name, COALESCE(SUM(quantity), 0) AS quantity,
                                    COALESCE(SUM(net_value), 0) AS net_value
                                    FROM (
                                        SELECT pt.categ_id, sl.name AS loc_name, COALESCE(SUM(sq.quantity), 0) AS quantity, 
                                        COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(sq.net_value), 0) AS net_value
                                        FROM stock_quant sq
                                        LEFT JOIN product_product pp ON pp.id = sq.product_id
                                        LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                                        LEFT JOIN stock_location sl ON sl.id = sq.location_id
                                        WHERE sl.usage='internal' AND sl.active='True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                                        {0} {1} {2}
                                        GROUP BY sl.name, pt.categ_id
                                        ORDER BY sl.name
                                    ) main_tbl
                                    LEFT JOIN product_category pc ON pc.id = main_tbl.categ_id
                                    GROUP BY main_tbl.categ_id, main_tbl.loc_name, pc.name
                                    ORDER BY pc.name, main_tbl.loc_name
                                    """.format(categoryFilter, locationFilter, locationTypeFilter)
                self.env.cr.execute(categ_summary_sql)
                categ_summary_dict = self.env.cr.dictfetchall()

            for rec in categ_summary_dict:
                vals = {
                    'categ_name': rec['categ_name'],
                    'location_name': rec['loc_name'],
                    'quantity': rec['quantity'],
                    'net_value': rec['net_value'],
                }
                data_list.append(vals)

        else:
            if self.is_all_product:
                self.env.cr.execute("""
                                    -- Query for products with stock
                                    SELECT main_tbl.product_id as product_id, pc.name AS categ_name, main_tbl.product_name, uom.id AS uom_id,
                                    COALESCE(SUM(quantity), 0) AS quantity,
                                    COALESCE(SUM(total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(net_value), 0) AS net_value
                                    FROM (
                                        SELECT pt.categ_id, sq.product_id, pt.name AS product_name, pt.uom_id, COALESCE(SUM(sq.quantity), 0) AS quantity, 
                                        COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(sq.net_value), 0) AS net_value
                                        FROM stock_quant sq
                                        LEFT JOIN product_product pp ON pp.id=sq.product_id
                                        LEFT JOIN product_template pt ON pt.id=pp.product_tmpl_id
                                        LEFT JOIN stock_location sl ON sl.id=sq.location_id
                                        WHERE sl.usage='internal'  AND sl.active='True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                                        {0}
                                        GROUP BY sq.product_id, pt.name, pt.uom_id, pt.categ_id
                                        ORDER BY pt.name
                                    ) main_tbl
                                    LEFT JOIN product_category pc ON pc.id = main_tbl.categ_id
                                    LEFT JOIN uom_uom uom ON uom.id = main_tbl.uom_id
                                    GROUP BY main_tbl.product_id, main_tbl.product_name, uom.id, pc.name
                                    
                                    UNION ALL
                                    
                                    -- Query for products without stock
                                    SELECT pp.id AS product_id, pc.name AS categ_name, pt.name AS product_name, uom.id AS uom_id,
                                           0 AS quantity, 0 AS total_cost_rate, 0 AS net_value
                                    FROM product_product pp
                                    LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                                    LEFT JOIN product_category pc ON pc.id = pt.categ_id
                                    LEFT JOIN uom_uom uom ON uom.id = pt.uom_id
                                    WHERE pt.state = 'approve'
                                          AND pp.active = 'True'
                                          AND pp.id NOT IN (
                                              SELECT DISTINCT sq.product_id
                                              FROM stock_quant sq
                                              WHERE sq.location_id IN (
                                                  SELECT id
                                                  FROM stock_location
                                                  WHERE usage = 'internal' AND active = 'True' AND state = 'done'
                                              )
                                          )

                                    ORDER BY quantity desc ;
                                    """.format(productFilter, locationFilter, locationTypeFilter))
                product_summary_dict = self.env.cr.dictfetchall()
            else:
                product_summary_sql = """
                                    SELECT main_tbl.product_id, pc.name AS categ_name, main_tbl.product_name, uom.id AS uom_id,
                                    COALESCE(SUM(quantity), 0) AS quantity,
                                    COALESCE(SUM(total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(net_value), 0) AS net_value
                                    FROM (
                                        SELECT pt.categ_id, sq.product_id, pt.name AS product_name, pt.uom_id, COALESCE(SUM(sq.quantity), 0) AS quantity, 
                                        COALESCE(SUM(sq.total_cost_rate), 0) AS total_cost_rate, COALESCE(SUM(sq.net_value), 0) AS net_value
                                        FROM stock_quant sq
                                        LEFT JOIN product_product pp ON pp.id=sq.product_id
                                        LEFT JOIN product_template pt ON pt.id=pp.product_tmpl_id
                                        LEFT JOIN stock_location sl ON sl.id=sq.location_id
                                        WHERE sl.usage='internal'  AND sl.active='True' AND sl.state = 'done' AND pp.active = 'True' AND pt.state = 'approve'
                                        {0}
                                        GROUP BY sq.product_id, pt.name, pt.uom_id, pt.categ_id
                                        ORDER BY pt.name
                                    ) main_tbl
                                    LEFT JOIN product_category pc ON pc.id = main_tbl.categ_id
                                    LEFT JOIN uom_uom uom ON uom.id = main_tbl.uom_id
                                    GROUP BY main_tbl.product_id, main_tbl.product_name, uom.id, pc.name
                                    ORDER BY pc.name, main_tbl.product_name
                                    """.format(productFilter)
                self.env.cr.execute(product_summary_sql)
                product_summary_dict = self.env.cr.dictfetchall()

            for data in product_summary_dict:
                product_obj = self.env['product.product'].search([('id', '=', data['product_id'])], limit=1)
                uom_obj = self.env['uom.uom'].search([('id', '=', data['uom_id'])], limit=1)
                cost = product_obj.standard_price
                t_p = data['quantity'] * cost
                t_c = t_p + data['total_cost_rate']

                other_cost_rate = 0
                if data['quantity'] > 0:
                    other_cost_rate = data['total_cost_rate'] / data['quantity']

                t_u_p = other_cost_rate + cost
                vals = {
                    'categ_name': data['categ_name'],
                    'product_name': product_obj.display_name,
                    'uom_name': uom_obj.display_name,
                    'quantity': data['quantity'],
                    't_p': t_p,
                    't_c': t_c,
                    'other_cost_rate': other_cost_rate,
                    't_u_p': t_u_p,
                    'total_cost_rate': data['total_cost_rate'],
                    'net_value': data['net_value'],
                    'cost': cost
                }
                data_list.append(vals)
        #print(data_list)
        data = {
            'model': "current.stock.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'categ_name': categ_name,
            'loc_name': loc_name,
            'loc_type': dict(self._fields['location_type'].selection).get(location_type),
        }
        return data
