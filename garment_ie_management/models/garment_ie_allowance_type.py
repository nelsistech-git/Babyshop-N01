# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Allowance Type master (SRS s.16) — Personal / Fatigue / Delay / Machine
Delay allowance policy used by SMV Master and Time Study to build up the
total allowance percentage added on top of Basic/Normal Time."""
from odoo import fields, models


class GarmentIeAllowanceType(models.Model):
    _name = 'garment.ie.allowance.type'
    _description = 'Garment IE Allowance Type'
    _order = 'category, name'

    name = fields.Char(string='Allowance Name', required=True)
    code = fields.Char(string='Code')
    category = fields.Selection([
        ('personal', 'Personal Allowance'),
        ('fatigue', 'Fatigue Allowance'),
        ('delay', 'Delay Allowance'),
        ('machine_delay', 'Machine Delay'),
        ('other', 'Other'),
    ], string='Category', required=True)
    default_pct = fields.Float(string='Default Allowance (%)', required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
