import odoo.addons.decimal_precision as dp

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare

class AdvanceExpenseLine(models.Model):
    _name = "advance.expense.line"
    _description = "Advance Expense Line"
    
    @api.depends('unit_amount','quantity')
    def _compute_total_line_expense(self):
        for rec in self:
            amount_line = rec.unit_amount * rec.quantity
            rec.total_amount = amount_line

    product_id = fields.Many2one('product.product', string='Expense')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]}, default=lambda self: self.env['uom.uom'].search([], limit=1, order='id'))
    unit_amount = fields.Float(string='Unit Price',required=True,digits=dp.get_precision('Product Price'))
    quantity = fields.Float(required=True,digits=dp.get_precision('Product Unit of Measure'), default=1)
    description = fields.Char(string='Description', required=True)
    total_amount = fields.Float(string='Subtotal', compute='_compute_total_line_expense', digits=dp.get_precision('Account'))
    currency_id = fields.Many2one('res.currency', string='Currency', related = 'advance_line_id.currency_id', readonly=True, store=True)
    # expense_line_ids = fields.One2many('hr.expense', 'sheet_id', string='Expense Lines', copy=False)
    advance_line_id = fields.Many2one('employee.advance.expense', string="Advance Expense Report")
    employee_id = fields.Many2one('hr.employee', required=True, string="Employee", related = 'advance_line_id.employee_id')
    name = fields.Char(
        string='Number',
        related = 'advance_line_id.name',
        readonly=1,
    )
    state = fields.Selection(
        related = 'advance_line_id.state',
    )
    reambursment = fields.Boolean(
        string='Reimbursement',
        default=False,
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            rec.description = rec.product_id.name
            if rec.advance_line_id.company_id.currency_id != rec.advance_line_id.currency_id:
                amount = rec.advance_line_id.company_id.currency_id._convert(rec.product_id.standard_price, rec.advance_line_id.currency_id)

                # amount = rec.advance_line_id.company_id.currency_id.compute(rec.product_id.standard_price, rec.advance_line_id.currency_id)
                rec.unit_amount = amount
            else:
                rec.unit_amount = rec.product_id.standard_price


