from odoo import fields, models

class InheritedAccountMoveInheritCustomSaleIndividual(models.Model):
    _inherit = 'account.move'

    base_id = fields.Many2one('region.list', string='Region (Base)', domain="[('type', '=', 'base')]")
    # cost_center_id = fields.Many2one('acc.cost.center', string='Cost Center')

    # @api.onchange('date')
    # def on_change_account_date(self):
    #     if self.date:
    #         if not self.env.user.has_group('custom_common_settings.group_account_previous_date_entry'):
    #             current_date = datetime.now().date()
    #             given_date = self.date if self.date else None
    #
    #             if given_date and given_date < current_date:
    #                 raise UserError("Error: Given date cannot be less than the current date.")


# class InheritedAccountMoveLineInheritCommonSettings(models.Model):
#     _inherit = "account.move.line"
#     _description = "Account Move Line Inherit common settings"
#
#     cost_center_id = fields.Many2one('acc.cost.center', string='Cost Center')
