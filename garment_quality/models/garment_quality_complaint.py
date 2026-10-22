# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityComplaint(models.Model):
    """Buyer Quality Complaint management. See Quality Complaint Management
    (base QMS SRS sec. 36), Buyer Complaint Management (Garment QMS SRS sec.
    36) and Buyer Complaint Management (Advanced QMS SRS sec. 50 —
    'garment.buyer.complaint'; kept here as garment.quality.complaint to
    stay under the module's garment.quality.* naming convention)."""
    _name = 'garment.quality.complaint'
    _description = 'Garment Quality Buyer Complaint'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'

    complaint_no = fields.Char(string='Complaint No.', copy=False, readonly=True, default=lambda s: _('New'))
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    style_id = fields.Many2one('garment.style', string='Style')
    order_reference = fields.Char(string='Order Reference')
    shipment_reference = fields.Char(string='Shipment Reference')
    complaint_type = fields.Selection([
        ('measurement', 'Measurement Problem'),
        ('color', 'Color Variation'),
        ('stitch', 'Stitch / Sewing Defect'),
        ('packing', 'Packing Issue'),
        ('fabric', 'Fabric Issue'),
        ('accessory', 'Accessory Issue'),
        ('shortage', 'Shortage'),
        ('other', 'Other'),
    ], string='Complaint Type', required=True)
    severity = fields.Selection([
        ('critical', 'Critical'),
        ('major', 'Major'),
        ('minor', 'Minor'),
    ], string='Severity', default='major', tracking=True)
    complaint_date = fields.Date(string='Complaint Date', default=fields.Date.context_today)
    description = fields.Text(string='Description', required=True)
    root_cause = fields.Text(string='Root Cause')
    action_taken = fields.Text(string='Action Taken')
    capa_id = fields.Many2one('garment.quality.capa', string='CAPA')
    status = fields.Selection([
        ('new', 'New'),
        ('investigating', 'Investigating'),
        ('rca', 'Root Cause Analysis'),
        ('corrective_plan', 'Corrective Plan'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='new', tracking=True)
    resolution_date = fields.Date(string='Resolution Date')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('complaint_no', _('New')) == _('New'):
                vals['complaint_no'] = self.env['ir.sequence'].next_by_code('garment.quality.complaint') or _('New')
        return super().create(vals_list)

    def action_create_capa(self):
        self.ensure_one()
        capa = self.env['garment.quality.capa'].create({
            'source': 'complaint',
            'complaint_id': self.id,
            'style_id': self.style_id.id,
            'problem_description': self.description,
        })
        self.capa_id = capa.id
        return {
            'name': _('CAPA'), 'type': 'ir.actions.act_window', 'res_model': 'garment.quality.capa',
            'view_mode': 'form', 'res_id': capa.id,
        }

    def action_resolve(self):
        self.write({'status': 'resolved', 'resolution_date': fields.Date.context_today(self)})
