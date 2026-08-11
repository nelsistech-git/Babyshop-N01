from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.helper import validator


class InheritedProductCategoryInheritCustomProductCommon(models.Model):
    _inherit = "product.category"

    code = fields.Char(string="Code", size=2)
    default_qty = fields.Float(string="Default Quantity", default=1)
    product_uom_line_ids = fields.One2many('product.category.uom', 'category_id', string='Default Quantity')
    default_uom_id = fields.Many2one('uom.uom', string='Default UOM')
    last_product_code = fields.Char(string='Product Code')
    is_saleable = fields.Boolean(string='Is Saleable?', default=False)

    def write(self, vals):
        res = super(InheritedProductCategoryInheritCustomProductCommon, self).write(vals)
        if self.product_uom_line_ids:
            for pc in self.product_uom_line_ids:
                product_tmpl = self.env['product.template'].search(
                    [('categ_id', '=', self.id), ('uom_id', '=', pc.product_uom_id.id)]).ids
                if product_tmpl:
                    self.env.cr.execute("UPDATE product_template SET default_qty = %s where id in %s",
                                        (pc.default_qty, tuple(product_tmpl)))
                    self.env.cr.execute("UPDATE product_product SET default_qty = %s where product_tmpl_id in %s",
                                        (pc.default_qty, tuple(product_tmpl)))
        # if self.default_qty:
        #     product_tmpl = self.env['product.template'].search([('categ_id', '=', self.id)])
        #     tmpl_ids = []
        #     for rec in product_tmpl:
        #         rec.default_qty = self.default_qty
        #         tmpl_ids.append(rec.id)
        #
        #     product_product = self.env['product.product'].search([('product_tmpl_id', 'in', tmpl_ids)])
        #     for pr in product_product:
        #         pr.default_qty = self.default_qty

        return res

    def action_get_last_product_code(self):
        last_code_row = self.env['product.template'].search(
            [('categ_id', 'child_of', self.id),
             ('state', '!=', 'draft'),
             ('product_code', '!=', ''), '|', ('active', '=', True),
             ('active', '=', False)], order='product_code desc',
            limit=1)
        self.last_product_code = last_code_row.product_code
    # _sql_constraints = [
    #     ('code', 'unique (code)', 'The Category ID already Exists!'),
    # ]

    @api.constrains('code', 'name')
    def _check_unique_constraint_category_code(self):
        for rec in self:
            if rec.code:
                msg = 'Category Code "%s"' % rec.code
                envobj = self.env['product.category']
                conditionlist = [('code', '=', rec.code)]
                validator.check_duplicate_value(rec, envobj, conditionlist, msg)
            # if rec.name:
            #     msg = 'Category Name "%s"' % rec.name
            #     envobj = self.env['product.category']
            #     conditionlist = [('name', '=', rec.name)]
            #     validator.check_duplicate_value(rec, envobj, conditionlist, msg)


class ProductUOMCategory(models.Model):
    _name = "product.category.uom"
    _description = "Product Category UOM"

    category_id = fields.Many2one('product.category')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    default_qty = fields.Float(string="Default Quantity", default=1)

    @api.constrains('product_uom_id', 'category_id')
    def _check_unique_constraint_product_uom_id(self):
        for rec in self:
            msg = 'UoM "%s"' % rec.product_uom_id.name
            envobj = self.env['product.category.uom']
            conditionlist = [('product_uom_id', '=', rec.product_uom_id.id), ('category_id', '=', rec.category_id.id)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)
