# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from datetime import timedelta

from odoo import api, fields, models, _


class GarmentRFQ(models.Model):
    """RFQ (Request for Quotation) intake — captures buyer inquiries before
    order confirmation. Downstream modules (Merchandising, Costing) read
    from this model, so it is intentionally lightweight here and does not
    own costing/quotation logic."""
    _name = 'garment.rfq'
    _description = 'Garment RFQ (Request for Quotation)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'rfq_date desc'

    rfq_number = fields.Char(string='RFQ Number', copy=False, readonly=True, default=lambda s: _('New'))
    rfq_date = fields.Date(string='RFQ Date', default=fields.Date.context_today, required=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    buyer_contact_id = fields.Many2one('garment.buyer.contact', string='Buyer Contact',
                                        domain="[('buyer_id', '=', buyer_id)]")
    opportunity_id = fields.Many2one('garment.opportunity', string='Opportunity')
    inquiry_number = fields.Char(string='Inquiry Number')
    season = fields.Char(string='Season')
    brand = fields.Char(string='Brand')
    collection = fields.Char(string='Collection')
    department = fields.Char(string='Department')
    product_category = fields.Char(string='Product Category')
    product_type = fields.Char(string='Product Type')

    # Product Information
    style_name = fields.Char(string='Style Name')
    style_number = fields.Char(string='Style Number')
    product_description = fields.Text(string='Product Description')
    fabric_type = fields.Char(string='Fabric Type')
    fabric_composition = fields.Char(string='Fabric Composition')
    gsm = fields.Char(string='GSM')
    color = fields.Char(string='Color')
    print_type = fields.Char(string='Print Type')
    embroidery = fields.Char(string='Embroidery')
    wash_type = fields.Char(string='Wash Type')
    size_range = fields.Char(string='Size Range')
    packing_type = fields.Char(string='Packing Type')
    label_type = fields.Char(string='Label Type')
    hang_tag = fields.Boolean(string='Hang Tag')
    poly_bag = fields.Boolean(string='Poly Bag')
    carton = fields.Boolean(string='Carton')

    # Quantity Information
    moq = fields.Integer(string='Minimum Order Quantity')
    order_quantity = fields.Integer(string='Order Quantity')
    size_breakdown = fields.Text(string='Size Breakdown')
    color_breakdown = fields.Text(string='Color Breakdown')
    country_wise_quantity = fields.Text(string='Country Wise Quantity')
    delivery_schedule = fields.Char(string='Delivery Schedule')

    # Commercial Information
    target_fob_price = fields.Monetary(string='Target FOB Price', currency_field='currency_id')
    target_cm = fields.Monetary(string='Target CM', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    delivery_term = fields.Char(string='Delivery Terms')
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterms')
    destination_port = fields.Char(string='Destination Port')
    shipment_mode = fields.Selection([
        ('sea', 'Sea Freight'), ('air', 'Air Freight'), ('road', 'Road'), ('rail', 'Rail'), ('courier', 'Courier'),
    ], string='Shipment Mode')

    # Required Dates
    rfq_received_date = fields.Date(string='RFQ Received Date')
    costing_due_date = fields.Date(string='Costing Due Date')
    sample_due_date = fields.Date(string='Sample Due Date')
    quotation_due_date = fields.Date(string='Quotation Due Date')
    buyer_response_date = fields.Date(string='Buyer Response Date')
    expected_po_date = fields.Date(string='Expected PO Date')

    # Attachments
    tech_pack_file = fields.Binary(string='Tech Pack', attachment=True)
    artwork_file = fields.Binary(string='Artwork', attachment=True)
    measurement_sheet_file = fields.Binary(string='Measurement Sheet', attachment=True)
    color_standard_file = fields.Binary(string='Color Standard', attachment=True)
    fabric_standard_file = fields.Binary(string='Fabric Standard', attachment=True)
    trim_sheet_file = fields.Binary(string='Trim Sheet', attachment=True)
    packaging_instruction_file = fields.Binary(string='Packaging Instructions', attachment=True)
    cad_file = fields.Binary(string='CAD Files', attachment=True)
    reference_image = fields.Binary(string='Reference Image', attachment=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('costing', 'Costing'),
        ('sample_development', 'Sample Development'),
        ('quotation_ready', 'Quotation Ready'),
        ('submitted', 'Submitted'),
        ('buyer_review', 'Buyer Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    branch = fields.Char(string='Branch')
    internal_notes = fields.Text(string='Internal Notes')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('rfq_number', _('New')) == _('New'):
                vals['rfq_number'] = self.env['ir.sequence'].next_by_code('garment.rfq') or _('New')
        return super().create(vals_list)

    def action_submit(self):
        self.write({'state': 'submitted'})
        for rec in self:
            rec.buyer_id.write({'buyer_status': 'quotation_sent'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    # ------------------------------------------------------------------
    # RFQ Automation (SRS section 14): reminders before deadlines /
    # escalate overdue RFQs.
    # ------------------------------------------------------------------
    @api.model
    def _cron_remind_due_dates(self, reminder_days=3):
        today = fields.Date.context_today(self)
        limit = today + timedelta(days=reminder_days)
        open_states = ['draft', 'under_review', 'costing', 'sample_development', 'quotation_ready']
        due_date_fields = [
            ('costing_due_date', _('Costing due')),
            ('sample_due_date', _('Sample due')),
            ('quotation_due_date', _('Quotation due')),
        ]
        for field_name, label in due_date_fields:
            rfqs = self.search([
                (field_name, '!=', False),
                (field_name, '<=', limit),
                (field_name, '>=', today),
                ('state', 'in', open_states),
            ])
            for rfq in rfqs:
                rfq.message_post(body=_('%s on %s for RFQ %s.') % (label, rfq[field_name], rfq.rfq_number))

    @api.model
    def _cron_escalate_overdue(self):
        today = fields.Date.context_today(self)
        open_states = ['draft', 'under_review', 'costing', 'sample_development', 'quotation_ready', 'submitted']
        overdue = self.search([
            ('expected_po_date', '!=', False),
            ('expected_po_date', '<', today),
            ('state', 'in', open_states),
        ])
        for rfq in overdue:
            rfq.message_post(body=_('RFQ %s is overdue (expected PO date %s has passed).') % (
                rfq.rfq_number, rfq.expected_po_date))
