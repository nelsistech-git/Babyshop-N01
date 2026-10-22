# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityRework(models.Model):
    """Repair / Rework Management. See Repair Management System (base QMS
    SRS sec. 27) and Rework Management System (Garment QMS SRS sec. 30)."""
    _name = 'garment.quality.rework'
    _description = 'Garment Quality Repair / Rework'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Rework Ref.', copy=False, readonly=True, default=lambda s: _('New'))
    defect_id = fields.Many2one('garment.quality.defect', string='Defect')
    inspection_id = fields.Many2one('garment.quality.inspection', string='Inspection')
    defect_code_id = fields.Many2one('garment.quality.defect.code', string='Defect Code')
    style_id = fields.Many2one('garment.style', string='Style')
    garment_ref = fields.Char(string='Garment / Bundle ID')
    quantity = fields.Float(string='Quantity', default=1.0)
    repair_person_id = fields.Many2one('res.users', string='Repair Person')
    repair_start = fields.Datetime(string='Repair Start')
    repair_end = fields.Datetime(string='Repair End')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_repair', 'In Repair'),
        ('completed', 'Repair Completed'),
        ('re_inspection', 'Re-Inspection'),
        ('approved', 'Approved'),
        ('scrapped', 'Scrapped'),
    ], string='Status', default='pending', tracking=True)
    reinspection_result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Re-Inspection Result')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.quality.rework') or _('New')
        return super().create(vals_list)
