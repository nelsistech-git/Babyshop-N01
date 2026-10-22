# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Import Permission (IP) Management (SRS section 26) —
garment.import.permission. Covers Fabric/Accessories/Chemical/Spare
Parts/Machinery/Raw Material import tracking (SRS section 19), driven off
a Back-to-Back LC opened against the Master LC (garment.lc)."""
from odoo import api, fields, models, _


class GarmentImportPermission(models.Model):
    _name = 'garment.import.permission'
    _description = 'Garment Import Permission (IP)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'validity_date desc'

    ip_number = fields.Char(string='IP Number', copy=False, readonly=True, default=lambda s: _('New'))
    import_category = fields.Selection([
        ('fabric', 'Fabric Import'), ('accessories', 'Accessories Import'), ('chemical', 'Chemical Import'),
        ('spare_parts', 'Spare Parts Import'), ('machinery', 'Machinery Import'),
        ('raw_material', 'Raw Material Import'),
    ], string='Import Category', required=True, tracking=True)

    supplier_id = fields.Many2one('garment.supplier', string='Supplier', required=True)
    material_id = fields.Many2one('garment.material', string='Material')
    material_description = fields.Char(string='Material Description')
    quantity = fields.Float(string='Quantity', required=True)
    uom = fields.Char(string='UOM', default='Meter')
    value = fields.Monetary(string='Value', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    validity_date = fields.Date(string='Validity Date', tracking=True)

    btb_lc_id = fields.Many2one('garment.lc', string='Back-to-Back LC',
                                 domain="[('lc_type', '=', 'back_to_back')]")
    bond_license_id = fields.Many2one('garment.bond.license', string='Bond License')

    status = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('utilized', 'Utilized'), ('expired', 'Expired'),
    ], string='Status', default='draft', tracking=True)

    ud_ids = fields.One2many('garment.utilization.declaration', 'import_permission_id',
                              string='Utilization Declarations')
    ud_count = fields.Integer(compute='_compute_ud_totals')
    consumed_qty = fields.Float(string='Consumed Quantity', compute='_compute_ud_totals', store=True)
    remaining_qty = fields.Float(string='Remaining Quantity', compute='_compute_ud_totals', store=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('ip_number_uniq', 'unique(ip_number, company_id)', 'IP Number must be unique per company!'),
    ]

    @api.depends('quantity', 'ud_ids.consumed_qty')
    def _compute_ud_totals(self):
        for rec in self:
            rec.ud_count = len(rec.ud_ids)
            rec.consumed_qty = sum(rec.ud_ids.mapped('consumed_qty'))
            rec.remaining_qty = rec.quantity - rec.consumed_qty

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ip_number', _('New')) == _('New'):
                vals['ip_number'] = self.env['ir.sequence'].next_by_code('garment.import.permission') or _('New')
        return super().create(vals_list)

    def action_view_ud(self):
        self.ensure_one()
        return {'name': _('Utilization Declarations'), 'type': 'ir.actions.act_window',
                'res_model': 'garment.utilization.declaration', 'view_mode': 'tree,form',
                'domain': [('import_permission_id', '=', self.id)],
                'context': {'default_import_permission_id': self.id}}
