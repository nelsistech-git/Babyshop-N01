from odoo import api, fields, models
from odoo.exceptions import UserError
import base64
import os


class BdBarcodeLabelWizard(models.TransientModel):
    _name = 'bd.barcode.label.wizard'
    _description = 'Generate Barcode Wizard'

    """brand = fields.Many2one(
        'res.company',
        string='Brand',
        required=True,
        default=lambda self: self.env.company,
    )"""
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    name = fields.Char(
        string='Product Name',
        related='product_id.name',
        readonly=True,
    )
    barcode = fields.Char(
        string='Barcode',
        related='product_id.barcode',
        readonly=True,
    )
    categ_id = fields.Many2one(
        'product.category',
        string='Category',
        related='product_id.categ_id',
        readonly=True,
    )
    sale_price = fields.Float(
        string='Sale Price',
        related='product_id.list_price',
        readonly=True,
    )
    ratio_type = fields.Selection(
        related='product_id.product_tmpl_id.ratio_type',
        string='Ratio Type',
        readonly=True,
    )
    print_quantity = fields.Integer(string='Print Quantity', default=1)
    per_sku_qty = fields.Integer(string='Per SKU Qty', default=1)

    def _get_fixed_logo_src(self):
        """Load fixed logo from static folder as base64."""
        try:
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logo_path = os.path.join(module_path, 'static', 'img', 'bluedream_bm.png')
            with open(logo_path, 'rb') as f:
                logo_b64 = base64.b64encode(f.read()).decode('utf-8')
            return 'data:image/png;base64,' + logo_b64
        except Exception:
            return False

    def action_generate_barcode(self):
        self.ensure_one()
        #if not self.brand:
            #raise UserError('Please select a Brand.')
        if not self.product_id:
            raise UserError('Please select a product.')
        if not self.barcode:
            raise UserError(
                'Selected product does not have a barcode. '
                'Please set a barcode on the product first.'
            )
        if self.print_quantity <= 0:
            raise UserError('Print Quantity must be greater than 0.')
        if self.per_sku_qty <= 0:
            raise UserError('Per SKU Qty must be greater than 0.')

        # Fixed logo from static folder
        brand_logo_src = self._get_fixed_logo_src()

        # Barcode image as base64
        barcode_src = False
        try:
            barcode_image = self.env['ir.actions.report'].barcode(
                'Code128', self.barcode, width=400, height=60,
                humanreadable=False
            )
            b64 = base64.b64encode(barcode_image).decode('utf-8')
            barcode_src = 'data:image/png;base64,' + b64
        except Exception:
            barcode_src = False

        label_list = []
        for i in range(self.print_quantity):
            label_list.append({
                'product_name': self.name or '',
                'barcode': self.barcode or '',
                'barcode_src': barcode_src,
                'sale_price': self.sale_price,
                'per_sku_qty': self.per_sku_qty,
                'brand_logo_src': brand_logo_src,
                'ratio_type': dict(
                    self._fields['ratio_type']._description_selection(self.env)
                ).get(self.ratio_type, '') if self.ratio_type else '',
            })

        data = {
            'label_list': label_list,
            'print_quantity': self.print_quantity,
        }

        return self.env.ref(
            'custom_generate_barcode_label.action_bd_barcode_label_report'
        ).report_action(self, data={'data': data})