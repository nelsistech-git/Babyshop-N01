# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError


class FwWorkerIncentive(models.Model):
    _name = 'fw.worker.incentive'
    _description = 'Footwear Worker Incentive Calculation'
    _inherit = ['mail.thread']
    _order = 'period_end desc'

    name = fields.Char(string='Incentive Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.worker.incentive') or 'New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    scheme_id = fields.Many2one('fw.incentive.scheme', string='Incentive Scheme', required=True)
    scheme_type = fields.Selection(related='scheme_id.scheme_type', string='Scheme Type')

    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)

    currency_id = fields.Many2one(related='scheme_id.currency_id', string='Currency', store=True)

    total_qty_produced = fields.Integer(string='Total Qty Produced (Piece Rate)', readonly=True,
                                         help="Auto-computed from Worker Output records for "
                                              "this employee within the period, matching the "
                                              "scheme's Operation if one is set.")
    efficiency_percent = fields.Float(string='Efficiency % (for Efficiency Bonus)',
                                       help="Enter the worker's individual efficiency for the "
                                            "period. Individual-level efficiency is not tracked "
                                            "elsewhere in the system, so this is a manual entry.")

    incentive_amount = fields.Monetary(string='Incentive Amount', compute='_compute_incentive',
                                        store=True, currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.worker.incentive') or 'New'
        return super().create(vals_list)

    @api.depends('scheme_id', 'total_qty_produced', 'efficiency_percent')
    def _compute_incentive(self):
        for rec in self:
            if not rec.scheme_id:
                rec.incentive_amount = 0.0
                continue
            if rec.scheme_id.scheme_type == 'piece_rate':
                rec.incentive_amount = (rec.total_qty_produced or 0) \
                    * (rec.scheme_id.rate_per_piece or 0.0)
            elif rec.scheme_id.scheme_type == 'efficiency_bonus':
                excess = (rec.efficiency_percent or 0.0) \
                    - (rec.scheme_id.efficiency_threshold_percent or 0.0)
                excess = max(excess, 0.0)
                rec.incentive_amount = excess * (rec.scheme_id.bonus_rate_per_percent or 0.0)
            else:
                rec.incentive_amount = 0.0

    def action_pull_qty_produced(self):
        for rec in self:
            if not rec.period_start or not rec.period_end:
                raise UserError("Please set both Period Start and Period End first.")
            domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('date', '>=', rec.period_start),
                ('date', '<=', rec.period_end),
            ]
            if rec.scheme_id.operation_id:
                domain.append(('operation_id', '=', rec.scheme_id.operation_id.id))
            outputs = self.env['fw.worker.output'].search(domain)
            rec.total_qty_produced = sum(outputs.mapped('qty_produced'))

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
