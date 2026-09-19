# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from datetime import timedelta

from odoo import api, fields, models


class FwBuyerCompliance(models.Model):
    _name = 'fw.buyer.compliance'
    _description = 'Footwear Buyer Compliance Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'

    buyer_id = fields.Many2one('fw.buyer', string='Buyer', required=True, tracking=True)
    certificate_type = fields.Selection([
        ('bsci', 'BSCI'),
        ('wrap', 'WRAP'),
        ('sedex', 'SEDEX / SMETA'),
        ('iso9001', 'ISO 9001'),
        ('iso14001', 'ISO 14001'),
        ('iso45001', 'ISO 45001'),
        ('gots', 'GOTS'),
        ('oeko_tex', 'OEKO-TEX'),
        ('higg_index', 'Higg Index'),
        ('other', 'Other'),
    ], string='Certificate Type', required=True, default='bsci', tracking=True)

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
    def _cron_notify_expiring_certificates(self):
        """Scheduled action: create an activity on any certificate that is expired or
        expiring within 60 days, assigned to its Responsible user, so the person who
        needs to renew it gets a reminder without anyone manually checking dates."""
        certs = self.search([('status', 'in', ('expiring_soon', 'expired'))])
        for cert in certs:
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'fw.buyer.compliance'),
                ('res_id', '=', cert.id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ], limit=1)
            if existing:
                continue
            note = "Certificate %s for buyer %s is %s (expiry: %s). Please renew." % (
                cert.certificate_type, cert.buyer_id.name,
                'expired' if cert.status == 'expired' else 'expiring soon',
                cert.expiry_date)
            cert.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='Compliance certificate needs renewal',
                note=note,
                user_id=cert.responsible_id.id or self.env.user.id,
            )
