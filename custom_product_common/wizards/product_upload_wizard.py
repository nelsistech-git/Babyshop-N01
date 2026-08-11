from odoo import exceptions, fields, models, _
from odoo.exceptions import UserError
import base64
import datetime, time


class ProductUploadWizard(models.TransientModel):
    _name = "product.upload.wizard"
    _description = "Product Upload Wizard"

    upload_csv_file = fields.Binary(string="Upload File")
    upload_des = fields.Text(string="Description")
    is_old_product = fields.Boolean(string='Is Old Product?', default=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
    ], string='Product Status', default='draft')

    def action_product_upload(self):
        if not self.upload_csv_file:
            raise exceptions.ValidationError("Failed! Required CSV file!")
        else:
            # lines = []
            file_data = base64.decodestring(self.upload_csv_file)
            csv_data = str(file_data.decode("utf-8"))
            row_list = csv_data.split('\n')
            # for csv_line in row_list:
            #     if csv_line:
            #         lines.append(csv_line.split(','))
            # lines.pop(0)
            line_count = len(row_list)

            pos_module_obj = self.env['ir.model'].sudo().search([('model', '=', 'pos.order')], limit=1)
            product_tmpl_obj = self.env['product.template'].sudo()
            product_cat_obj = self.env['product.category'].sudo()
            product_uom_obj = self.env['uom.uom'].sudo()
            product_item_gr_obj = self.env['product.item.group'].sudo()
            product_brand_obj = self.env['product.brand'].sudo()
            product_color_obj = self.env['product.color'].sudo()
            product_model_obj = self.env['product.style'].sudo()
            res_partner_obj = self.env['res.partner'].sudo()

            article_count = 0
            loop_count = 0
            error_str = ""
            row_no = 1
            if len(row_list) > 0:
                for i in range(len(row_list)):
                    if i == 0:
                        continue  # it's for 1st row heading

                    row_no = i + 1
                    rowdata = row_list[i]
                    col_list = rowdata.split(',')
                    if rowdata == '':
                        continue

                    if len(col_list) != 13:
                        error_str += "Row-%s: Error: Required All Columns: Product Category, Barcode, Name, Unit of Measure, Item Group, Product Group, Brand, Color, Model, Sales Price, Cost Price!" % row_no + '\n'
                        continue
                        # raise UserError('Required All Columns: Product Category, Old Barcode, Name, Unit of Measure, Item Group, Product Group, Brand, Sales Price, Cost Price')

                    else:
                        prod_cat = col_list[0]
                        prod_barcode = col_list[1]
                        prod_name = col_list[2]
                        prod_uom = col_list[3]
                        vendor = col_list[4]
                        prod_item_gr = col_list[5]
                        prod_product_gr = col_list[6]
                        prod_brand = col_list[7]
                        prod_color = col_list[8]
                        prod_model = col_list[9]
                        prod_sal = col_list[10]
                        prod_cost = col_list[11]
                        is_salable = col_list[12]
                        if prod_cat == '' or prod_name == '' or prod_uom == '' or prod_sal == '' or prod_cost == '':
                            error_str += "Row-%s: Error: Category, Name, UOM, Sale Price or Cost Price values!" % row_no + '\n'
                            continue
                        elif self.is_old_product and prod_barcode == '':
                            error_str += "Row-%s: Error: Barcode Value for Old Product Flag!" % row_no + '\n'
                            continue
                        else:
                            try:
                                if prod_barcode != '':
                                    product_row = product_tmpl_obj.search(
                                        ['|', ('barcode', '=', prod_barcode), ('product_code', '=', prod_barcode)],
                                        limit=1)
                                else:
                                    product_row = False
                                if product_row:
                                    error_str += "Row-%s: Error: %s already exists!" % (row_no, prod_barcode) + '\n'
                                    continue
                                else:
                                    categ_id = product_cat_obj.search([('complete_name', '=ilike', prod_cat)], limit=1)
                                    uom_id = product_uom_obj.search([('name', '=ilike', prod_uom)], limit=1)
                                    product_item_group_id = product_item_gr_obj.search(
                                        [('name', '=ilike', prod_item_gr)], limit=1)
                                    brand_id = product_brand_obj.search([('name', '=ilike', prod_brand)], limit=1)
                                    color_id = product_color_obj.search([('name', '=ilike', prod_color)], limit=1)
                                    model_id = product_model_obj.search([('name', '=ilike', prod_model)], limit=1)
                                    vendor_id = res_partner_obj.search([('vendor_code', '=ilike', vendor)], limit=1)

                                    if prod_product_gr == 'FG':
                                        product_group = 'product'
                                    elif prod_product_gr == 'SFG':
                                        product_group = 'semi_fg'
                                    elif prod_product_gr == 'RM':
                                        product_group = 'parts'
                                    else:
                                        product_group = None

                                    # if not product_item_group_id:
                                    #     error_str += "Row-%s: Product Item Group not not found!" % (row_no) + '\n'
                                    # elif not brand_id:
                                    #     error_str += "Row-%s: Product Brand not found!" % (row_no) + '\n'

                                    if product_group is None:
                                        error_str += "Row-%s: Error: Product Group not found!" % row_no + '\n'
                                        continue
                                    elif not categ_id:
                                        error_str += "Row-%s: Error: Category not found!" % row_no + '\n'
                                        continue
                                    elif not uom_id:
                                        error_str += "Row-%s: Error: Unit not found!" % row_no + '\n'
                                        continue
                                    else:
                                        categ_code = product_tmpl_obj.get_parent_cat_code(categ_id)
                                        product_code = ''
                                        barcode = ''
                                        default_code = ''

                                        if self.is_old_product:
                                            product_code = prod_barcode
                                            barcode = prod_barcode
                                            default_code = prod_barcode
                                        # else:
                                        #     # if categ_code and self.state == 'approve':
                                        #     #     last_code_row = product_tmpl_obj.search(
                                        #     #         [('category_code', '=', categ_code), ('state', '!=', 'draft'),
                                        #     #          ('product_code', '!=', ''), ('is_old_product', '=', False)],
                                        #     #         order='product_code desc',
                                        #     #         limit=1)
                                        #     #     if last_code_row:
                                        #     #         product_code = str(int(last_code_row[0].product_code) + 1)
                                        #     #     else:
                                        #     #         product_code = str(categ_code) + str(1).zfill(4)
                                        #     # barcode = product_code + '01'
                                        #     # default_code = product_code
                                        #
                                        #     barcode = ''
                                        #     default_code = ''

                                        try:
                                            list_price = float(prod_sal)
                                        except:
                                            list_price = 0
                                        try:
                                            standard_price = float(prod_cost)
                                        except:
                                            standard_price = 0
                                        if not is_salable:
                                            is_salable = '1'
                                        vals = {
                                            'categ_id': categ_id.id,
                                            'category_code': categ_code,
                                            'product_code': product_code,
                                            'product_old_code': prod_barcode,
                                            'is_old_product': self.is_old_product,
                                            'default_code': default_code,
                                            'barcode': barcode,
                                            'name': prod_name,
                                            'uom_id': uom_id.id if uom_id else None,
                                            'uom_po_id': uom_id.id if uom_id else None,
                                            'list_price': list_price,
                                            'standard_price': standard_price,
                                            'product_item_group_id': product_item_group_id.id if product_item_group_id else None,
                                            'product_group': product_group,
                                            'type': 'product',
                                            'brand': brand_id.id if brand_id else None,
                                            'vendor_id': vendor_id.id if vendor_id else None,
                                            'color_id': color_id.id if color_id else None,
                                            'style_id': model_id.id if model_id else None,
                                            'sale_ok': True if str(is_salable) == '1' else False,
                                            'purchase_ok': True,
                                            # 'available_in_pos': True,
                                            # 'state': self.state,
                                        }
                                        if pos_module_obj:
                                            if str(is_salable) == '1':
                                                vals['available_in_pos'] = True
                                        pro_obj = product_tmpl_obj.create(vals)
                                        if self.state == 'approve':
                                            pro_obj.action_confirm()
                                            pro_obj.action_approve()

                                        if not pro_obj.product_variant_ids:
                                            pro_obj._create_variant_ids()

                                        # if categ_code and self.state == 'approve' and product_code and not tmpl_obj.barcode:
                                        #     count = 1
                                        #     for line in tmpl_obj.product_variant_ids:
                                        #         line.barcode = product_code + str(count).zfill(2)
                                        #         count = count + 1

                                        article_count += 1
                                        loop_count += 1
                                        if loop_count == 100:
                                            time.sleep(1)
                                            loop_count = 0
                            except Exception as e:
                                error_str += "Row-%s: Error: Possibly it already exists!" % row_no + '\n'
                                continue
            else:
                raise UserError('No Products to Upload!')

            upload_des = 'Total Rows: ' + str(line_count) + '\nImport Rows: ' + str(article_count) + '\nError:\n' + str(error_str)

            self.upload_des = upload_des

            return {
                'name': _('Product Upload'),
                'context': self.env.context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'product.upload.wizard',
                'res_id': self.id,
                'view_id': False,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    # def x_action_product_upload(self):
    #     if not self.upload_csv_file:
    #         raise exceptions.ValidationError("Failed! Required CSV file!")
    #     else:
    #         lines = []
    #         file_data = base64.decodestring(self.upload_csv_file)
    #         csv_data = str(file_data.decode("utf-8"))
    #         csv_data = csv_data.split('\n')
    #         for csv_line in csv_data:
    #             if csv_line:
    #                 lines.append(csv_line.split(','))
    #         lines.pop(0)
    #         line_count = len(lines)
    #
    #         pos_module_obj = self.env['ir.model'].sudo().search([('model', '=', 'pos.order')], limit=1)
    #         product_tmpl_obj = self.env['product.template'].sudo()
    #
    #         article_count = 0
    #         loop_count = 0
    #         error_str = ""
    #         row_no = 1
    #         if len(lines) > 0:
    #             for i in range(len(lines)):
    #                 row_no = row_no + 1
    #                 rowdata = lines[i]
    #
    #                 if len(rowdata) != 9:
    #                     raise UserError(
    #                         'Required All Columns: Product Category, Old Barcode, Name, Unit of Measure, Item Group, Product Group, Brand, Sales Price, Cost Price')
    #                 else:
    #                     if rowdata[0] == '' or rowdata[2] == '' or rowdata[3] == '' or rowdata[7] == '' or rowdata[
    #                         8] == '':
    #                         error_str += "Row-%s: Missing some values!" % (row_no) + '\n'
    #                         continue
    #                     elif self.is_old_product and rowdata[1] == '':
    #                         error_str += "Row-%s: Missing some values!" % (row_no) + '\n'
    #                         continue
    #                     else:
    #                         try:
    #                             if rowdata[1] != '':
    #                                 product_row = product_tmpl_obj.search(
    #                                     ['|', ('barcode', '=', rowdata[1]), ('product_old_code', '=', rowdata[1])],
    #                                     limit=1)
    #                             else:
    #                                 product_row = False
    #                             if product_row:
    #                                 error_str += "Row-%s: %s already exists!" % (row_no, rowdata[1]) + '\n'
    #                                 continue
    #                             else:
    #                                 categ_id = self.env['product.category'].sudo().search(
    #                                     [('complete_name', '=ilike', rowdata[0])], limit=1)
    #                                 uom_id = self.env['uom.uom'].sudo().search([('name', '=ilike', rowdata[3])],
    #                                                                            limit=1)
    #                                 product_item_group_id = self.env['product.item.group'].sudo().search(
    #                                     [('name', '=ilike', rowdata[4])], limit=1)
    #
    #                                 if rowdata[5] == 'FG':
    #                                     product_group = 'product'
    #                                 elif rowdata[5] == 'RM':
    #                                     product_group = 'parts'
    #                                 else:
    #                                     product_group = None
    #
    #                                 brand_id = self.env['product.brand'].sudo().search([('name', '=ilike', rowdata[6])],
    #                                                                                    limit=1)
    #                                 if not product_item_group_id:
    #                                     error_str += "Row-%s: Product Item Group not not found!" % (
    #                                         row_no) + '\n'
    #                                 if not brand_id:
    #                                     error_str += "Row-%s: Product Brand not found!" % (
    #                                         row_no) + '\n'
    #                                 if product_group is None:
    #                                     error_str += "Row-%s: Product Group not found!" % (
    #                                         row_no) + '\n'
    #                                 if not categ_id or not uom_id:
    #                                     if not categ_id:
    #                                         error_str += "Row-%s: Product not created. Category not found!" % (
    #                                             row_no) + '\n'
    #                                         continue
    #                                     if not uom_id:
    #                                         error_str += "Row-%s: Product not created. Unit not found!" % (
    #                                             row_no) + '\n'
    #                                         continue
    #                                 else:
    #                                     categ_code = product_tmpl_obj.get_parent_cat_code(categ_id)
    #                                     product_code = ''
    #                                     barcode = ''
    #                                     default_code = ''
    #
    #                                     if self.is_old_product:
    #                                         product_code = rowdata[1]
    #                                         barcode = rowdata[1]
    #                                         default_code = rowdata[1]
    #                                     else:
    #                                         if categ_code and self.state == 'approve':
    #                                             last_code_row = self.env['product.template'].sudo().search(
    #                                                 [('category_code', '=', categ_code), ('state', '!=', 'draft'),
    #                                                  ('product_code', '!=', ''), ('is_old_product', '=', False)],
    #                                                 order='product_code desc',
    #                                                 limit=1)
    #                                             if last_code_row:
    #                                                 product_code = str(int(last_code_row[0].product_code) + 1)
    #                                             else:
    #                                                 product_code = str(categ_code) + str(1).zfill(4)
    #
    #                                             barcode = product_code + '01'
    #                                             default_code = product_code
    #
    #                                     list_price = float(rowdata[7]) if rowdata[7] != '' else 0.00
    #                                     standard_price = float(rowdata[8]) if rowdata[8] != '' else 0.00
    #
    #                                     vals = {
    #                                         'categ_id': categ_id.id,
    #                                         'category_code': categ_code,
    #                                         'product_code': product_code,
    #                                         'product_old_code': rowdata[1],
    #                                         'is_old_product': self.is_old_product,
    #                                         'default_code': default_code,
    #                                         'barcode': barcode,
    #                                         'name': rowdata[2],
    #                                         'uom_id': uom_id.id,
    #                                         'uom_po_id': uom_id.id,
    #                                         'list_price': list_price,
    #                                         'standard_price': standard_price,
    #                                         'product_item_group_id': product_item_group_id.id,
    #                                         'product_group': product_group,
    #                                         'type': 'product',
    #                                         'brand': brand_id.id,
    #                                         'sale_ok': True,
    #                                         'purchase_ok': True,
    #                                         # 'available_in_pos': True,
    #                                         'state': self.state,
    #                                     }
    #                                     if pos_module_obj:
    #                                         vals['available_in_pos'] = True
    #                                     tmpl_obj = product_tmpl_obj.create(vals)
    #
    #                                     # if categ_code and self.state == 'approve' and product_code and not tmpl_obj.barcode:
    #                                     #     count = 1
    #                                     #     for line in tmpl_obj.product_variant_ids:
    #                                     #         line.barcode = product_code + str(count).zfill(2)
    #                                     #         count = count + 1
    #
    #                                     article_count += 1
    #                                     loop_count += 1
    #                                     if loop_count == 100:
    #                                         time.sleep(1)
    #                                         loop_count = 0
    #                         except:
    #                             error_str += "Row-%s: Product not created. Possibly it already exists!" % (
    #                                 row_no) + '\n'
    #                             continue
    #         else:
    #             raise UserError('No Products to Upload!')
    #
    #         upload_des = 'Total Rows: ' + str(line_count) + '\nImport Rows: ' + str(article_count) + '\nError:\n' + str(
    #             error_str)
    #
    #         self.upload_des = upload_des
    #
    #         return {
    #             'name': _('Product Upload'),
    #             'context': self.env.context,
    #             'view_type': 'form',
    #             'view_mode': 'form',
    #             'res_model': 'product.upload.wizard',
    #             'res_id': self.id,
    #             'view_id': False,
    #             'type': 'ir.actions.act_window',
    #             'target': 'new',
    #         }

    def action_sample_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/custom_product_common/static/src/sample_product_upload_file.csv',
            'target': 'self',
        }
