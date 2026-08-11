from odoo import models, exceptions, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError


class MiniProductInventoryAdjustment(models.Model):
    _name = "mini.product.inventory.adjustment"
    _description = "Mini Product Inventory Adjustment"
    _order = 'product_id asc'
    _rec_name = 'product_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    product_id = fields.Many2one('product.product', string='Product', readonly=False, required=True)
    qty = fields.Float()
    location_id = fields.Many2one('stock.location', string='Location',
                                  domain=[('state', '=', 'done')])
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', copy=False, index=True, tracking=24, default='draft')

    def js_python_method(self, model_name, active_id):
        pass

    @api.constrains('qty')
    def _check_qty(self):
        if self.qty:
            if self.qty < .1 or self.qty > .99:
                raise exceptions.ValidationError(_('Qty should be Greater than .1 and less than 1!'))

    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        self.state = 'confirm'

    def adjustment_action_done(self):
        loc_obj = self.env['stock.location'].search([('usage', '=', 'inventory')], limit=1)
        stock_move_obj = self.env['stock.move'].sudo()
        move_vals = {
            'name': 'Inventory Adjustment',
            'product_id': self.product_id.id,
            'product_uom': self.product_id.uom_id.id,
            'product_uom_qty': self.qty,
            'location_id': loc_obj.id,
            'location_dest_id': self.location_id.id,
            'quantity_done': self.qty,
            'date': datetime.today().date(),
            'date_expected': datetime.today().date()
        }
        mo_move_obj = stock_move_obj.create(move_vals)
        mo_move_obj.sudo()._action_done()
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'
