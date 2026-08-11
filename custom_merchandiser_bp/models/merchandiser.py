from odoo import models, fields, api

class MerchandiserInfo(models.Model):
    _name = 'merchandiser.info'
    _description = 'Merchandiser Information'
    _rec_name = 'style_no'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection([
        ('draft', 'Draft'),
        ('costing_management', 'Costing Management'),
        ('sample_created', 'Sample Created'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    partner_id = fields.Many2one(
        'res.partner', string='Buyer Name',
        domain="[('is_company', '=', True)]", tracking=True
    )
    brand = fields.Char(string="Brand")
    country = fields.Char(string="Country")
    email = fields.Char(string="Email")
    shipment_terms = fields.Char(string="Shipment Terms")
    contact_person_id = fields.Many2one('res.partner', string='Contact Person')

    style_no = fields.Char(string="Style No", required=True)
    item_id = fields.Many2one('product.template', string='Product from Inventory')

    fabric_type = fields.Char(
        string="Fabric Type", related='item_id.fabric_type', readonly=False
    )
    gsm = fields.Char(string="GSM", related='item_id.gsm', readonly=False)
    color = fields.Char(string="Color", related='item_id.color', readonly=False)
    size_range = fields.Char(
        string="Size Range", related='item_id.size_range', readonly=False
    )

    tech_pack_attachment = fields.Binary(
        string="Tech Pack Attachment", attachment=True
    )
    tech_pack_name = fields.Char(string="File Name")

    costing_product_id = fields.Many2one('product.product', string='Product')
    bom_qty = fields.Float(string='Quantity', default=1.0)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company
    )

    costing_line_ids = fields.One2many(
        'merchandiser.costing.line', 'merchandiser_id', string='Components'
    )
    profit_percentage = fields.Float(string='Profit (%)', default=0.0)
    total_component_cost = fields.Float(
        string='Total Cost', compute='_compute_total_price', store=True
    )
    final_total_price = fields.Float(
        string='Total Price', compute='_compute_total_price', store=True
    )
    costing_note = fields.Text(string="Notes")

    sample_ids = fields.One2many(
        'merchandiser.sample', 'merchandiser_info_id', string="Samples"
    )
    sample_count = fields.Integer(compute='_compute_sample_count', string="Samples")

    @api.depends('sample_ids')
    def _compute_sample_count(self):
        for rec in self:
            rec.sample_count = len(rec.sample_ids)

    @api.depends('costing_line_ids.subtotal', 'profit_percentage')
    def _compute_total_price(self):
        for rec in self:
            total_cost = sum(line.subtotal for line in rec.costing_line_ids)
            rec.total_component_cost = total_cost
            rec.final_total_price = total_cost + (total_cost * (rec.profit_percentage / 100.0))

    def action_confirm_costing(self):
        self.state = 'costing_management'

    def action_create_sample(self):
        self.ensure_one()
        self.state = 'sample_created'
        return {
            'name': 'Create Sample',
            'type': 'ir.actions.act_window',
            'res_model': 'merchandiser.sample',
            'view_mode': 'form',
            'context': {
                'default_merchandiser_info_id': self.id,
                'default_buyer_id': self.partner_id.id if self.partner_id else False,
                'default_style_no': self.style_no,
                'default_fabric_type': self.fabric_type,
                'default_gsm': self.gsm,
                'default_color': self.color,
                'default_unit_price': self.final_total_price,
            },
            'target': 'current',
        }

    def action_view_samples(self):
        self.ensure_one()
        return {
            'name': 'Samples',
            'type': 'ir.actions.act_window',
            'res_model': 'merchandiser.sample',
            'view_mode': 'tree,form',
            'domain': [('merchandiser_info_id', '=', self.id)],
            'context': {'default_merchandiser_info_id': self.id},
        }

    def action_cancel(self):
        self.state = 'cancel'

    def action_draft(self):
        self.state = 'draft'


class MerchandiserCostingLine(models.Model):
    _name = 'merchandiser.costing.line'
    _description = 'Costing Components Line'

    merchandiser_id = fields.Many2one(
        'merchandiser.info', string='Reference', ondelete='cascade'
    )
    product_id = fields.Many2one('product.product', string='Component', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_price = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_price = self.product_id.standard_price
