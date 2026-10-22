# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentMobileOfflineSyncLog(models.Model):
    """Offline Sync Log (SRS s.24 Offline Mode Management, s.25 Mobile Data
    Synchronization, s.48 Mobile Offline Security, MOB-003 test case) —
    garment.mobile.offline.sync.log. Every record captured on a device while
    offline (shop-floor production entry, QC inspection, attendance,
    warehouse scan, checklist update) writes one row here when it syncs back
    to the ERP, keeping the raw payload for audit/replay and recording
    whether the offline-captured record landed cleanly, failed, or
    conflicted with server-side data."""
    _name = 'garment.mobile.offline.sync.log'
    _description = 'Garment Mobile Offline Sync Log'
    _order = 'synced_at desc'

    sync_number = fields.Char(string='Sync No.', copy=False, readonly=True, default=lambda s: _('New'))
    device_id = fields.Many2one('garment.mobile.device', string='Device', required=True,
                                 ondelete='cascade', tracking=False)
    user_id = fields.Many2one('res.users', string='User', required=True)

    sync_type = fields.Selection([
        ('production_entry', 'Production Entry'),
        ('qc_inspection', 'QC Inspection'),
        ('attendance', 'Attendance Entry'),
        ('warehouse_scan', 'Warehouse Scan'),
        ('checklist', 'Checklist Update'),
        ('other', 'Other'),
    ], string='Sync Type', required=True)

    source_model = fields.Char(string='Target Model',
                                help='Technical model the offline record was synced into, '
                                     'e.g. garment.production.entry.')
    source_res_id = fields.Integer(string='Target Record ID',
                                    help='ID of the record created/updated in the ERP once synced.')

    offline_created_at = fields.Datetime(string='Captured Offline At',
                                          help='Client-side timestamp of when the data was captured '
                                               'on the device, before connectivity returned.')
    synced_at = fields.Datetime(string='Synced At', default=fields.Datetime.now)

    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('failed', 'Failed'),
        ('conflict', 'Conflict'),
    ], string='Sync Status', default='pending', required=True)

    payload = fields.Text(string='Raw Payload (JSON)',
                           help='The offline-captured JSON payload exactly as received, kept for audit and replay.')
    error_message = fields.Text(string='Error Message', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sync_number', _('New')) == _('New'):
                vals['sync_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.mobile.offline.sync.log') or _('New')
        return super().create(vals_list)

    def action_mark_synced(self):
        self.write({'sync_status': 'synced', 'synced_at': fields.Datetime.now(), 'error_message': False})

    def action_mark_failed(self, error_message=False):
        self.write({'sync_status': 'failed', 'error_message': error_message or _('Sync failed.')})
