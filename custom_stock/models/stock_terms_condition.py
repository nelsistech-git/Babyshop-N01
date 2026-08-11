from odoo import api, exceptions, fields, models
from odoo.addons.helper import validator
import re


class StockTermCondition(models.Model):
    _name = "stock.terms.condition"
    _description = "Stock Terms Condition"

    name = fields.Char(string="Title", required=True, size=120, help="Title can be maximum 120 characters")
    description = fields.Html(string="Description",
                              help=" * $total_amount: Total purchase order amount.\n"
                                   " * $convert_total: Total purchase order amount text.\n"
                                   " * $vat_type: Vat Type means Inclusive or Exclusive.\n"
                                   " * $advanced_pay: Advanced Paid amount (%).\n"
                                   " * $payment_by: Payment By Cash or Cheque.\n"
                                   " * $delivery_date: Delivery Date\n"
                                   " * $supplier_name: Supplier Name."
                              )
    active = fields.Boolean(default=True)

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()

    @api.constrains('name')
    def _check_unique_constraint(self):
        msg = "Title"
        envObj = self.env['stock.terms.condition']
        conditionList = [('name', '=ilike', self.name), '|', ('active', '=', True), ('active', '=', False)]

        validator.check_duplicate_value(self, envObj, conditionList, msg)

    @api.constrains('description')
    def _check_stock_termscondition_description_length(self):
        limit = 10000
        record = self.description
        field_name = "Description"
        validator._check_length_with_clean_htmltag(self, record, limit, field_name)