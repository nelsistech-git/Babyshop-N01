# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from datetime import timedelta

from odoo import api, fields, models


class FwFactoryCertification(models.Model):
    _name = 'fw.factory.certification'
    _description = 'Footwear Factory Owned Certification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'

    factory_id = fields.Many2one('fw.factory', string='Factory', required=True, tracking=True)
    certification_type = fields.Selection([
        ('iso9001', 'ISO 9001'),
        ('iso14001', 'ISO 14001'),
        ('iso45001', 'ISO 45001'),
        ('bsci', 'BSCI'),
        ('wrap', 'WRAP'),
        ('sedex', 'SEDEX / SMETA'),
        ('higg_index', 'Higg Index (Worldly)'),
        ('bluesign', 'bluesign'),
        ('grs', 'Global Recycled Standard (GRS)'),
        ('oeko_tex', 'OEKO-TEX'),
        ('other', 'Other'),
    ], string='Certification Type', required=True, default='iso9001', tracking=True)

    certificate_no = fields.Char(string='Certificate No.')
    issuing_body = fields.Char(string='Issuing Body')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)

    status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon (within 60 days)'),
        ('expired', 'Expired'),
    ], string='Status', compute='_compute_status', store=True)

    responsible_id = fields.Many2one('res.users', string='Responsible',
                                      default=lambda self: self.env.user)
    remarks = fields.Text(string='Remarks')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.depends('expiry_date')
    def _compute_status(self):
        today = fields.Date.context_today(self)
        soon_cutoff = today + timedelta(days=60)
        for rec in self:
            if not rec.expiry_date:
                rec.status = 'valid'
            elif rec.expiry_date < today:
                rec.status = 'expired'
            elif rec.expiry_date <= soon_cutoff:
                rec.status = 'expiring_soon'
            else:
                rec.status = 'valid'

    @api.model
    def _cron_notify_expiring_certifications(self):
        """Scheduled action: create an activity on any factory certification that is
        expired or expiring within 60 days, assigned to its Responsible user."""
        certs = self.search([('status', 'in', ('expiring_soon', 'expired'))])
        for cert in certs:
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'fw.factory.certification'),
                ('res_id', '=', cert.id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ], limit=1)
            if existing:
                continue
            note = "Certification %s for factory %s is %s (expiry: %s). Please renew." % (
                cert.certification_type, cert.factory_id.name,
                'expired' if cert.status == 'expired' else 'expiring soon',
                cert.expiry_date)
            cert.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='Factory certification needs renewal',
                note=note,
                user_id=cert.responsible_id.id or self.env.user.id,
            )
