# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models


class FwFabricSwatch(models.Model):
    _name = 'fw.fabric.swatch'
    _description = 'Footwear Fabric / Trim Swatch Library'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Swatch Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.fabric.swatch') or 'New')
    material_type = fields.Selection([
        ('fabric', 'Fabric'),
        ('leather', 'Leather'),
        ('synthetic', 'Synthetic Upper Material'),
        ('trim', 'Trim / Accessory'),
        ('lining', 'Lining'),
        ('sole_material', 'Sole Material'),
        ('other', 'Other'),
    ], string='Material Type', required=True, default='fabric', tracking=True)

    material_description = fields.Char(string='Material Description', required=True)
    color_id = fields.Many2one('fw.color', string='Color')
    supplier_id = fields.Many2one('res.partner', string='Supplier',
                                   domain="[('supplier_rank', '>', 0)]")
    location_id = fields.Many2one('fw.sample.location', string='Storage Location')
    received_date = fields.Date(string='Received Date', default=fields.Date.context_today)

    style_ids = fields.Many2many('fw.style', string='Used in Styles',
                                  help="Styles that reference this swatch, for quick "
                                       "cross-lookup when a material needs to be re-sourced.")

    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.fabric.swatch') or 'New'
        return super().create(vals_list)
