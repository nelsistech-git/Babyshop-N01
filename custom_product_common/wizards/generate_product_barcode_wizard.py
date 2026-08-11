from odoo import fields, models


class GenerateProductBarcodeWizard(models.TransientModel):
    _name = "generate.product.barcode.wizard"
    _description = "Generate Product Barcode Wizard"

    report_type = fields.Selection([
        ('category_code', 'Category Code'),
        ('product_code', 'Product Code'),
    ], string='Report Type', required=True, default='category_code')

    def action_generate(self):
        report_type = self.report_type

        if report_type == 'category_code':
            product_tmpl_obj = self.env['product.template'].search(['|',('category_code', 'in', (False, '')),('parent_categ_id', '=', False)], order='id ASC', limit=10000)
            for rec in product_tmpl_obj:
                try:
                    if not rec.category_code or not rec.parent_categ_id:
                        rec.action_get_cat_code()
                except:
                    continue
        else:
            product_tmpl_obj = self.env['product.template'].search([('state', '!=', 'draft'), ('category_code', 'not in', (False, '')), ('product_code', 'in', (False, ''))], limit=1000, order='id ASC')
            for rec in product_tmpl_obj:
                try:
                    # if not rec.category_code:
                    #     rec.action_get_cat_code()
                    if not rec.product_code:
                        rec.action_get_product_code()
                    if not rec.barcode:
                        rec.action_get_barcode()
                    rec.state = 'approve'
                    if rec.product_variant_ids.filtered(lambda x: x.barcode == False):
                        rec.action_regen_barcode()
                except:
                    continue
