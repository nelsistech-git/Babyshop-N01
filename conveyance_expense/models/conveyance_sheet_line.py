from odoo import models, fields, api


class ConveyanceSheetLine(models.Model):
    _name = 'conveyance.sheet.line'
    _description = 'Conveyance Sheet Line'
    _order = 'date asc, id asc'

    sheet_id = fields.Many2one('conveyance.sheet', string='Conveyance Sheet', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    from_location = fields.Char(string='From', required=True)
    to_location = fields.Char(string='To', required=True)
    purpose = fields.Char(string='Purpose')
    transport = fields.Selection([
        ('rickshaw', 'Rickshaw'),
        ('cng', 'CNG'),
        ('uber', 'Uber'),
        ('bus', 'Bus'),
        ('pathao', 'Pathao'),
        ('metro_rail', 'Metro Rail'),
        ('car', 'Car'),
        ('walked', 'Walked'),
        ('others', 'Others'),
    ], string='Transport', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer')
    conveyance_amount = fields.Float(string='Conveyance Amount', digits=(12, 2))
    others_cost = fields.Char(string='Others Cost')
    amount = fields.Float(string='Amount', digits=(12, 2))
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        digits=(12, 2),
    )
    remarks = fields.Char(string='Remarks')
    food_bill = fields.Float(string='Food Bill' , digits=(12, 2))

    @api.depends('conveyance_amount', 'amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.conveyance_amount + rec.food_bill + rec.amount