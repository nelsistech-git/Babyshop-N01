# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwSupplierScorecard(models.Model):
    _name = 'fw.supplier.scorecard'
    _description = 'Footwear Supplier Scorecard'
    _inherit = ['mail.thread']
    _order = 'period_end desc'

    name = fields.Char(string='Scorecard Reference', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.supplier.scorecard') or 'New')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True,
                                   domain="[('supplier_rank', '>', 0)]", tracking=True)

    period_start = fields.Date(string='Period Start', required=True)
    period_end = fields.Date(string='Period End', required=True)

    quality_weight = fields.Float(string='Quality Weight (%)', default=50.0)
    delivery_weight = fields.Float(string='Delivery Weight (%)', default=50.0)

    @api.constrains('quality_weight', 'delivery_weight')
    def _check_weights_non_negative(self):
        for rec in self:
            if rec.quality_weight < 0:
                raise ValidationError("Quality Weight cannot be negative.")
            if rec.delivery_weight < 0:
                raise ValidationError("Delivery Weight cannot be negative.")

    grn_count = fields.Integer(string='GRN Count Considered', readonly=True)
    quality_score = fields.Float(string='Quality Score (Avg. Acceptance %)', readonly=True)

    delivery_count = fields.Integer(string='Deliveries Considered', readonly=True)
    delivery_score = fields.Float(string='Delivery Score (On-Time %)', readonly=True)

    overall_score = fields.Float(string='Overall Score', compute='_compute_overall_score',
                                  store=True)
    grade = fields.Selection([
        ('a', 'A - Excellent'),
        ('b', 'B - Good'),
        ('c', 'C - Acceptable'),
        ('d', 'D - Poor'),
    ], string='Grade', compute='_compute_overall_score', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.supplier.scorecard') or 'New'
        return super().create(vals_list)

    @api.depends('quality_score', 'delivery_score', 'quality_weight', 'delivery_weight')
    def _compute_overall_score(self):
        for rec in self:
            total_weight = (rec.quality_weight or 0.0) + (rec.delivery_weight or 0.0)
            if total_weight:
                rec.overall_score = (
                    rec.quality_score * (rec.quality_weight or 0.0)
                    + rec.delivery_score * (rec.delivery_weight or 0.0)
                ) / total_weight
            else:
                rec.overall_score = 0.0

            if rec.overall_score >= 90:
                rec.grade = 'a'
            elif rec.overall_score >= 75:
                rec.grade = 'b'
            elif rec.overall_score >= 60:
                rec.grade = 'c'
            else:
                rec.grade = 'd'

    def action_compute_scores(self):
        for rec in self:
            if not rec.period_start or not rec.period_end:
                raise UserError("Please set both Period Start and Period End first.")
            if rec.period_start > rec.period_end:
                raise UserError("Period Start cannot be after Period End.")

            grn_records = self.env['fw.material.grn'].search([
                ('supplier_id', '=', rec.supplier_id.id),
                ('received_date', '>=', rec.period_start),
                ('received_date', '<=', rec.period_end),
                ('state', '=', 'inspected'),
            ])
            quality_score = 0.0
            if grn_records:
                quality_score = sum(grn_records.mapped('acceptance_rate')) / len(grn_records)

            delivery_records = self.env['fw.supplier.delivery'].search([
                ('supplier_id', '=', rec.supplier_id.id),
                ('promised_date', '>=', rec.period_start),
                ('promised_date', '<=', rec.period_end),
                ('actual_delivery_date', '!=', False),
            ])
            delivery_score = 0.0
            if delivery_records:
                on_time_count = len(delivery_records.filtered('on_time'))
                delivery_score = on_time_count / len(delivery_records) * 100.0

            rec.write({
                'grn_count': len(grn_records),
                'quality_score': quality_score,
                'delivery_count': len(delivery_records),
                'delivery_score': delivery_score,
            })

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})
