from odoo import models, fields


# Res User Inherit
class UsersInherit(models.Model):
    _inherit = "res.users"
    _description = "Res Users Inherit to add Operation Type"

    operation_types = fields.Many2one('stock.picking.type', string='Operation Types', ondelete="restrict")
    # note: state is in custom_stock module, so it's not available here
    # work_location_id = fields.Many2one('stock.location', string='Work Location', ondelete="restrict", domain="[('usage', '=', 'internal'),('state', '=', 'done')]")
    # src_location_id = fields.Many2one('stock.location', string='Source Location', ondelete="restrict", domain="[('usage', '=', 'internal'),('state', '=', 'done')]")
    user_work_location_id = fields.Many2one('stock.location', string='Work Location', ondelete="restrict")
    work_location_id = fields.Many2one(string="Work Place")
    src_location_id = fields.Many2one('stock.location', string='Source Location', ondelete="restrict",
                                      domain="[('usage', '=', 'internal')]")
    is_purchaser = fields.Boolean(string='Purchaser', default=False)
