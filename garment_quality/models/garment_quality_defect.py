# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentQualityDefect(models.Model):
    """Defect occurrence log — every individual defect finding, logged
    against an Inspection or an AQL Inspection and a Defect Code. See
    Defect Tracking (base QMS SRS sec. 18) and Quality Defect Management
    System (Garment QMS SRS sec. 28)."""
    _name = 'garment.quality.defect'
    _description = 'Garment Quality Defect'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Defect', required=True)
    defect_code_id = fields.Many2one('garment.quality.defect.code', string='Defect Code', required=True)
    category = fields.Selection(related='defect_code_id.category', store=True, readonly=True)
    severity = fields.Selection([
        ('critical', 'Critical'),
        ('major', 'Major'),
        ('minor', 'Minor'),
    ], string='Severity', compute='_compute_severity', store=True, readonly=False)
    department = fields.Selection([
        ('incoming', 'Incoming / Warehouse'),
        ('cutting', 'Cutting'),
        ('sewing', 'Sewing'),
        ('washing', 'Washing'),
        ('finishing', 'Finishing'),
        ('packing', 'Packing'),
        ('quality', 'Quality'),
    ], string='Department')

    inspection_id = fields.Many2one('garment.quality.inspection', string='Inspection', ondelete='cascade')
    aql_inspection_id = fields.Many2one('garment.aql.inspection', string='AQL Inspection', ondelete='cascade')
    style_id = fields.Many2one('garment.style', string='Style')
    production_order_id = fields.Char(string='Production Order Ref.',
                                       help='Soft reference — see IMPLEMENTATION_NOTES.md.')
    sewing_line = fields.Char(string='Sewing Line')
    location = fields.Char(string='Defect Location', help='Location on the garment / panel')

    quantity = fields.Float(string='Defect Quantity', default=1.0)
    responsible_user_id = fields.Many2one('res.users', string='Responsible Person')
    corrective_action = fields.Text(string='Corrective Action')
    status = fields.Selection([
        ('open', 'Open'),
        ('under_repair', 'Under Repair'),
        ('corrected', 'Corrected'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True)
    photo = fields.Binary(string='Defect Photo', attachment=True)
    capa_id = fields.Many2one('garment.quality.capa', string='CAPA')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.onchange('defect_code_id')
    def _onchange_defect_code_id(self):
        for rec in self:
            if rec.defect_code_id:
                rec.name = rec.defect_code_id.name
                rec.severity = rec.defect_code_id.severity

    @api.depends('defect_code_id')
    def _compute_severity(self):
        for rec in self:
            if rec.defect_code_id:
                rec.severity = rec.defect_code_id.severity
