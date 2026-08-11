from odoo import models, fields, api, exceptions


class CourierPartner(models.Model):
    _name = 'courier.partner'
    _description = 'Courier Partner'
    _order = 'name'

    name = fields.Char(string='Courier Name', required=True)
    active = fields.Boolean(default=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_type = fields.Selection([
        ('hole_sale', 'Wholesale'),
        ('depot', 'Depo'),
        ('dealer', 'Dealer'),
        ('corporate', 'Corporate'),
        ('vip', 'VIP'),
    ], string='Customer Type')

    customer_location = fields.Selection([
        ('local', 'Local'),
        ('foreign', 'Foreign'),
    ], string='Local/Foreign', default='local')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_type = fields.Selection([
        ('hole_sale', 'Wholesale'),
        ('depot', 'Depo'),
        ('dealer', 'Dealer'),
        ('corporate', 'Corporate'),
        ('vip', 'VIP'),
    ], string='Customer Type', compute='_compute_partner_custom_fields', store=True)

    customer_location = fields.Selection([
        ('local', 'Local'),
        ('foreign', 'Foreign'),
    ], string='Customer Location', compute='_compute_partner_custom_fields', store=True)

    sales_type = fields.Selection([
        ('normal', 'Normal'),
        ('condition', 'Condition'),
    ], string='Sales Type')

    courier_id = fields.Many2one(
        'courier.partner',
        string='Courier Name',
    )

    courier_condition = fields.Selection([
        ('cod', 'Cash on Delivery'),
        ('prepaid', 'Prepaid'),
    ], string='Condition')

    courier_slip_no = fields.Char(string='Slip Number')

    partner_address = fields.Char(
        string='Address',
        compute='_compute_partner_address',
        store=True,
    )

    discount = fields.Float(string='Discount (%)', digits=(5, 2))

    @api.depends('partner_id')
    def _compute_partner_address(self):
        for rec in self:
            if rec.partner_id:
                parts = list(filter(None, [
                    rec.partner_id.street,
                    rec.partner_id.street2,
                    rec.partner_id.city,
                    rec.partner_id.country_id.name,
                ]))
                rec.partner_address = ', '.join(parts)
            else:
                rec.partner_address = ''

    @api.depends('partner_id')
    def _compute_partner_custom_fields(self):
        for rec in self:
            if rec.partner_id:
                rec.customer_type = rec.partner_id.customer_type
                rec.customer_location = rec.partner_id.customer_location
            else:
                rec.customer_type = False
                rec.customer_location = False

    @api.onchange('discount')
    def _onchange_discount(self):
        if self.discount:
            for line in self.order_line:
                line.discount = self.discount
        else:
            for line in self.order_line:
                line.discount = 0.0


# ============================================================
# ACCOUNT MOVE (INVOICE) CUSTOM FIELDS — Optional (Not Mandatory)
# ============================================================
class AccountMove(models.Model):
    _inherit = 'account.move'

    # --- Bank Details  ---
    bank_account_name = fields.Char(string='Account Name')
    bank_name = fields.Char(string='Bank Name')
    bank_account_no = fields.Char(string='Account No.')
    bank_branch = fields.Char(string='Branch')
    bank_routing_no = fields.Char(string='Routing No.')

    # --- Invoice Report Custom Fields (Optional — Not Mandatory) ---
    labor_charge = fields.Monetary(
        string='Labor Charge',
        currency_field='currency_id',
        default=0.0,
        help='Add labor charge if applicable',
    )
    delivery_charge = fields.Monetary(
        string='Delivery Charge',
        currency_field='currency_id',
        default=0.0,
        help='Add delivery charge if applicable',
    )
    lab_test_charge = fields.Monetary(
        string='Lab Test Charge',
        currency_field='currency_id',
        default=0.0,
        help='Add lab test charge if applicable',
    )
    advance_paid = fields.Monetary(
        string='Advance Paid',
        currency_field='currency_id',
        default=0.0,
        help='Add advance paid amount if applicable',
    )
    discount_vat = fields.Monetary(
        string='Discount on VAT',
        currency_field='currency_id',
        default=0.0,
        help='Add VAT discount if applicable',
    )
    discount_lab_test = fields.Monetary(
        string='Discount Lab Test',
        currency_field='currency_id',
        default=0.0,
        help='Add lab test discount if applicable',
    )
    # --- VAT % field ---
    vat_percent = fields.Float(
        string='VAT (%)',
        digits=(5, 2),
        default=5.0,
        help='VAT percentage for invoice',
    )

    # --- Terms & Conditions (Optional) ---
    terms_conditions = fields.Text(
        string='Terms & Conditions',
        help='Add terms and conditions if applicable',
    )

    # --- Computed Fields for Report ---
    sub_total = fields.Monetary(
        string='Sub Total',
        currency_field='currency_id',
        compute='_compute_invoice_totals',
        store=True,
    )
    total_before_discount = fields.Monetary(
        string='Total Before Discount',
        currency_field='currency_id',
        compute='_compute_invoice_totals',
        store=True,
    )
    total_after_discount = fields.Monetary(
        string='Total After Discount',
        currency_field='currency_id',
        compute='_compute_invoice_totals',
        store=True,
    )
    total_due_amount = fields.Monetary(
        string='Total Due Amount',
        currency_field='currency_id',
        compute='_compute_invoice_totals',
        store=True,
    )

    @api.depends('amount_untaxed', 'amount_tax', 'labor_charge',
                 'delivery_charge', 'lab_test_charge', 'discount_vat',
                 'discount_lab_test', 'advance_paid', 'vat_percent')
    def _compute_invoice_totals(self):
        for move in self:
            # Sub Total = Untaxed Amount
            move.sub_total = move.amount_untaxed

            # Total Before Discount = Untaxed + VAT + Extra Charges
            move.total_before_discount = (
                    move.amount_untaxed +
                    move.amount_tax +
                    move.labor_charge +
                    move.delivery_charge +
                    move.lab_test_charge
            )

            # Total After Discount
            move.total_after_discount = (
                    move.total_before_discount -
                    move.discount_vat -
                    move.discount_lab_test
            )

            # Total Due = After Discount - Advance Paid
            move.total_due_amount = move.total_after_discount - move.advance_paid

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    line_details = fields.Text(string='Details')
    type = fields.Char(string='Type', compute='_compute_product_attributes', store=True)
    color = fields.Char(string='Color', compute='_compute_product_attributes', store=True)

    @api.depends('product_id')
    def _compute_product_attributes(self):
        for line in self:
            if line.product_id:
                line.type = line.product_id.categ_id.name or ''
                color_value = line.product_id.product_template_attribute_value_ids.filtered(
                    lambda v: v.attribute_id.name.lower() == 'color'
                )
                line.color = color_value[0].name if color_value else ''
            else:
                line.type = ''
                line.color = ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order_id = vals.get('order_id')
            if order_id:
                order = self.env['sale.order'].browse(order_id)
                if order.exists() and order.discount:
                    vals['discount'] = order.discount
        return super().create(vals_list)

    @api.onchange('product_id')
    def _onchange_product_id_clear_description(self):
        if self.product_id:
            self.name = self.product_id.name