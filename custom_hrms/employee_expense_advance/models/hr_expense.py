# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class HrExpense(models.Model):
    _inherit = "hr.expense"
    
    @api.depends('custom_advance_expense_id', 'custom_advance_expense_id.total_amount')
    def _compute_advance_expense_id(self):
        for rec in self:
            amount = 0.0
            amount = rec.custom_advance_expense_id.total_amount
            rec.custom_advance_amount = amount
            print("rec.custom_advance_amount")
    
    custom_advance_expense_id = fields.Many2one(
        'advance.expense.line', 
        string='Expense Advance', 
        copy=False
    )
    custom_advance_amount = fields.Float(
        string='Advance Amount', 
        compute='_compute_advance_expense_id', 
        store=True
    )
    custom_advance_currency_id = fields.Many2one(
        'res.currency', 
        string='Expense Advance Currency', 
        related='custom_advance_expense_id.currency_id',
        store=True,
    )
    
    # @api.multi
    # def submit_expenses(self): # Override Odoo method.
    def action_submit_expenses(self):
        result = super(HrExpense, self).action_submit_expenses()
        for rec in self:
            if rec.custom_advance_expense_id:
                rec.custom_advance_expense_id.reambursment = True
        return result
    

