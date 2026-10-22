# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentTnaRevision(models.Model):
    """TNA Revision Management (SRS section 38) — garment.tna.revision.

    Any major timeline change must create a Revision. This is also the
    sanctioned way to change the Shipment Date on a Completed/Closed TNA
    (SRS section 37 record rule: "Completed TNA cannot be edited without
    revision"), and the Audit Trail example in section 39 (old date / new
    date / reason) maps directly onto this record."""
    _name = 'garment.tna.revision'
    _description = 'Garment TNA Revision'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    revision_number = fields.Char(string='Revision Number', copy=False, readonly=True, default=lambda s: _('New'))
    tna_id = fields.Many2one('garment.tna', string='TNA', required=True, ondelete='cascade')
    previous_shipment_date = fields.Date(string='Previous Timeline (Shipment Date)', required=True)
    new_shipment_date = fields.Date(string='New Timeline (Shipment Date)', required=True)
    change_reason = fields.Selection([
        ('buyer_delay', 'Buyer Delay'), ('material_delay', 'Material Delay'),
        ('production_delay', 'Production Delay'), ('capacity_issue', 'Capacity Issue'),
        ('shipment_change', 'Shipment Change'), ('quality_issue', 'Quality Issue'), ('other', 'Other'),
    ], string='Change Reason', required=True, tracking=True)
    notes = fields.Text(string='Notes')
    requested_by_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('revision_number', _('New')) == _('New'):
                vals['revision_number'] = self.env['ir.sequence'].next_by_code('garment.tna.revision') or _('New')
        return super().create(vals_list)

    def action_approve(self):
        """Applies the New Timeline to the TNA — "Critical changes require
        approval" (SRS section 37) — and, if the TNA had already reached
        Completed/Closed, reopens it to Monitoring so the revised schedule
        is actively tracked again."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only a Draft revision can be approved.'))
            rec.tna_id.with_context(tna_revision_apply=True).write({'shipment_date': rec.new_shipment_date})
            if rec.tna_id.status in ('completed', 'closed'):
                rec.tna_id.write({'status': 'monitoring'})
            rec.write({'state': 'approved', 'approved_by_id': self.env.user.id, 'date': fields.Datetime.now()})
            rec.tna_id.message_post(body=_(
                'TNA Revision %s applied: Shipment Date changed from %s to %s. Reason: %s.') % (
                rec.revision_number, rec.previous_shipment_date, rec.new_shipment_date,
                dict(rec._fields['change_reason'].selection).get(rec.change_reason)))

    def action_reject(self):
        self.write({'state': 'rejected', 'approved_by_id': self.env.user.id, 'date': fields.Datetime.now()})
