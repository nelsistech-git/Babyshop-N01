from odoo import models, fields, api, _
import odoo.addons.decimal_precision as dp
from datetime import datetime, timedelta
from odoo.exceptions import UserError


class ComparisonReportCategory(models.Model):
    _name = 'comparison.report.category'
    _order="sequence"


    name = fields.Char("Account Category")
    sequence = fields.Integer("Sequence")
    calculation = fields.Selection([('cumulative',"Cumulative"),('different','Differentiated')], string="Calulation Type")
    account_type = fields.Selection([('asset',"Asset"),('liability','Liability'),('income','Income'),('expense','Expense'),('pl','Profit-Loss')], string="Account Group")
    account_ids = fields.Many2many('account.account', string="Accounts")
    entry_type = fields.Selection([('in','IN'),('out','OUT'),('both','IN & OUT')], string="Entry Type", default='both')
    user_type_id = fields.Many2many('account.account.type', string="Account Type")
    config_type = fields.Selection([('account','Account Wise'),('type','Account Type Wise')], string="Config Type", default='account')