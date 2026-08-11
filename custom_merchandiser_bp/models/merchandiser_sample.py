from odoo import models, fields, api

class MerchandiserSample(models.Model):
    _name = 'merchandiser.sample'
    _description = 'Sample and Courier Management'
    _rec_name = 'sample_no'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection([
        ('sample', 'Sample Details'),
        ('courier', 'Courier Info'),
        ('feedback', 'Feedback'),
        ('done', 'Done'),
    ], string='Status', default='sample', tracking=True)

    merchandiser_info_id = fields.Many2one(
        'merchandiser.info', string="Costing Reference", readonly=True
    )

    sample_no = fields.Char(string="Sample No", required=True, default='New')
    buyer_id = fields.Many2one('res.partner', string="Buyer")
    style_no = fields.Char(string="Style No")
    sample_type = fields.Char(string="Sample Type")
    season = fields.Char(string="Season")
    merchandiser_name = fields.Char(string="Merchandiser")
    sample_date = fields.Date(
        string="Sample Date", default=fields.Date.context_today
    )

    color = fields.Char(string="Color")
    size = fields.Char(string="Size")
    quantity = fields.Float(string="Quantity")
    fabric_type = fields.Char(string="Fabric Type")
    gsm = fields.Char(string="GSM")
    unit_price = fields.Float(string="Unit Price")
    measurement_status = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail')], string="Measurement Status"
    )

    courier_name = fields.Char(string="Courier Name")
    tracking_no = fields.Char(string="Tracking No")
    sent_date = fields.Date(string="Sent Date")
    delivery_date = fields.Date(string="Delivery Date")

    buyer_comment = fields.Text(string="Buyer Comment")
    correction_note = fields.Text(string="Correction Note")
    approval_date = fields.Date(string="Approval Date")
    attachment = fields.Binary(string="Attachment")
    attachment_name = fields.Char(string="File Name")

    def action_to_courier(self):
        self.state = 'courier'

    def action_to_feedback(self):
        self.state = 'feedback'

    def action_done(self):
        self.state = 'done'
        return {
            'name': 'Create Order',
            'type': 'ir.actions.act_window',
            'res_model': 'merchandiser.order',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_sample_id': self.id,
                'default_buyer_id': self.buyer_id.id if self.buyer_id else False,
                'default_style_no': self.style_no,
                'default_fabric_type': self.fabric_type,
                'default_color': self.color,
                'default_size_range': self.size,
                'default_unit_price': self.unit_price,
            },
        }
