# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentMerchHandover(models.Model):
    """Production Handover (SRS section 32) — garment.merch.handover. Formal
    transfer of responsibility from Merchandising to Production, with a
    checklist and a multi-role approval chain."""
    _name = 'garment.merch.handover'
    _description = 'Garment Merchandising Production Handover'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'handover_date desc'

    handover_number = fields.Char(string='Handover Number', copy=False, readonly=True, default=lambda s: _('New'))
    order_confirmation_id = fields.Many2one('garment.merch.order.confirmation', string='Order Confirmation',
                                             required=True, ondelete='cascade')
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True)
    handover_date = fields.Date(string='Handover Date', default=fields.Date.context_today)

    # Handover Checklist
    chk_buyer_po = fields.Boolean(string='Buyer Purchase Order')
    chk_approved_techpack = fields.Boolean(string='Approved Tech Pack')
    chk_approved_bom = fields.Boolean(string='Approved BOM')
    chk_approved_cost_sheet = fields.Boolean(string='Approved Cost Sheet')
    chk_approved_tna = fields.Boolean(string='Approved TNA')
    chk_fabric_booking = fields.Boolean(string='Fabric Booking')
    chk_trim_booking = fields.Boolean(string='Trim Booking')
    chk_sample_approval = fields.Boolean(string='Sample Approval')
    chk_size_specification = fields.Boolean(string='Size Specification')
    chk_measurement_sheet = fields.Boolean(string='Measurement Sheet')
    chk_packaging_instructions = fields.Boolean(string='Packaging Instructions')
    chk_artwork = fields.Boolean(string='Artwork')
    chk_label_details = fields.Boolean(string='Label Details')
    chk_washing_instructions = fields.Boolean(string='Washing Instructions')
    production_comments = fields.Text(string='Production Comments')

    # Approval chain: Merchandiser -> Merchandising Manager -> Planning Manager -> Production Manager
    merchandiser_id = fields.Many2one('res.users', string='Merchandiser', default=lambda s: s.env.user)
    merchandiser_signed_date = fields.Datetime(string='Merchandiser Signed Date')
    merchandising_manager_id = fields.Many2one('res.users', string='Merchandising Manager')
    merchandising_manager_signed_date = fields.Datetime(string='Merchandising Manager Signed Date')
    planning_manager_id = fields.Many2one('res.users', string='Planning Manager')
    planning_manager_signed_date = fields.Datetime(string='Planning Manager Signed Date')
    production_manager_id = fields.Many2one('res.users', string='Production Manager')
    production_manager_signed_date = fields.Datetime(string='Production Manager Signed Date')

    status = fields.Selection([
        ('draft', 'Draft'), ('merchandiser_submitted', 'Merchandiser Submitted'),
        ('merchandising_manager_review', 'Merchandising Manager Review'),
        ('planning_manager_review', 'Planning Manager Review'),
        ('production_manager_review', 'Production Manager Review'), ('accepted', 'Accepted'),
    ], string='Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('handover_number', _('New')) == _('New'):
                vals['handover_number'] = self.env['ir.sequence'].next_by_code('garment.merch.handover') or _('New')
        return super().create(vals_list)

    def action_next_stage(self):
        flow = ['draft', 'merchandiser_submitted', 'merchandising_manager_review',
                'planning_manager_review', 'production_manager_review', 'accepted']
        signed_field = {
            'merchandiser_submitted': 'merchandiser_signed_date',
            'merchandising_manager_review': 'merchandising_manager_signed_date',
            'planning_manager_review': 'planning_manager_signed_date',
            'production_manager_review': 'production_manager_signed_date',
        }
        for rec in self:
            idx = flow.index(rec.status)
            if idx < len(flow) - 1:
                next_status = flow[idx + 1]
                vals = {'status': next_status}
                field = signed_field.get(next_status)
                if field:
                    vals[field] = fields.Datetime.now()
                rec.write(vals)
