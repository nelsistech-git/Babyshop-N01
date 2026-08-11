from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression


class InheritedAccountMoveInheritHRPayroll(models.Model):
    _inherit = "account.move"
    _description = "Account Move Inherit"

    fs_dept = fields.Selection([
        ('accounts', 'Accounts'),
        ('pf', 'PF')
    ], string='FS Department', default='accounts')


class InheritedAccountMoveLineInheritHRPayroll(models.Model):
    _inherit = "account.move.line"
    _description = "Account Move Line Inherit"

    fs_dept = fields.Selection(related='move_id.fs_dept')