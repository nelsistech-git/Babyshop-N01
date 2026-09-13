# -*- coding: utf-8 -*-
"""Configurable installation checklist (SRS 37)."""

from odoo import api, fields, models


class GcErmChecklistTemplate(models.Model):
    _name = 'gc.erm.checklist.template'
    _description = 'GC ERM Installation Checklist Template'
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_default = fields.Boolean(
        string='Default Template',
        help='Template proposed automatically on new installation records.')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    service_ids = fields.Many2many(
        'gc.erm.service.catalog', string='Applicable Services',
        help='Leave empty to make the template available for every service.')
    item_ids = fields.One2many(
        'gc.erm.checklist.template.item', 'template_id', string='Checklist Items',
        copy=True)
    item_count = fields.Integer(string='Items', compute='_compute_item_count')

    @api.depends('item_ids')
    def _compute_item_count(self):
        for template in self:
            template.item_count = len(template.item_ids)

    @api.model
    def _get_default_template(self, service=None):
        domain = [('active', '=', True),
                  ('company_id', 'in', (False, self.env.company.id))]
        if service:
            candidate = self.search(
                domain + [('service_ids', 'in', service.ids)], limit=1)
            if candidate:
                return candidate
        return self.search(domain + [('is_default', '=', True)], limit=1) \
            or self.search(domain, limit=1)


class GcErmChecklistTemplateItem(models.Model):
    _name = 'gc.erm.checklist.template.item'
    _description = 'GC ERM Checklist Template Item'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'gc.erm.checklist.template', string='Template', required=True,
        ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Checklist Item', required=True, translate=True)
    mandatory = fields.Boolean(
        string='Mandatory', default=True,
        help='A mandatory item must be answered Yes or N/A before the '
             'installation report can be submitted.')
    category = fields.Selection([
        ('site', 'Site Readiness'),
        ('material', 'Material'),
        ('install', 'Installation'),
        ('test', 'Testing'),
        ('customer', 'Customer'),
    ], string='Category', default='install', required=True)
    help_text = fields.Char(string='Guidance', translate=True)
