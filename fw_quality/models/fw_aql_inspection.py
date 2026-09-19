# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwAqlInspection(models.Model):
    _name = 'fw.aql.inspection'
    _description = 'Footwear AQL Sampling Inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(string='Inspection Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.aql.inspection') or 'New')
    inspection_type = fields.Selection([
        ('inline', 'Inline'),
        ('final', 'Final Inspection'),
        ('pre_shipment', 'Pre-Shipment Inspection'),
    ], string='Inspection Type', required=True, default='final', tracking=True)

    production_order_id = fields.Many2one('fw.production.order', string='Production Order',
                                           tracking=True)
    shipment_id = fields.Many2one('fw.shipment', string='Shipment', tracking=True)
    style_id = fields.Many2one('fw.style', string='Style')

    date = fields.Date(string='Inspection Date', default=fields.Date.context_today)
    inspector_id = fields.Many2one('res.users', string='Inspector',
                                    default=lambda self: self.env.user)

    lot_size = fields.Integer(string='Lot Size', required=True, default=0)
    inspection_level = fields.Selection([
        ('i', 'Level I (Reduced)'),
        ('ii', 'Level II (Normal)'),
        ('iii', 'Level III (Tightened)'),
    ], string='Inspection Level', default='ii', required=True)

    aql_table_id = fields.Many2one('fw.aql.table', string='Matched AQL Reference Row',
                                    readonly=True, copy=False)
    sample_size = fields.Integer(string='Sample Size')

    ac_major = fields.Integer(string='Accept (Major)')
    re_major = fields.Integer(string='Reject (Major)')
    ac_minor = fields.Integer(string='Accept (Minor)')
    re_minor = fields.Integer(string='Reject (Minor)')
    ac_critical = fields.Integer(string='Accept (Critical)')
    re_critical = fields.Integer(string='Reject (Critical)')

    found_critical_qty = fields.Integer(string='Found Critical Defects', default=0)
    found_major_qty = fields.Integer(string='Found Major Defects', default=0)
    found_minor_qty = fields.Integer(string='Found Minor Defects', default=0)

    defect_line_ids = fields.One2many('fw.aql.defect.line', 'inspection_id', string='Defects Found')

    result = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Result', compute='_compute_result', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.aql.inspection') or 'New'
        return super().create(vals_list)

    @api.depends('found_critical_qty', 're_critical', 'found_major_qty', 're_major',
                 'found_minor_qty', 're_minor', 'sample_size')
    def _compute_result(self):
        for rec in self:
            if not rec.sample_size:
                rec.result = 'pending'
                continue
            failed = (
                (rec.re_critical and rec.found_critical_qty >= rec.re_critical) or
                (rec.re_major and rec.found_major_qty >= rec.re_major) or
                (rec.re_minor and rec.found_minor_qty >= rec.re_minor)
            )
            rec.result = 'fail' if failed else 'pass'

    @api.constrains('lot_size', 'found_critical_qty', 'found_major_qty', 'found_minor_qty')
    def _check_non_negative(self):
        for rec in self:
            for field_name, label in [
                ('lot_size', 'Lot Size'), ('found_critical_qty', 'Found Critical Defects'),
                ('found_major_qty', 'Found Major Defects'),
                ('found_minor_qty', 'Found Minor Defects'),
            ]:
                if rec[field_name] < 0:
                    raise ValidationError("%s cannot be negative." % label)

    def action_determine_sample(self):
        for rec in self:
            if not rec.lot_size:
                raise UserError("Please enter the Lot Size before determining the sample size.")
            domain = [
                ('inspection_level', '=', rec.inspection_level),
                ('lot_size_min', '<=', rec.lot_size),
                '|',
                ('lot_size_max', '=', 0),
                ('lot_size_max', '>=', rec.lot_size),
            ]
            table_row = self.env['fw.aql.table'].search(domain, limit=1)
            if not table_row:
                raise UserError(
                    "No matching AQL reference row found for Lot Size %d at Inspection "
                    "Level %s. Please add a matching row in the AQL Sampling Table "
                    "(Quality > AQL Sampling Table)." % (rec.lot_size, rec.inspection_level))
            rec.write({
                'aql_table_id': table_row.id,
                'sample_size': table_row.sample_size,
                'ac_major': table_row.ac_major,
                're_major': table_row.re_major,
                'ac_minor': table_row.ac_minor,
                're_minor': table_row.re_minor,
                'ac_critical': table_row.ac_critical,
                're_critical': table_row.re_critical,
            })

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        for rec in self:
            if not rec.sample_size:
                raise UserError(
                    "Please determine the sample size (AQL lookup) before completing "
                    "the inspection.")
        self.write({'state': 'completed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class FwAqlDefectLine(models.Model):
    _name = 'fw.aql.defect.line'
    _description = 'AQL Inspection Defect Line'
    _order = 'id'

    inspection_id = fields.Many2one('fw.aql.inspection', string='AQL Inspection', required=True,
                                     ondelete='cascade')
    defect_code_id = fields.Many2one('fw.defect.code', string='Defect Code', required=True)
    severity = fields.Selection(related='defect_code_id.severity', string='Severity', store=True)
    qty = fields.Integer(string='Qty', required=True, default=1)
    remarks = fields.Char(string='Remarks')

    @api.constrains('qty')
    def _check_qty_non_negative(self):
        for rec in self:
            if rec.qty < 0:
                raise ValidationError("Defect Qty cannot be negative.")
