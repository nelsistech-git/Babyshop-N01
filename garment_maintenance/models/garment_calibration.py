# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Calibration Management System (Maintenance & Asset Mgmt SRS sec. 28-30,
CMMS SRS sec. 28-29). Calibrated instruments (weight scale, temperature
meter, pressure gauge, GSM tester, testing machines) are registered as
``garment.asset`` (category ``quality_instrument``) rather than a third
equipment model; this document tracks the calibration event, due date
and certificate against that asset (or, for an in-line production
gauge, against the machine it is mounted on).
"""
from datetime import timedelta

from odoo import api, fields, models, _


class GarmentCalibration(models.Model):
    _name = 'garment.calibration'
    _description = 'Garment Calibration Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_due_date'

    name = fields.Char(string='Calibration No.', copy=False, readonly=True, default=lambda s: _('New'))
    equipment_type = fields.Selection([
        ('asset', 'Asset / Instrument'),
        ('machine', 'Production Machine'),
    ], string='Equipment Type', default='asset', required=True)
    asset_id = fields.Many2one('garment.asset', string='Equipment')
    machine_id = fields.Many2one('garment.production.machine', string='Machine')
    equipment_name = fields.Char(string='Equipment Name', compute='_compute_equipment_name', store=True)

    standard = fields.Char(string='Calibration Standard')
    service_provider_id = fields.Many2one('garment.supplier', string='Calibration Company')
    calibration_date = fields.Date(string='Calibration Date', default=fields.Date.context_today, required=True,
                                    tracking=True)
    next_due_date = fields.Date(string='Next Due Date', required=True, tracking=True)
    result = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Result', default='pending', tracking=True)

    certificate_number = fields.Char(string='Certificate Number')
    certificate_file = fields.Binary(string='Certificate', attachment=True)
    certificate_filename = fields.Char(string='Certificate Filename')
    validity_period_months = fields.Integer(string='Validity Period (Months)', default=12)
    is_due_soon = fields.Boolean(string='Due Soon', compute='_compute_due_flags', store=True)
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_due_flags', store=True)

    workorder_id = fields.Many2one('garment.maintenance.workorder', string='Related Work Order')
    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('asset_id.name', 'asset_id.asset_code', 'machine_id.name', 'machine_id.machine_number')
    def _compute_equipment_name(self):
        for rec in self:
            if rec.equipment_type == 'machine' and rec.machine_id:
                rec.equipment_name = rec.machine_id.name or rec.machine_id.machine_number
            elif rec.equipment_type == 'asset' and rec.asset_id:
                rec.equipment_name = '%s [%s]' % (rec.asset_id.name, rec.asset_id.asset_code)
            else:
                rec.equipment_name = False

    @api.depends('next_due_date')
    def _compute_due_flags(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_overdue = bool(rec.next_due_date and rec.next_due_date < today)
            rec.is_due_soon = bool(rec.next_due_date and today <= rec.next_due_date <= today + timedelta(days=15))

    @api.onchange('equipment_type')
    def _onchange_equipment_type(self):
        self.asset_id = False
        self.machine_id = False

    @api.onchange('calibration_date', 'validity_period_months')
    def _onchange_calibration_date(self):
        if self.calibration_date and self.validity_period_months:
            self.next_due_date = fields.Date.add(self.calibration_date, months=self.validity_period_months)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.calibration') or _('New')
        return super().create(vals_list)

    def action_approve(self):
        self.write({'result': 'approved'})

    def action_reject(self):
        self.write({'result': 'rejected'})
