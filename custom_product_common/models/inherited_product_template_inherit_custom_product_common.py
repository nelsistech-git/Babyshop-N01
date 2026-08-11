import time

from odoo import models, fields, api, _
from odoo.addons.helper import validator
from odoo.exceptions import UserError, ValidationError
import datetime


# class ProductTemplateLineIds(models.Model):
#     _inherit = "product.template.attribute.line"
#
#     @api.constrains('attribute_id')
#     def _check_unique_constraint_attribute_id(self):
#         for rec in self:
#             msg = 'Attribute Name "%s"' % rec.attribute_id.name
#             envobj = self.env['product.template.attribute.line']
#             conditionlist = [('product_tmpl_id', '=', rec.product_tmpl_id.id), ('attribute_id', '=', rec.attribute_id.id)]
#             validator.check_duplicate_value(rec, envobj, conditionlist, msg)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    categ_id = fields.Many2one(
        'product.category', 'Product Category',
         group_expand='_read_group_categ_id',
         help="Select category for the current product")
    country_id = fields.Many2one('res.country', 'Country')
    # brand_id = fields.Many2one("product.brand", string="Brand Name") #will be delete for abm existing
    minimum_stock_qty = fields.Float('Minimum Stock Qty', copy=False)
    brand = fields.Many2one('product.brand', 'Product Brand', domain="[('active', '=', True)]")  # for abm old
    product_common_name_id = fields.Many2one('product.common.name', domain="[('active', '=', True)]")  # for abm old
    product_description = fields.Char(string="Product Description")
    product_code = fields.Char(size=20, string='Product Code', copy=False, help="Code can be maximum 20 characters")
    product_old_code = fields.Char(size=20, string='Product Old Code', help="Code can be maximum 20 characters")
    category_code = fields.Char(string="Category Code", default='')
    vendor_product_code = fields.Char(string="vendor Product Code", default='')
    conversion_uom_id = fields.Many2one('uom.uom', ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved'),
    ], string='Product Status', readonly=True, copy=False, default='draft')
    type = fields.Selection([
        ('consu', 'Consumable'),
        ('service', 'Service'),
        ('product', 'Storable Product')], string='Product Type', default='product', required=True, tracking=True,
        help='A storable product is a product for which you manage stock. The Inventory app has to be installed.\n'
             'A consumable product is a product for which stock is not managed.\n'
             'A service is a non-material product you provide.')
    # list_price: catalog price, user defined
    list_price = fields.Float(
        'Sales Price', default=0.0,
        digits='Product Price',
        copy=False,
        help="Price at which the product is sold to customers.")
    is_old_product = fields.Boolean(string='Is Old Product?', default=False)
    style_id = fields.Many2one("product.style", string="Product Style", domain="[('active', '=', True)]")
    default_qty = fields.Float(string="Default Quantity")

    product_item_group_id = fields.Many2one("product.item.group", string="Item Group", copy=False,
                                            domain="[('active', '=', True)]")
    product_item_group_type_id = fields.Many2one("product.item.group.type", string="Item Common Type", copy=False,
                                            domain="[('active', '=', True)]")

    color_id = fields.Many2one("product.color", string="Product Color", copy=False, domain="[('active', '=', True)]")
    parent_categ_id = fields.Many2one("product.category", string='Parent Category')
    # size_id = fields.Many2one("product.size", string="Product Size", copy=False, domain="[('active', '=', True)]")
    # cmt_fob_id = fields.Many2one("product.cmt.fob", string="Product CMT/FOB", domain="[('active', '=', True)]")
    customer_id = fields.Many2one('res.partner', 'Customer', ondelete="cascade", domain="[('type', '=', 'contact'), ('active', '=', True), ('customer_rank', '>', 0)]")
    vendor_id = fields.Many2one('res.partner', string="Vendor", ondelete="cascade", domain="[('type', '=', 'contact'), ('active', '=', True), ('supplier_rank', '>', '0')]")
    is_default_discount_product = fields.Boolean(string='Is Default Discount Product?', default=False)
    is_default_product = fields.Boolean(string='Is Default Product?', default=False)
    product_group = fields.Selection([
        ('product', 'FG'),
        ('semi_fg', 'Semi-FG'),
        ('parts', 'Raw Material'),
        ('fixed_asset', 'Fixed Asset'),
        ('others', 'Others')
    ], string='Product Group', default='')
    ratio_type = fields.Selection([
        ('ratio_general', 'Ratio General'),
        ('ratio_break', 'Ratio Break'),
    ], string='Ratio Type', default='')
    fabric_code = fields.Char('Fabric Code')
    roll_no = fields.Char('Roll No.')
    gsm_id = fields.Many2one('product.gsm', 'GSM')
    width = fields.Float('Width')
    composition = fields.Char('Composition')

    # def _value_search(self, operator, value):
    #     recs = self.search([]).filtered(lambda x: len(x.product_variant_ids) < 1)
    #     if recs:
    #         return [('id', 'in', [x.id for x in recs] if recs else False)]
    #     else:
    #         return [('id', '=', 0)]

    @api.onchange('minimum_stock_qty')
    def _onchange_minimum_stock_qty(self):
        if self.minimum_stock_qty < 0:
            raise UserError(_('Minimum stock cannot be less than zero.'))

    def unlink(self):
        for rec in self:
            if any(rec.filtered(lambda rec: rec.state in ('confirm', 'approve'))):
                raise UserError(_('%s can be deleted only in draft state.') % rec.display_name)

        return super(ProductTemplate, self).unlink()

    # def js_python_method(self, model_name, active_id):
    #     pass

    # @api.constrains('attribute_id')
    # def _check_unique_constraint_attribute_id(self):
    #     for rec in self:
    #         msg = 'Attribute Name "%s"' % rec.attribute_id.name
    #         envobj = self.env['product.template.attribute.line']
    #         conditionlist = [('attribute_id', '=', rec.attribute_id.id)]
    #         validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    # def _check_illegal_char(self, values, msg):
    #     flag = True
    #     for value in values:
    #         checkIllegal = values[value].strip()
    #         if checkIllegal:
    #             if re.search("[^A-Za-z0-9 ]", checkIllegal) == None:
    #                 flag = True
    #             else:
    #                 error = 'Remove Special  Character from ' + msg
    #                 raise exceptions.ValidationError(error)
    #                 #                 raise osv.except_osv(('Validation Error'), (msg))
    #                 flag = False
    #         else:
    #             flag = False
    #     if (flag):
    #         return flag
    #     else:
    #         error = msg
    #         raise exceptions.ValidationError(error)
    #         #         raise osv.except_osv(('Validation Error'), (msg))
    #         return flag

    # @api.model
    # def create(self, vals):
    #     res = super(ProductTemplate, self).create(vals)
    #     if res.categ_id.product_uom_line_ids:
    #         for rec in res.categ_id.product_uom_line_ids:
    #             if rec.product_uom_id.id == res.uom_id.id:
    #                 res.default_qty = rec.default_qty
    #     # updating product by template
    #     for pr in res.product_variant_ids:
    #         pr.default_qty = res.default_qty
    #     return res

    @api.onchange('categ_id')
    def _onchange_product_cat_code(self):
        for rec in self:
            parent_cat_code = self.get_parent_cat_code(rec.categ_id)
            if rec.categ_id.default_uom_id:
                rec.uom_id = rec.categ_id.default_uom_id.id
            rec.category_code = parent_cat_code[0]
            rec.parent_categ_id = parent_cat_code[1]

    # @api.constrains('name', 'color_id', 'country_id', 'brand', 'style_id', 'customer_id', 'product_group')
    # def _check_unique_constraint_product(self):
    #     for rec in self:
    #         msg = 'Product "%s"' % rec.name
    #         envobj = self.env['product.template']
    #
    #         conditionlist = [('name', '=', rec.name),
    #                          ('color_id', '=', rec.color_id.id if rec.color_id else None),
    #                          ('country_id', '=', rec.country_id.id if rec.country_id else None),
    #                          ('brand', '=', rec.brand.id if rec.brand else None),
    #                          ('style_id', '=', rec.style_id.id if rec.style_id else None),
    #                          ('customer_id', '=', rec.customer_id.id if rec.customer_id else None),
    #                          ('product_group', '=', rec.product_group)
    #                          ]
    #
    #         validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.constrains('product_code')
    def _check_unique_constraint_product_code(self):
        for rec in self:
            if rec.product_code:
            # if rec.product_code:
                msg = 'Product Code "%s"' % rec.product_code
                envobj = self.env['product.template']
                conditionlist = [('id', '!=', rec.id), ('product_code', '=', rec.product_code)]
                # conditionlist = [('id', '!=', rec.id), ('product_code', '=', rec.product_code), ('default_code', '=', rec.default_code),
                #                  ('active', '=', True)]
                validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.constrains('product_old_code')
    def _check_unique_constraint_product_old_code(self):
        for rec in self:
            if rec.product_old_code:
                msg = 'Old Product Code "%s"' % rec.product_old_code
                envobj = self.env['product.template']
                conditionlist = [('id', '!=', rec.id), ('product_old_code', '=', rec.product_old_code)]
                validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    #not used
    # def action_product_approve(self):
    #     search_domain = [('state', '!=', 'cancel'),
    #                      ('create_date', '>', '2023-08-18')]
    #     pro_obj = self.env['product.template'].search(search_domain, order='id asc')
    #     today_date = datetime.datetime.now()
    #     for x in pro_obj:
    #         # print(x.product_code)
    #         x.write_date = today_date


    def get_parent_cat_code(self, categ_id):
        code = ''
        parent_categ_id = None
        #categ_id.parent_id.code
        # need code update to recurtion function
        if categ_id.parent_id:
            p_id1 = categ_id.parent_id
            if not p_id1.parent_id:
                code = p_id1.code
                parent_categ_id = p_id1.id
            else:
                p_id2 = p_id1.parent_id
                if not p_id2.parent_id:
                    code = p_id2.code
                    parent_categ_id = p_id1.id
                else:
                    p_id3 = p_id2.parent_id
                    if not p_id3.parent_id:
                        code = p_id3.code
                        parent_categ_id = p_id1.id
                    else:
                        p_id4 = p_id3.parent_id
                        if not p_id4.parent_id:
                            code = p_id4.code
                            parent_categ_id = p_id1.id
                        else:
                            p_id5 = p_id4.parent_id
                            if not p_id5.parent_id:
                                code = p_id5.code
                                parent_categ_id = p_id1.id
                            else:
                                p_id6 = p_id5.parent_id
                                if not p_id6.parent_id:
                                    code = p_id6.code
                                    parent_categ_id = p_id1.id
        else:
            code = categ_id.code
            parent_categ_id = categ_id.id
        return [code, parent_categ_id]

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    # func name rollback to prv
    def action_confirm(self):
        self.state = 'confirm'

    def action_approve(self):
        for rec in self:
            # if not rec.barcode:
            if rec.product_code:
                count = 1

                for line in rec.product_variant_ids:
                    if line.barcode:
                        continue

                    product_barcode = rec.product_code + str(count).zfill(2)

                    product_code_row = self.env['product.product'].sudo().search(
                        [('barcode', '=', product_barcode), '|', ('active', '=', True), ('active', '=', False)],
                        limit=1)
                    # if product_code_row:
                    #     count += 1
                    #     continue
                    #sequence = int(product_code_row.barcode)

                    while product_code_row:
                        #sequence += 1
                        count += 1
                        #product_barcode = str(sequence)
                        product_barcode = rec.product_code + str(count).zfill(2)

                        product_code_row = self.env['product.product'].sudo().search([('barcode', '=', product_barcode), '|', ('active', '=', True), ('active', '=', False)], limit=1)
                        if not product_code_row:
                            break
                        else:
                            continue

                    #--------
                    line.barcode = product_barcode
                    count += 1

            else:
                raise UserError("Required product code!")
            rec.state = 'approve'

    def name_get(self):
        result = []
        for rec in self:
            ratio_label = dict(rec._fields['ratio_type'].selection).get(rec.ratio_type, '')
            name = '%s (%s)' % (rec.name, ratio_label) if ratio_label else rec.name
            result.append((rec.id, name))
        return result

    def action_regen_barcode(self):
        for rec in self:
            product_obj = self.env['product.product'].sudo().search([('product_tmpl_id', '=', rec.id), '|', ('active', '=', True), ('active', '=', False)], order='barcode asc')
            exist_barcode = ''
            for pp in product_obj:
                if not rec.product_code:
                    raise ValidationError(
                        _("Warning! Required Product Code.")
                    )
                pp_barcode = pp.barcode
                if pp_barcode:
                    exist_barcode = pp_barcode
                    pp.default_code = pp.product_code
                else:
                    if not exist_barcode:
                        exist_barcode = str(rec.product_code) + '00'
                    new_barcode = int(exist_barcode) + 1
                    pp.barcode = new_barcode
                    pp.default_code = pp.product_code
                    exist_barcode = new_barcode

    def action_get_cat_code(self):
        for rec in self:
            categ_id = rec.categ_id
            code = ''
            parent_categ_id = None
            if not rec.category_code or not rec.parent_categ_id:
                # need code update to recursion function
                if categ_id.parent_id:
                    p_id1 = categ_id.parent_id
                    if not p_id1.parent_id:
                        code = p_id1.code
                        parent_categ_id = p_id1.id
                    else:
                        p_id2 = p_id1.parent_id
                        if not p_id2.parent_id:
                            code = p_id2.code
                            parent_categ_id = p_id2.id
                        else:
                            p_id3 = p_id2.parent_id
                            if not p_id3.parent_id:
                                code = p_id3.code
                                parent_categ_id = p_id3.id
                            else:
                                p_id4 = p_id3.parent_id
                                if not p_id4.parent_id:
                                    code = p_id4.code
                                    parent_categ_id = p_id4.id
                                else:
                                    p_id5 = p_id4.parent_id
                                    if not p_id5.parent_id:
                                        code = p_id5.code
                                        parent_categ_id = p_id5.id
                                    else:
                                        p_id6 = p_id5.parent_id
                                        if not p_id6.parent_id:
                                            code = p_id6.code
                                            parent_categ_id = p_id6.id
                else:
                    code = categ_id.code
                    parent_categ_id = categ_id.id
                rec.category_code = code
                rec.parent_categ_id = parent_categ_id

    def action_get_product_code(self):
        for rec in self:
            if not rec.product_code:
                if not rec.category_code or not rec.parent_categ_id:
                    rec.action_get_cat_code()

                if rec.category_code:
                    # last_code_row = self.env['product.template'].search(
                    #     [('category_code', '=', rec.category_code), ('state', '!=', 'draft'),
                    #      ('product_code', '!=', ''), ('is_old_product', '=', False), '|', ('active', '=', True),
                    #      ('active', '=', False)], order='product_code desc',
                    #     limit=1)

                    last_code_row = self.env['product.template'].sudo().search(
                        [('categ_id', 'child_of', rec.parent_categ_id.id),
                         ('product_code', '!=', ''), ('active', '=', True)], order='product_code desc',
                        limit=1)

                    if last_code_row:
                        product_code = str(int(last_code_row[0].product_code) + 1)
                    else:
                        product_code = str(rec.category_code) + str(1).zfill(5)
                    if not rec.product_code:
                        rec.product_code = product_code
                        rec.default_code = product_code

    def action_get_barcode(self):
        for rec in self:
            #if not rec.barcode:
            if rec.product_code:
                count = 1
                for line in rec.product_variant_ids:
                    if line.barcode:
                        continue
                    else:
                        product_barcode = rec.product_code + str(count).zfill(2)

                        product_code_row = self.env['product.product'].sudo().search(
                            [('barcode', '=', product_barcode), '|', ('active', '=', True), ('active', '=', False)],
                            limit=1)

                        while product_code_row:
                            count += 1
                            product_barcode = rec.product_code + str(count).zfill(2)

                            product_code_row = self.env['product.product'].sudo().search(
                                [('barcode', '=', product_barcode), '|', ('active', '=', True), ('active', '=', False)],
                                limit=1)
                            if not product_code_row:
                                break
                            else:
                                continue

                        # --------
                        line.barcode = product_barcode
                        count += 1
