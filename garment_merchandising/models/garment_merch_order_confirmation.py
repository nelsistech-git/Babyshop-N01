# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentMerchOrderConfirmation(models.Model):
    """Order Confirmation, merchandising side (SRS section 31) —
    garment.merch.order.confirmation. Converts an accepted Quotation into a
    confirmed order record. This is NOT the full Production/Order
    Management system (a future module) — it is the merchandiser's
    commitment record that Production Handover then formalizes."""
    _name = 'garment.merch.order.confirmation'
    _description = 'Garment Merchandising Order Confirmation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'order_date desc'

    order_number = fields.Char(string='Order Number', copy=False, readonly=True, default=lambda s: _('New'))
    buyer_po_number = fields.Char(string='Buyer PO Number')
    quotation_id = fields.Many2one('garment.merch.quotation', string='Quotation')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True)
    order_date = fields.Date(string='Order Date', default=fields.Date.context_today)
    quantity = fields.Integer(string='Quantity')
    # Order Booking (Garment Merchandising Management System SRS section 10:
    # Buyer, Style, Quantity, Color, Size, Delivery Date, Price, Terms).
    color = fields.Char(string='Color')
    size_breakdown = fields.Text(string='Size Breakdown')
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    fob_value = fields.Monetary(string='FOB Value', compute='_compute_fob_value', store=True,
                                 currency_field='currency_id')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterms')
    delivery_date = fields.Date(string='Delivery Date')
    shipment_date = fields.Date(string='Shipment Date')
    factory = fields.Char(string='Factory')
    production_unit = fields.Char(string='Production Unit')
    merchandiser_id = fields.Many2one('res.users', string='Merchandiser')

    status = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('material_planning', 'Material Planning'),
        ('production', 'Production'), ('quality_inspection', 'Quality Inspection'), ('packing', 'Packing'),
        ('shipment', 'Shipment'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')

    # Order Approval Workflow (Garment Merchandising Management System SRS
    # section 33: Merchandiser -> Merchandising Manager -> Production Manager
    # -> Commercial Manager -> Factory Head), separate from the operational
    # 'status' flow above which tracks execution once the order is approved.
    approval_stage = fields.Selection([
        ('draft', 'Draft'), ('merchandiser', 'Merchandiser'),
        ('merchandising_manager', 'Merchandising Manager'), ('production_manager', 'Production Manager'),
        ('commercial_manager', 'Commercial Manager'), ('factory_head', 'Factory Head'),
        ('approved', 'Approved'),
    ], string='Approval Stage', default='draft', tracking=True)
    merchandiser_approver_id = fields.Many2one('res.users', string='Merchandiser (Approval)')
    merchandiser_approved_date = fields.Datetime(string='Merchandiser Approved On')
    merchandising_manager_id = fields.Many2one('res.users', string='Merchandising Manager')
    merchandising_manager_approved_date = fields.Datetime(string='Merchandising Manager Approved On')
    production_manager_id = fields.Many2one('res.users', string='Production Manager')
    production_manager_approved_date = fields.Datetime(string='Production Manager Approved On')
    commercial_manager_id = fields.Many2one('res.users', string='Commercial Manager')
    commercial_manager_approved_date = fields.Datetime(string='Commercial Manager Approved On')
    factory_head_id = fields.Many2one('res.users', string='Factory Head')
    factory_head_approved_date = fields.Datetime(string='Factory Head Approved On')

    handover_ids = fields.One2many('garment.merch.handover', 'order_confirmation_id', string='Handovers')
    task_ids = fields.One2many('garment.merch.task', 'order_confirmation_id', string='Merchandising Tasks')
    task_count = fields.Integer(compute='_compute_task_count')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('task_ids')
    def _compute_task_count(self):
        for rec in self:
            rec.task_count = len(rec.task_ids)

    @api.depends('quantity', 'unit_price')
    def _compute_fob_value(self):
        for rec in self:
            rec.fob_value = (rec.quantity or 0) * (rec.unit_price or 0.0)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('order_number', _('New')) == _('New'):
                vals['order_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.merch.order.confirmation') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'status': 'confirmed'})

    def action_create_handover(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Production Handover'),
            'res_model': 'garment.merch.handover', 'view_mode': 'form', 'target': 'new',
            'context': {'default_order_confirmation_id': self.id, 'default_buyer_id': self.buyer_id.id,
                        'default_style_id': self.style_id.id},
        }

    def action_next_approval_stage(self):
        """Advance the Order Approval Workflow (SRS section 33)."""
        flow = ['draft', 'merchandiser', 'merchandising_manager', 'production_manager',
                'commercial_manager', 'factory_head', 'approved']
        signed_field = {
            'merchandiser': 'merchandiser_approved_date',
            'merchandising_manager': 'merchandising_manager_approved_date',
            'production_manager': 'production_manager_approved_date',
            'commercial_manager': 'commercial_manager_approved_date',
            'factory_head': 'factory_head_approved_date',
        }
        for rec in self:
            idx = flow.index(rec.approval_stage)
            if idx < len(flow) - 1:
                next_stage = flow[idx + 1]
                vals = {'approval_stage': next_stage}
                field = signed_field.get(next_stage)
                if field:
                    vals[field] = fields.Datetime.now()
                rec.write(vals)

    def action_view_tasks(self):
        self.ensure_one()
        return {'name': _('Merchandising Tasks'), 'type': 'ir.actions.act_window', 'res_model': 'garment.merch.task',
                'view_mode': 'tree,form', 'domain': [('order_confirmation_id', '=', self.id)],
                'context': {'default_order_confirmation_id': self.id, 'default_buyer_id': self.buyer_id.id}}
