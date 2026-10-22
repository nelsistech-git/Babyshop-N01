# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Chart of Accounts (SRS section 7) — garment.account. A lightweight,
garment-industry-categorized account list for internal reporting on top
of this module. For statutory bookkeeping, use Odoo's standard
account.account (Accounting app) — this model does not replace it.
"""
from odoo import fields, models


class GarmentAccount(models.Model):
    _name = 'garment.account'
    _description = 'Garment Chart of Account'
    _order = 'code'

    code = fields.Char(string='Account Code', required=True)
    name = fields.Char(string='Account Name', required=True)
    account_type = fields.Selection([
        ('asset', 'Assets'), ('liability', 'Liabilities'), ('income', 'Income'), ('expense', 'Expenses'),
    ], string='Account Type', required=True)
    account_group = fields.Selection([
        ('cash', 'Cash'), ('bank', 'Bank'), ('inventory', 'Inventory'), ('machinery', 'Machinery'),
        ('factory_equipment', 'Factory Equipment'), ('supplier_payable', 'Supplier Payable'),
        ('bank_loan', 'Bank Loan'), ('lc_liability', 'LC Liability'), ('export_sales', 'Export Sales'),
        ('local_sales', 'Local Sales'), ('service_income', 'Service Income'), ('raw_material_cost', 'Raw Material Cost'),
        ('production_cost', 'Production Cost'), ('salary', 'Salary'), ('utility', 'Utility'),
        ('maintenance', 'Maintenance'), ('other', 'Other'),
    ], string='Account Group')
    account_move_id = fields.Many2one('account.account', string='Linked GL Account',
                                       help='Optional link to the real Odoo Accounting chart of accounts.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Account Code must be unique!'),
    ]
