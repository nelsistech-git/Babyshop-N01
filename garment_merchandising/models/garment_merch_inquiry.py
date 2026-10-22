# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentMerchInquiry(models.Model):
    """Buyer Inquiry Management + Merchandiser Assignment (SRS sections 7-8)
    — garment.merch.inquiry. The merchandiser's working record once an RFQ
    (garment.rfq, Buyer CRM) is picked up for active development; it does
    not duplicate RFQ fields but references it and adds workflow/assignment
    state specific to the merchandising desk."""
    _name = 'garment.merch.inquiry'
    _description = 'Garment Merchandising Inquiry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'inquiry_date desc'

    inquiry_number = fields.Char(string='Inquiry Number', copy=False, readonly=True, default=lambda s: _('New'))
    inquiry_date = fields.Date(string='Inquiry Date', default=fields.Date.context_today, required=True)
    rfq_id = fields.Many2one('garment.rfq', string='RFQ Reference')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    buyer_contact_id = fields.Many2one('garment.buyer.contact', string='Buyer Contact',
                                        domain="[('buyer_id', '=', buyer_id)]")
    buying_house = fields.Char(string='Buying House')
    brand = fields.Char(string='Brand')
    season = fields.Char(string='Season')
    product_category_id = fields.Many2one('garment.style.category', string='Product Category')
    product_type = fields.Char(string='Product Type')
    collection = fields.Char(string='Collection')
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1')

    # Product Details (SRS section 7)
    product_description = fields.Text(string='Product Description')
    fabric_type = fields.Char(string='Fabric Type')
    fabric_composition = fields.Char(string='Fabric Composition')
    gsm = fields.Float(string='GSM')
    yarn_count = fields.Char(string='Yarn Count')
    knit_type = fields.Char(string='Knit Type')
    weave_type = fields.Char(string='Weave Type')
    dyeing_type = fields.Char(string='Dyeing Type')
    washing_type = fields.Char(string='Washing Type')
    print_type = fields.Char(string='Print Type')
    embroidery_type = fields.Char(string='Embroidery Type')
    finish_type = fields.Char(string='Finish Type')

    # Quantity (SRS section 7)
    moq = fields.Integer(string='MOQ')
    order_quantity = fields.Integer(string='Order Quantity')
    size_breakdown = fields.Text(string='Size Breakdown')
    color_breakdown = fields.Text(string='Color Breakdown')
    destination_country_id = fields.Many2one('res.country', string='Destination Country')
    delivery_schedule = fields.Date(string='Delivery Schedule')

    # Commercial Details (SRS section 7)
    target_fob = fields.Monetary(string='Target FOB', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterms')
    shipment_mode = fields.Selection([
        ('sea', 'Sea'), ('air', 'Air'), ('courier', 'Courier'), ('multimodal', 'Multimodal'),
    ], string='Shipment Mode')
    port_of_loading = fields.Char(string='Port of Loading')
    destination_port = fields.Char(string='Destination Port')

    # Assignment (SRS section 8 — criteria: buyer, product category, country, workload,
    # experience, department, team, capacity, performance score)
    assigned_merchandiser_id = fields.Many2one('res.users', string='Assigned Merchandiser', tracking=True)
    assignment_department = fields.Char(string='Department')
    assignment_team = fields.Char(string='Team')

    style_line_ids = fields.One2many('garment.merch.style.line', 'inquiry_id', string='Styles')
    checklist_ids = fields.One2many('garment.merch.review.checklist', 'inquiry_id', string='Review Checklists')
    quotation_ids = fields.One2many('garment.merch.quotation', 'inquiry_id', string='Quotations')
    task_ids = fields.One2many('garment.merch.task', 'inquiry_id', string='Merchandising Tasks')

    style_count = fields.Integer(compute='_compute_counts')
    quotation_count = fields.Integer(compute='_compute_counts')
    task_count = fields.Integer(compute='_compute_counts')

    status = fields.Selection([
        ('new', 'New'), ('assigned', 'Assigned'), ('style_development', 'Style Development'),
        ('internal_review', 'Internal Review'), ('costing', 'Costing'), ('quotation_sent', 'Quotation Sent'),
        ('negotiation', 'Negotiation'), ('order_confirmed', 'Order Confirmed'), ('lost', 'Lost'),
    ], string='Status', default='new', tracking=True, group_expand='_expand_states')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('style_line_ids', 'quotation_ids', 'task_ids')
    def _compute_counts(self):
        for rec in self:
            rec.style_count = len(rec.style_line_ids)
            rec.quotation_count = len(rec.quotation_ids)
            rec.task_count = len(rec.task_ids)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('inquiry_number', _('New')) == _('New'):
                vals['inquiry_number'] = self.env['ir.sequence'].next_by_code('garment.merch.inquiry') or _('New')
        return super().create(vals_list)

    def action_auto_assign_merchandiser(self):
        """Workload-aware assignment (SRS section 8 criteria: workload)."""
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            user, note = ai_engine.recommend_merchandiser_for_inquiry(rec)
            if user:
                rec.write({'assigned_merchandiser_id': user.id, 'status': 'assigned'})
            rec.message_post(body=note)
        return True

    def action_view_quotations(self):
        self.ensure_one()
        return {'name': _('Quotations'), 'type': 'ir.actions.act_window', 'res_model': 'garment.merch.quotation',
                'view_mode': 'tree,form', 'domain': [('inquiry_id', '=', self.id)],
                'context': {'default_inquiry_id': self.id}}

    def action_view_tasks(self):
        self.ensure_one()
        return {'name': _('Merchandising Tasks'), 'type': 'ir.actions.act_window', 'res_model': 'garment.merch.task',
                'view_mode': 'tree,form', 'domain': [('inquiry_id', '=', self.id)],
                'context': {'default_inquiry_id': self.id, 'default_buyer_id': self.buyer_id.id}}
