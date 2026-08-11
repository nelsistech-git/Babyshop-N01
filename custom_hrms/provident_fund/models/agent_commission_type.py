from odoo import models, fields


class AgentCommissionType(models.Model):
    _name = "agent.commission.type"
    _description = " Account Type"

    name = fields.Char(string='Name', required=True)
    type_account_id = fields.Many2one('account.account', string='Type Account', ondelete='restrict', required=True,
                                      domain="[('account_type', '=', 'income')]", change_default=True)
    remarks = fields.Text(string='Remarks')
    active = fields.Boolean(default=True)
