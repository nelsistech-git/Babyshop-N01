# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

from .constants import G_OFFICER


class NelsisLcDocument(models.Model):
    """Document checklist line of an LC or of one of its shipments."""
    _name = 'nelsis.lc.document'
    _description = 'LC Document Checklist Line'
    _inherit = ['nelsis.lc.guard.mixin']
    _order = 'lc_id, shipment_id, sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char('Reference / Number')
    type_id = fields.Many2one('nelsis.lc.document.type', string='Document', required=True, ondelete='restrict')
    lc_id = fields.Many2one('nelsis.lc', string='Letter of Credit', required=True, index=True,
                            ondelete='cascade')
    shipment_id = fields.Many2one('nelsis.lc.shipment', string='Shipment',
                                  domain="[('lc_id', '=', lc_id)]", ondelete='cascade')
    company_id = fields.Many2one(related='lc_id.company_id', store=True, index=True)
    partner_id = fields.Many2one(related='lc_id.partner_id', store=True, string='Supplier')
    is_required = fields.Boolean('Required')
    doc_date = fields.Date('Document Date')
    due_date = fields.Date('Due Date')
    state = fields.Selection([
        ('pending', 'Pending'), ('received', 'Received'), ('waived', 'Waived'),
    ], default='pending', required=True, readonly=True, copy=False, index=True)
    attachment_ids = fields.Many2many('ir.attachment', 'nelsis_lc_document_attachment_rel',
                                      'document_id', 'attachment_id', string='Attachments')
    note = fields.Text()
    waive_reason = fields.Text(readonly=True, copy=False)
    reminded = fields.Boolean(copy=False)

    @api.constrains('shipment_id', 'lc_id')
    def _check_shipment(self):
        for doc in self:
            if doc.shipment_id and doc.shipment_id.lc_id != doc.lc_id:
                raise ValidationError(_('The shipment does not belong to the selected LC.'))

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id:
            self.is_required = self.type_id.required_default

    def _check_editable(self):
        user = self.env.user
        for doc in self:
            if doc.lc_id.state in ('closed', 'cancelled'):
                raise UserError(_('LC %s is closed or cancelled; its checklist is locked.', doc.lc_id.name))
            if doc.lc_id.state != 'draft' and not user.has_group(G_OFFICER):
                raise AccessError(_('Only LC Officers may change the checklist after the LC leaves Draft.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'is_required' not in vals and vals.get('type_id'):
                vals['is_required'] = self.env['nelsis.lc.document.type'].browse(vals['type_id']).required_default
            if not self.env.su:
                vals['state'] = 'pending'
        records = super().create(vals_list)
        if not self.env.su:
            records._check_editable()
        return records

    def write(self, vals):
        if not self.env.su:
            business = self._business_vals(vals)
            if business:
                if business & {'state', 'waive_reason'}:
                    raise UserError(_('Use the Received / Waive buttons to change the document status.'))
                if business & {'lc_id'}:
                    raise UserError(_('The LC of a checklist line cannot be changed.'))
                self._check_editable()
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            self._check_editable()
            if any(doc.state != 'pending' for doc in self):
                raise UserError(_('Received or waived documents are part of the record and cannot be deleted.'))
        return super().unlink()

    def action_mark_received(self):
        self._assert_group(G_OFFICER)
        today = fields.Date.context_today(self)
        for doc in self:
            if doc.state != 'pending':
                raise UserError(_('Only pending documents can be marked received.'))
            if doc.lc_id.state in ('closed', 'cancelled'):
                raise UserError(_('LC %s is closed or cancelled.', doc.lc_id.name))
            doc.sudo().write({'state': 'received', 'doc_date': doc.doc_date or today})
            doc.lc_id._log(_('Document received: %s', doc.type_id.name))
        return True

    def action_waive(self):
        self._assert_group(G_OFFICER)
        self.ensure_one()
        return self._open_reason_wizard('document_waive', _('Waive Document'))

    def _do_waive(self, reason):
        self._assert_group(G_OFFICER)
        for doc in self:
            if doc.state != 'pending':
                raise UserError(_('Only pending documents can be waived.'))
            doc.sudo().write({'state': 'waived', 'waive_reason': reason})
            doc.lc_id._log(_('Document waived: %s', doc.type_id.name), note=reason)
