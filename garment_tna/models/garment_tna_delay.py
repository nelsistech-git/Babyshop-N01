# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentTnaDelay(models.Model):
    """Delay Management + Automatic Delay Calculation (SRS sections 14-16)
    — garment.tna.delay."""
    _name = 'garment.tna.delay'
    _description = 'Garment TNA Delay'
    _inherit = ['mail.thread']
    _order = 'planned_date desc'

    tna_id = fields.Many2one('garment.tna', string='TNA', required=True, ondelete='cascade')
    # FIXED: Changed tna_id to parent.id in domain
    activity_id = fields.Many2one('garment.tna.activity', string='Activity', domain="[('tna_id', '=', parent.id)]")
    planned_date = fields.Date(string='Planned Date', required=True)
    actual_date = fields.Date(string='Actual Date')
    delay_days = fields.Integer(string='Delay Days', compute='_compute_delay', store=True)
    severity = fields.Selection([
        ('normal', 'Normal (0 Days)'), ('low', 'Low (1-3 Days)'), ('medium', 'Medium (4-7 Days)'),
        ('high', 'High (8-15 Days)'), ('critical', 'Critical (15+ Days)'),
    ], string='Severity', compute='_compute_delay', store=True, tracking=True)
    delay_reason = fields.Selection([
        ('buyer_approval_delay', 'Buyer Approval Delay'), ('supplier_delay', 'Supplier Delay'),
        ('material_shortage', 'Material Shortage'), ('production_delay', 'Production Delay'),
        ('quality_issue', 'Quality Issue'), ('machine_breakdown', 'Machine Breakdown'),
        ('manpower_shortage', 'Manpower Shortage'), ('weather_port_issue', 'Weather/Port Issue'),
        ('other', 'Other'),
    ], string='Delay Reason', required=True)
    responsible_department = fields.Char(string='Responsible Department')
    corrective_action = fields.Text(string='Corrective Action')
    supplier_id = fields.Many2one('res.partner', string='Related Supplier',
                                   help='Set when Delay Reason is Supplier Delay, to feed AI supplier '
                                        'performance analysis.')

    @api.depends('planned_date', 'actual_date')
    def _compute_delay(self):
        for rec in self:
            if rec.planned_date and rec.actual_date:
                days = (rec.actual_date - rec.planned_date).days
            else:
                days = 0
            rec.delay_days = days
            if days <= 0:
                rec.severity = 'normal'
            elif days <= 3:
                rec.severity = 'low'
            elif days <= 7:
                rec.severity = 'medium'
            elif days <= 15:
                rec.severity = 'high'
            else:
                rec.severity = 'critical'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.severity in ('high', 'critical'):
                rec.tna_id.message_post(
                    body=_('%s severity delay logged on %s: %s') % (
                        rec.severity, rec.activity_id.activity_name or rec.tna_id.name, rec.delay_reason))
        return records