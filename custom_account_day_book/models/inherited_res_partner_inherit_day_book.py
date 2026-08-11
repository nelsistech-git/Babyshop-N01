from odoo import fields, models, _


class InheritResPartnerDayBook(models.Model):
    _inherit = "res.partner"
    _description = "Inherited Res Partner"

    customer_advance_account_id = fields.Many2one('account.account', string="Customer Advance Account",
                                                  domain="[('account_type', '!=', 'view'), ('is_cus_adv_ledger', '=', True)]",
                                                  default=lambda self: self.env['account.account'].search(
                                                      [('is_default_cus_adv', '=', True)], limit=1))
    vendor_advance_account_id = fields.Many2one('account.account', string="Vendor Advance Account",
                                                domain="[('account_type', '!=', 'view'), ('is_vendor_adv_ledger', '=', True)]",
                                                default=lambda self: self.env['account.account'].search(
                                                    [('is_default_vendor_adv', '=', True)], limit=1))
