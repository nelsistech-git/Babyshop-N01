# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .constants import G_OFFICER, LIVE_STATES


class NelsisLcBoe(models.Model):
    """Bill of Entry reference linked to an LC (and optionally a shipment).

    Duty amounts are entered from customs documents; this module never
    computes duties or statutory values.
    """
    _name = 'nelsis.lc.boe'
    _description = 'LC Bill of Entry'
    _inherit = ['nelsis.lc.guard.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'boe_date desc, id desc'

    name = fields.Char('Bill of Entry No.', required=True, tracking=True, index=True)
    lc_id = fields.Many2one('nelsis.lc', string='Letter of Credit', required=True, index=True,
                            ondelete='cascade', tracking=True)
    shipment_id = fields.Many2one('nelsis.lc.shipment', string='Shipment',
                                  domain="[('lc_id', '=', lc_id)]", tracking=True, ondelete='restrict')
    company_id = fields.Many2one(related='lc_id.company_id', store=True, index=True)
    company_currency_id = fields.Many2one(related='lc_id.company_id.currency_id', string='Company Currency')
    partner_id = fields.Many2one(related='lc_id.partner_id', store=True, string='Supplier')
    boe_date = fields.Date('BoE Date', default=fields.Date.context_today)
    customs_house = fields.Char('Customs House / Station')
    assessed_value = fields.Monetary('Assessed Value', currency_field='company_currency_id')
    duty_paid_amount = fields.Monetary('Duty / Tax Paid (as per customs)', currency_field='company_currency_id')
    clearance_date = fields.Date('Clearance Date', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('cleared', 'Cleared'), ('cancelled', 'Cancelled'),
    ], default='draft', required=True, readonly=True, copy=False, tracking=True, index=True)
    note = fields.Text()

    @api.constrains('shipment_id', 'lc_id')
    def _check_shipment(self):
        for boe in self:
            if boe.shipment_id and boe.shipment_id.lc_id != boe.lc_id:
                raise ValidationError(_('The shipment does not belong to the selected LC.'))

    @api.constrains('boe_date', 'clearance_date')
    def _check_dates(self):
        for boe in self:
            if boe.boe_date and boe.clearance_date and boe.clearance_date < boe.boe_date:
                raise ValidationError(_('The clearance date cannot be before the Bill of Entry date.'))

    @api.onchange('lc_id')
    def _onchange_lc_id(self):
        if self.shipment_id and self.shipment_id.lc_id != self.lc_id:
            self.shipment_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            lc = self.env['nelsis.lc'].browse(vals.get('lc_id')).exists()
            if not lc:
                raise ValidationError(_('Select a Letter of Credit.'))
            if not self.env.su:
                if lc.state not in LIVE_STATES:
                    raise UserError(_('Bills of Entry can only be added to an opened LC.'))
                vals['state'] = 'draft'
        records = super().create(vals_list)
        for boe in records:
            boe.lc_id._log(_('Bill of Entry %s created', boe.name))
        return records

    def write(self, vals):
        if not self.env.su:
            business = self._business_vals(vals)
            if business:
                if 'state' in business:
                    raise UserError(_('The status can only be changed through the workflow buttons.'))
                if 'lc_id' in business:
                    raise UserError(_('The LC of a Bill of Entry cannot be changed.'))
                if any(b.state in ('cleared', 'cancelled') for b in self):
                    raise UserError(_('Cleared or cancelled Bills of Entry cannot be edited.'))
        return super().write(vals)

    def unlink(self):
        for boe in self:
            if boe.state != 'draft':
                raise UserError(_('Only draft Bills of Entry can be deleted. Cancel %s instead.', boe.name))
        return super().unlink()

    def action_submit(self):
        self._assert_group(G_OFFICER)
        for boe in self:
            if boe.state != 'draft':
                raise UserError(_('Only draft Bills of Entry can be submitted.'))
        self.sudo().write({'state': 'submitted'})
        for boe in self:
            boe.lc_id._log(_('Bill of Entry %s submitted', boe.name))
        return True

    def action_clear(self):
        self._assert_group(G_OFFICER)
        for boe in self:
            if boe.state != 'submitted':
                raise UserError(_('Only submitted Bills of Entry can be marked cleared.'))
            if not boe.clearance_date:
                raise UserError(_('Enter the clearance date for %s first.', boe.name))
        self.sudo().write({'state': 'cleared'})
        for boe in self:
            boe.lc_id._log(_('Bill of Entry %s cleared', boe.name))
        return True

    def action_cancel(self):
        self._assert_group(G_OFFICER)
        self.ensure_one()
        return self._open_reason_wizard('boe_cancel', _('Cancel Bill of Entry'))

    def _do_cancel(self, reason):
        self._assert_group(G_OFFICER)
        for boe in self:
            if boe.state in ('cancelled',):
                raise UserError(_('%s is already cancelled.', boe.name))
            boe.sudo().write({'state': 'cancelled', 'note': ((boe.note or '') + '\n' + reason).strip()})
            boe.lc_id._log(_('Bill of Entry %s cancelled', boe.name), note=reason)
