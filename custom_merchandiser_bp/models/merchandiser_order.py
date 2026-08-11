from odoo import models, fields, api

class MerchandiserOrder(models.Model):
    _name = 'merchandiser.order'
    _description = 'Merchandiser Order'
    _rec_name = 'order_no'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Order Confirmed'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    order_no = fields.Char(
        string="Order No", required=True, copy=False,
        readonly=True, default='New'
    )
    po_number = fields.Char(string="PO Number", tracking=True)
    buyer_id = fields.Many2one('res.partner', string="Buyer", tracking=True)
    style_no = fields.Char(string="Style No")
    order_date = fields.Date(string="Order Date", default=fields.Date.context_today)
    shipment_date = fields.Date(string="Shipment Date", tracking=True)
    fabric_type = fields.Char(string="Fabric Type")
    shipment_mode = fields.Selection([
        ('sea', 'Sea'),
        ('air', 'Air'),
        ('road', 'Road'),
    ], string="Shipment Mode")
    port = fields.Char(string="Port")
    destination = fields.Char(string="Destination")
    incoterm = fields.Char(string="Incoterm")
    payment_term = fields.Char(string="Payment Term")
    lc_no = fields.Char(string="LC No")

    color = fields.Char(string="Color")
    size_range = fields.Char(string="Size Range")
    order_qty = fields.Float(string="Order Qty", default=1.0)
    unit_price = fields.Float(string="Unit Price")
    currency_id = fields.Many2one(
        'res.currency', string="Currency",
        default=lambda self: self.env.company.currency_id
    )
    total_amount = fields.Float(
        string="Total Amount", compute="_compute_total_amount", store=True
    )

    sample_id = fields.Many2one('merchandiser.sample', string="Sample Reference")

    purchase_order_ids = fields.Many2many(
        'purchase.order',
        'merchandiser_order_purchase_rel',
        'merch_order_id',
        'purchase_id',
        string="Purchase Orders",
    )
    purchase_count = fields.Integer(
        string="Purchase Orders", compute='_compute_purchase_count'
    )

    production_ids = fields.One2many(
        'merchandiser.production', 'order_id', string="Production"
    )
    production_count = fields.Integer(
        string="Production", compute='_compute_production_count'
    )

    @api.depends('order_qty', 'unit_price')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.order_qty * rec.unit_price

    @api.depends('purchase_order_ids')
    def _compute_purchase_count(self):
        for rec in self:
            rec.purchase_count = len(rec.purchase_order_ids)

    @api.depends('production_ids')
    def _compute_production_count(self):
        for rec in self:
            rec.production_count = len(rec.production_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('order_no', 'New') == 'New':
                vals['order_no'] = (
                    self.env['ir.sequence'].next_by_code('merchandiser.order') or 'New'
                )
        return super().create(vals_list)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_cancel(self):
        self.state = 'cancel'

    def action_draft(self):
        self.state = 'draft'

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.purchase_order_ids.ids)],
        }

    def action_create_production(self):
        self.ensure_one()
        production = self.env['merchandiser.production'].create({
            'order_id': self.id,
            'order_confirm_date': fields.Date.today(),
        })
        return {
            'name': 'Production',
            'type': 'ir.actions.act_window',
            'res_model': 'merchandiser.production',
            'view_mode': 'form',
            'res_id': production.id,
            'target': 'current',
        }

    def action_view_productions(self):
        self.ensure_one()
        return {
            'name': 'Production',
            'type': 'ir.actions.act_window',
            'res_model': 'merchandiser.production',
            'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }
