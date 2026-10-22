# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentPurchaseDelivery(models.Model):
    """Purchase Delivery Tracking + Goods Receipt (SRS sections 32-33) and
    Purchase Return Management (SRS section 36, folded into the same
    delivery record rather than a separate model) — garment.purchase.delivery."""
    _name = 'garment.purchase.delivery'
    _description = 'Garment Purchase Delivery'
    _inherit = ['mail.thread']
    _order = 'expected_date desc'

    grn_number = fields.Char(string='GRN Number', copy=False, readonly=True, default=lambda s: _('New'))
    order_id = fields.Many2one('garment.purchase.order', string='Purchase Order', required=True, ondelete='cascade')
    supplier_id = fields.Many2one('res.partner', string='Supplier', related='order_id.supplier_id', store=True)
    material_category = fields.Selection([
        ('fabric', 'Fabric'), ('trim', 'Trim/Accessory'), ('packaging', 'Packaging'), ('other', 'Other'),
    ], string='Material Category', help='Used to select the relevant Purchase Quality Integration checklist '
                                         '(SRS section 34) below.')
    challan_number = fields.Char(string='Challan Number', help='Local Purchase delivery challan (SRS section 27).')
    ordered_qty = fields.Float(string='Ordered Quantity')
    delivered_qty = fields.Float(string='Delivered Quantity')
    pending_qty = fields.Float(string='Pending Quantity', compute='_compute_pending', store=True)
    expected_date = fields.Date(string='Expected Date')
    actual_date = fields.Date(string='Actual Delivery Date')
    delay_days = fields.Integer(string='Delay Days', compute='_compute_pending', store=True)
    on_time = fields.Boolean(string='On-Time Delivery', compute='_compute_pending', store=True,
                              help='Used by the Delivery Performance Report (SRS section 38).')

    quality_status = fields.Selection([
        ('pending', 'Pending Inspection'), ('passed', 'Passed'), ('failed', 'Failed'),
        ('conditional', 'Conditional Pass'),
    ], string='Quality Status', default='pending')

    # Purchase Quality Integration (SRS section 34)
    gsm_test_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
                                        string='GSM Test', default='na')
    shade_test_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
                                          string='Shade Test', default='na')
    shrinkage_test_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
                                              string='Shrinkage Test', default='na')
    color_fastness_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
                                              string='Color Fastness', default='na')
    size_check_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
                                          string='Size Check', default='na')
    color_match_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
                                           string='Color Match', default='na')
    quantity_check_result = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'), ('na', 'N/A')],
                                              string='Quantity Check', default='na')

    # Return Management (SRS section 36)
    return_qty = fields.Float(string='Return Quantity')
    return_reason = fields.Selection([
        ('quality_issue', 'Quality Issue'), ('wrong_material', 'Wrong Material'),
        ('excess_quantity', 'Excess Quantity'), ('damage', 'Damage'),
    ], string='Return Reason')
    return_status = fields.Selection([
        ('none', 'No Return'), ('requested', 'Return Requested'), ('supplier_approved', 'Supplier Approved'),
        ('returned', 'Material Returned'), ('credit_note_issued', 'Credit Note Issued'),
    ], string='Return Status', default='none')

    @api.depends('ordered_qty', 'delivered_qty', 'expected_date', 'actual_date')
    def _compute_pending(self):
        for rec in self:
            rec.pending_qty = max(0.0, (rec.ordered_qty or 0.0) - (rec.delivered_qty or 0.0))
            if rec.expected_date and rec.actual_date:
                rec.delay_days = (rec.actual_date - rec.expected_date).days
            else:
                rec.delay_days = 0
            rec.on_time = bool(rec.actual_date) and rec.delay_days <= 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('grn_number', _('New')) == _('New'):
                vals['grn_number'] = self.env['ir.sequence'].next_by_code('garment.purchase.delivery') or _('New')
        return super().create(vals_list)
