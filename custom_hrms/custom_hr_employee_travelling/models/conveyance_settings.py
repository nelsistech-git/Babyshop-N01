from odoo import models, fields, api


class HrConveyanceSettings(models.Model):
    _name = 'hr.conveyance.settings'
    _description = 'Conveyance Settings'
    _rec_name = "purpose"
    _order = "id desc"

    conveyance_type = fields.Selection([
        ('tc', 'Travel & Conveyance'),
        ('ef', 'Entertainment & Food Allowance'),
        ('iou', 'IOU')
    ], string="Type", copy=False)

    purpose = fields.Char(string="Purpose")
    journal_id = fields.Many2one('account.journal', string='Journal')
    debit_account_id = fields.Many2one('account.account', 'Debit Account',
                                       domain="[('account_type', '!=', 'view')]")
    credit_account_id = fields.Many2one('account.account', 'Credit Account',
                                        domain="[('account_type', '!=', 'view')]")
    is_active = fields.Boolean(string='Is Active?')
