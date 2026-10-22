# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentProductionMachine(models.Model):
    """Machine master with running/idle/breakdown status and IoT counters.
    See Production Management SRS s.36, Planning & MES SRS s.30-32, MES SRS
    s.10, Shop Floor SRS s.34 (IoT Production Monitoring)."""
    _name = 'garment.production.machine'
    _description = 'Garment Production Machine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'machine_number'
    _rec_name = 'machine_number'

    machine_number = fields.Char(string='Machine Number', required=True, tracking=True)
    name = fields.Char(string='Machine Name')
    machine_type = fields.Selection([
        ('single_needle', 'Single Needle'), ('overlock', 'Overlock'), ('flatlock', 'Flatlock'),
        ('bartack', 'Bartack'), ('buttonhole', 'Buttonhole'), ('button_attach', 'Button Attach'),
        ('cutting_machine', 'Cutting Machine'), ('spreading_machine', 'Spreading Machine'),
        ('washing_machine', 'Washing Machine'), ('dryer', 'Dryer'), ('iron', 'Ironing Machine'),
        ('embroidery_machine', 'Embroidery Machine'), ('printing_machine', 'Printing Machine'),
        ('other', 'Other'),
    ], string='Machine Type', required=True)
    brand = fields.Char(string='Brand')
    model_reference = fields.Char(string='Model')
    work_center_id = fields.Many2one('garment.work.center', string='Work Center')
    line_id = fields.Many2one('garment.production.line', string='Production Line')
    location = fields.Char(string='Location')
    purchase_date = fields.Date(string='Purchase Date')
    status = fields.Selection([
        ('running', 'Running'), ('idle', 'Idle'), ('breakdown', 'Breakdown'),
        ('maintenance', 'Maintenance'), ('offline', 'Offline'),
    ], string='Status', default='idle', tracking=True)

    # IoT / machine data (SRS: Running Time, Idle Time, Output Count, Breakdown Time, Speed, Vibration, Energy)
    iot_enabled = fields.Boolean(string='IoT Connected')
    running_hours_total = fields.Float(string='Total Running Hours')
    idle_hours_total = fields.Float(string='Total Idle Hours')
    breakdown_hours_total = fields.Float(string='Total Breakdown Hours')
    last_output_count = fields.Integer(string='Last Output Count')
    last_speed = fields.Float(string='Last Speed (RPM)')
    last_vibration = fields.Float(string='Last Vibration Reading')
    last_energy_consumption = fields.Float(string='Last Energy Consumption (kWh)')
    last_data_sync = fields.Datetime(string='Last IoT Data Sync')

    downtime_ids = fields.One2many('garment.machine.downtime', 'machine_id', string='Downtime Records')
    downtime_count = fields.Integer(compute='_compute_downtime_count')

    # AI predictive maintenance
    ai_maintenance_risk = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='AI Maintenance Risk', readonly=True)
    ai_maintenance_note = fields.Text(string='AI Maintenance Prediction', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    def _compute_downtime_count(self):
        for rec in self:
            rec.downtime_count = len(rec.downtime_ids)

    def action_run_ai_maintenance_prediction(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            risk, note = ai_engine.predict_machine_maintenance(rec)
            rec.write({'ai_maintenance_risk': risk, 'ai_maintenance_note': note,
                       'ai_last_run': fields.Datetime.now()})

    def action_view_downtime(self):
        self.ensure_one()
        return {
            'name': 'Downtime Records', 'type': 'ir.actions.act_window', 'res_model': 'garment.machine.downtime',
            'view_mode': 'tree,form', 'domain': [('machine_id', '=', self.id)],
            'context': {'default_machine_id': self.id},
        }
