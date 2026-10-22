# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentCostRevision(models.Model):
    """Costing Version Management (SRS sections 21-22) —
    garment.cost.revision."""
    _name = 'garment.cost.revision'
    _description = 'Garment Costing Revision'
    _inherit = ['mail.thread']
    _order = 'version_number desc'

    costing_id = fields.Many2one('garment.costing', string='Costing', required=True, ondelete='cascade')
    version_number = fields.Integer(string='Version Number', required=True, default=1)
    previous_version_id = fields.Many2one('garment.cost.revision', string='Previous Version')
    change_date = fields.Datetime(string='Change Date', default=fields.Datetime.now)
    changed_by_id = fields.Many2one('res.users', string='Changed By', default=lambda s: s.env.user)
    change_reason = fields.Selection([
        ('fabric_price_increase', 'Fabric Price Increase'), ('trim_price_change', 'Trim Price Change'),
        ('buyer_spec_change', 'Buyer Specification Change'), ('consumption_change', 'Consumption Change'),
        ('process_change', 'Process Change'), ('exchange_rate_change', 'Exchange Rate Change'),
        ('supplier_change', 'Supplier Change'), ('production_cost_change', 'Production Cost Change'),
        ('other', 'Other'),
    ], string='Change Reason', required=True)
    change_notes = fields.Text(string='Change Notes')
    previous_fob_price = fields.Monetary(string='Previous FOB Price', currency_field='currency_id')
    new_fob_price = fields.Monetary(string='New FOB Price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='costing_id.currency_id', store=True)
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.costing_id.message_post(
                body=_('Cost revision v%s created (%s): FOB %.2f -> %.2f') % (
                    rec.version_number, rec.change_reason, rec.previous_fob_price, rec.new_fob_price or 0.0))
        return records

    def action_approve(self):
        for rec in self:
            rec.write({'approval_status': 'approved'})
            if rec.new_fob_price:
                rec.costing_id.write({'is_locked': True})
