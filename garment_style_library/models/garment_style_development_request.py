# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentStyleDevelopmentRequest(models.Model):
    """Every new style starts with a development request (SRS section 9)."""
    _name = 'garment.style.development.request'
    _description = 'Garment Product Development Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    request_number = fields.Char(string='Request Number', copy=False, readonly=True, default=lambda s: _('New'))
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    rfq_id = fields.Many2one('garment.rfq', string='RFQ Reference')
    merchandiser_id = fields.Many2one('res.users', string='Merchandiser')
    designer_id = fields.Many2one('res.users', string='Designer')
    style_category_id = fields.Many2one('garment.style.category', string='Product Category')
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1')
    required_completion_date = fields.Date(string='Required Completion Date')
    remarks = fields.Text(string='Remarks')

    buyer_image = fields.Binary(string='Buyer Images', attachment=True)
    sketch = fields.Binary(string='Sketches', attachment=True)
    reference_sample_image = fields.Binary(string='Reference Samples', attachment=True)
    mood_board = fields.Binary(string='Mood Board', attachment=True)
    buyer_tech_pack = fields.Binary(string='Buyer Tech Pack', attachment=True)
    video = fields.Binary(string='Videos', attachment=True)
    fabric_reference = fields.Binary(string='Fabric References', attachment=True)

    state = fields.Selection([
        ('new', 'New'), ('in_progress', 'In Progress'), ('converted', 'Converted to Style'), ('cancelled', 'Cancelled'),
    ], string='Status', default='new', tracking=True)
    style_id = fields.Many2one('garment.style', string='Resulting Style', readonly=True, copy=False)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('request_number', _('New')) == _('New'):
                vals['request_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.style.development.request') or _('New')
        return super().create(vals_list)

    def action_convert_to_style(self):
        self.ensure_one()
        style = self.env['garment.style'].create({
            'style_name': _('New Style from %s') % self.request_number,
            'buyer_id': self.buyer_id.id,
            'style_category_id': self.style_category_id.id,
            'designer_id': self.designer_id.id,
            'development_request_id': self.id,
        })
        self.write({'state': 'converted', 'style_id': style.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'garment.style',
            'res_id': style.id,
            'view_mode': 'form',
        }
