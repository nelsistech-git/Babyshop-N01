# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Fired IoT Alerts (SRS s.28 Smart Andon, s.48 Real-Time Alert Management,
IOT-005 test case) — audit trail of every garment.iot.alert.rule that
tripped, what action ran, and its current acknowledgement state."""

from odoo import api, fields, models, _


class GarmentIotAlertLog(models.Model):
    _name = 'garment.iot.alert.log'
    _description = 'Garment IoT Fired Alert'
    _order = 'triggered_datetime desc, id desc'

    name = fields.Char(string='Alert Reference', copy=False, readonly=True, default=lambda s: _('New'))
    rule_id = fields.Many2one('garment.iot.alert.rule', string='Alert Rule', required=True,
                               ondelete='restrict', index=True)
    reading_id = fields.Many2one('garment.iot.reading', string='Triggering Reading', ondelete='set null')
    device_id = fields.Many2one('garment.iot.device', string='Device', required=True,
                                 ondelete='cascade', index=True)
    gateway_id = fields.Many2one(related='device_id.gateway_id', string='Gateway', store=True)
    machine_id = fields.Many2one(related='device_id.machine_id', string='Machine', store=True)

    severity = fields.Selection([
        ('info', 'Info / Green'),
        ('warning', 'Warning / Yellow'),
        ('critical', 'Critical / Red'),
    ], string='Severity', required=True, default='warning')
    value = fields.Float(string='Value At Trigger', digits=(16, 4))
    triggered_datetime = fields.Datetime(string='Triggered On', default=fields.Datetime.now, required=True)
    action_taken = fields.Char(string='Action Taken', readonly=True,
                                help='Short description of what the rule action did (or why it failed).')

    state = fields.Selection([
        ('new', 'New'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    ], string='Status', default='new', tracking=False, required=True)
    acknowledged_by_id = fields.Many2one('res.users', string='Acknowledged By', readonly=True)
    acknowledged_date = fields.Datetime(string='Acknowledged On', readonly=True)
    notes = fields.Text(string='Notes')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.iot.alert.log') or _('New')
        return super().create(vals_list)

    def action_acknowledge(self):
        self.write({
            'state': 'acknowledged',
            'acknowledged_by_id': self.env.user.id,
            'acknowledged_date': fields.Datetime.now(),
        })

    def action_resolve(self):
        self.write({'state': 'resolved'})
