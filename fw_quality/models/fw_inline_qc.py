# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwInlineQc(models.Model):
    _name = 'fw.inline.qc'
    _description = 'Footwear Inline Quality Check'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(string='QC Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.inline.qc') or 'New')
    production_order_id = fields.Many2one('fw.production.order', string='Production Order',
                                           required=True, tracking=True)
    stage_line_id = fields.Many2one('fw.production.stage.line', string='Process Stage',
                                     required=True,
                                     domain="[('production_order_id', '=', production_order_id)]")
    stage = fields.Selection(related='stage_line_id.stage', string='Stage', store=True)

    date = fields.Date(string='Date', default=fields.Date.context_today)
    inspector_id = fields.Many2one('res.users', string='Inspector',
                                    default=lambda self: self.env.user)

    checked_qty = fields.Integer(string='Checked Qty', required=True, default=0)
    defect_line_ids = fields.One2many('fw.inline.qc.defect.line', 'qc_id', string='Defects Found')

    @api.constrains('checked_qty')
    def _check_checked_qty_non_negative(self):
        for rec in self:
            if rec.checked_qty < 0:
                raise ValidationError("Checked Qty cannot be negative.")

    total_defect_qty = fields.Integer(string='Total Defect Qty', compute='_compute_results',
                                       store=True)
    passed_qty = fields.Integer(string='Passed Qty', compute='_compute_results', store=True)
    dhu_percent = fields.Float(string='DHU % (Defects per Hundred Units)',
                                compute='_compute_results', store=True,
                                help="Total Defect Qty / Checked Qty x 100")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.inline.qc') or 'New'
        return super().create(vals_list)

    @api.depends('checked_qty', 'defect_line_ids.qty')
    def _compute_results(self):
        for rec in self:
            rec.total_defect_qty = sum(rec.defect_line_ids.mapped('qty'))
            rec.passed_qty = max(rec.checked_qty - rec.total_defect_qty, 0)
            rec.dhu_percent = (rec.total_defect_qty / rec.checked_qty * 100.0) \
                if rec.checked_qty else 0.0

    def action_done(self):
        for rec in self:
            if rec.checked_qty <= 0:
                raise UserError("Checked quantity must be greater than zero.")
        self.write({'state': 'done'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class FwInlineQcDefectLine(models.Model):
    _name = 'fw.inline.qc.defect.line'
    _description = 'Inline QC Defect Line'
    _order = 'id'

    qc_id = fields.Many2one('fw.inline.qc', string='Inline QC', required=True,
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
