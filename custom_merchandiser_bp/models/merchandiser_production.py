from odoo import models, fields, api

class MerchandiserProduction(models.Model):
    _name = 'merchandiser.production'
    _description = 'Production Tracking'
    _rec_name = 'order_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection([
        ('order_confirm', 'Order Confirm'),
        ('material_receive', 'Material Receive'),
        ('cutting', 'Cutting'),
        ('sewing', 'Sewing'),
        ('finishing', 'Finishing'),
        ('packing', 'Packing'),
        ('shipment', 'Shipment'),
    ], string='Production Stage', default='order_confirm', tracking=True)

    order_id = fields.Many2one(
        'merchandiser.order', string="Order Reference",
        required=True, ondelete='cascade'
    )
    buyer_id = fields.Many2one(
        'res.partner', string="Buyer",
        related='order_id.buyer_id', store=True, readonly=True
    )
    style_no = fields.Char(
        string="Style No",
        related='order_id.style_no', store=True, readonly=True
    )
    order_qty = fields.Float(
        string="Order Qty",
        related='order_id.order_qty', store=True, readonly=True
    )
    shipment_date = fields.Date(
        string="Target Shipment Date",
        related='order_id.shipment_date', store=True, readonly=True
    )

    order_confirm_date = fields.Date(string="Order Confirm Date")
    material_receive_date = fields.Date(string="Material Receive Date")
    cutting_date = fields.Date(string="Cutting Start Date")
    sewing_date = fields.Date(string="Sewing Start Date")
    finishing_date = fields.Date(string="Finishing Start Date")
    packing_date = fields.Date(string="Packing Start Date")
    shipment_actual_date = fields.Date(string="Actual Shipment Date")

    material_receive_qty = fields.Float(string="Material Received Qty")
    cutting_qty = fields.Float(string="Cutting Qty")
    sewing_qty = fields.Float(string="Sewing Qty")
    finishing_qty = fields.Float(string="Finishing Qty")
    packing_qty = fields.Float(string="Packing Qty")
    shipment_qty = fields.Float(string="Shipment Qty")

    note = fields.Text(string="Notes")

    def action_to_material_receive(self):
        self.write({
            'state': 'material_receive',
            'order_confirm_date': self.order_confirm_date or fields.Date.today(),
        })

    def action_to_cutting(self):
        self.write({
            'state': 'cutting',
            'material_receive_date': self.material_receive_date or fields.Date.today(),
        })

    def action_to_sewing(self):
        self.write({
            'state': 'sewing',
            'cutting_date': self.cutting_date or fields.Date.today(),
        })

    def action_to_finishing(self):
        self.write({
            'state': 'finishing',
            'sewing_date': self.sewing_date or fields.Date.today(),
        })

    def action_to_packing(self):
        self.write({
            'state': 'packing',
            'finishing_date': self.finishing_date or fields.Date.today(),
        })

    def action_to_shipment(self):
        self.write({
            'state': 'shipment',
            'packing_date': self.packing_date or fields.Date.today(),
            'shipment_actual_date': self.shipment_actual_date or fields.Date.today(),
        })
