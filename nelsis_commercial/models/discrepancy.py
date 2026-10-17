# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from .constants import G_OFFICER, G_MANAGER, require_group


class NelsisCommercialDiscrepancy(models.Model):
    _name = 'nelsis.commercial.discrepancy'
    _description = 'Documented vs Received Quantity Comparison'
    _inherit = ['mail.thread']
    _order = 'file_id, id'

    line_id = fields.Many2one('nelsis.commercial.line', required=True, ondelete='cascade', index=True)
    file_id = fields.Many2one('nelsis.commercial.file', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='file_id.company_id', store=True, index=True)
    shipment_id = fields.Many2one(related='line_id.shipment_id', store=True)
    product_id = fields.Many2one(related='line_id.product_id', store=True)
    source_kind = fields.Selection(related='line_id.source_kind', store=True)
    uom_id = fields.Many2one(related='line_id.uom_id', string='Documented Unit')
    documented_qty = fields.Float(related='line_id.qty', string='Documented Qty')
    received_qty = fields.Float(string='Received Qty')
    received_uom_id = fields.Many2one('uom.uom', string='Received Unit')
    difference = fields.Float(compute='_compute_difference', string='Difference (Received - Documented)')
    state = fields.Selection(
        [('pending', 'Pending Receipt'), ('ok', 'Within Tolerance'), ('mismatch', 'Mismatch'),
         ('uom_review', 'Unit Review Needed'), ('approved', 'Approved with Explanation')],
        default='pending', required=True, tracking=True)
    basis = fields.Text(string='Source / Basis of Comparison', readonly=True)
    explanation = fields.Text(tracking=True)
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    approved_date = fields.Datetime(readonly=True, copy=False)

    @api.depends('received_qty', 'documented_qty')
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.received_qty - rec.documented_qty

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('state') == 'approved':
                vals['state'] = 'pending'
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('state') == 'approved':
            require_group(self.env, G_MANAGER)
        elif 'state' in vals:
            require_group(self.env, G_OFFICER)
        return super().write(vals)

    def unlink(self):
        raise UserError(_("Comparison records are part of the audit trail and cannot be deleted."))

    @api.constrains('state', 'explanation')
    def _check_explanation(self):
        for rec in self:
            if rec.state == 'approved' and not rec.explanation:
                raise ValidationError(_("An explanation is mandatory to approve a discrepancy."))

    def action_approve(self):
        require_group(self.env, G_MANAGER)
        for rec in self:
            if rec.state not in ('mismatch', 'uom_review'):
                raise UserError(_("Only mismatches or unit-review items can be approved."))
            if not rec.explanation:
                raise UserError(_("Record an explanation before approving."))
        self.write({'state': 'approved', 'approved_by': self.env.user.id, 'approved_date': fields.Datetime.now()})
