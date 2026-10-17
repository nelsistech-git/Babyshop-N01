# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from .constants import G_OFFICER, G_MANAGER, require_group

BOE_LOCKED = {'name', 'date', 'file_id', 'attachment_ids', 'customs_station', 'invoice_ref'}


class NelsisCommercialBoe(models.Model):
    _name = 'nelsis.commercial.boe'
    _description = 'Bill of Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Bill of Entry No.', required=True, tracking=True)
    date = fields.Date(string='B/E Date', tracking=True)
    customs_station = fields.Char(string='Customs Station / Port')
    file_id = fields.Many2one('nelsis.commercial.file', required=True, ondelete='restrict', index=True, tracking=True)
    company_id = fields.Many2one(related='file_id.company_id', store=True, index=True)
    lc_display = fields.Char(related='file_id.lc_display', string='LC')
    shipment_id = fields.Many2one('nelsis.commercial.shipment', domain="[('file_id', '=', file_id)]")
    invoice_ref = fields.Char(string='Supplier Invoice Ref.')
    officer_id = fields.Many2one('res.users', string='Responsible Officer', default=lambda self: self.env.user)
    state = fields.Selection([('draft', 'Draft'), ('submitted', 'Submitted'), ('verified', 'Verified'),
                              ('cleared', 'Cleared'), ('cancel', 'Cancelled')],
                             default='draft', required=True, tracking=True, copy=False)
    clearance_date = fields.Date(tracking=True)
    verified_by = fields.Many2one('res.users', readonly=True, copy=False)
    verified_date = fields.Datetime(readonly=True, copy=False)
    attachment_ids = fields.Many2many('ir.attachment', 'nelsis_commercial_boe_attachment_rel',
                                      'boe_id', 'attachment_id', string='Supporting Attachments', copy=False)
    picking_ids = fields.Many2many('stock.picking', 'nelsis_commercial_boe_picking_rel',
                                   'boe_id', 'picking_id', string='Related Receipts')
    line_ids = fields.One2many('nelsis.commercial.line', 'boe_id')
    notes = fields.Text()

    _sql_constraints = [
        ('name_company_unique', 'unique(name, company_id)', 'This Bill of Entry number already exists.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.pop('state', None)
        records = super().create(vals_list)
        records._link_attachments()
        return records

    def write(self, vals):
        if 'state' in vals:
            if vals['state'] in ('verified', 'cleared'):
                require_group(self.env, G_MANAGER)
            else:
                require_group(self.env, G_OFFICER)
        if BOE_LOCKED & set(vals) and self.filtered(lambda b: b.state in ('verified', 'cleared')):
            raise UserError(_("A verified or cleared Bill of Entry is locked. Ask a manager to reset it first."))
        res = super().write(vals)
        if 'attachment_ids' in vals:
            self._link_attachments()
        return res

    def unlink(self):
        if any(rec.state != 'draft' for rec in self):
            raise UserError(_("Only draft Bills of Entry can be deleted. Cancel it to keep the audit history."))
        return super().unlink()

    def _link_attachments(self):
        for rec in self:
            atts = rec.attachment_ids.filtered(lambda a: a.res_model != rec._name or a.res_id != rec.id)
            if atts:
                atts.sudo().write({'res_model': rec._name, 'res_id': rec.id})

    def action_submit(self):
        require_group(self.env, G_OFFICER)
        if any(r.state != 'draft' for r in self):
            raise UserError(_("Only draft Bills of Entry can be submitted."))
        self.write({'state': 'submitted'})

    def action_verify(self):
        require_group(self.env, G_MANAGER)
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_("Only submitted Bills of Entry can be verified."))
            if not rec.attachment_ids:
                raise UserError(_("Attach the Bill of Entry copy before verification."))
        self.write({'state': 'verified', 'verified_by': self.env.user.id, 'verified_date': fields.Datetime.now()})

    def action_clear(self):
        require_group(self.env, G_MANAGER)
        for rec in self:
            if rec.state != 'verified':
                raise UserError(_("Customs clearance can only be recorded after the Bill of Entry is verified."))
        for rec in self:
            rec.write({'state': 'cleared', 'clearance_date': rec.clearance_date or fields.Date.context_today(self)})

    def action_reset_draft(self):
        require_group(self.env, G_MANAGER)
        if any(r.state not in ('submitted', 'verified', 'cancel') for r in self):
            raise UserError(_("A cleared Bill of Entry cannot be reset; cancel it with a documented reason."))
        self.write({'state': 'draft'})

    def action_cancel(self):
        require_group(self.env, G_MANAGER)
        self.write({'state': 'cancel'})
