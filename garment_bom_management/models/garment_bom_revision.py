# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# BOM Approval Matrix (SRS section 39): a fabric/material change is a
# "Major Change" needing Technical Manager + QA Manager + Buyer sign-off;
# everything else is a "Minor Change" needing only Merchandiser approval.
MAJOR_CHANGE_REASONS = {'material_availability', 'quality_improvement'}


class GarmentBomRevision(models.Model):
    """BOM Change/Revision Management (SRS section 17-18) —
    garment.bom.revision. Revision history cannot be deleted (SRS section
    34 Record Rules)."""
    _name = 'garment.bom.revision'
    _description = 'Garment BOM Revision'
    _inherit = ['mail.thread']
    _order = 'revision_number desc'

    bom_id = fields.Many2one('garment.bom', string='BOM', required=True, ondelete='cascade')
    revision_number = fields.Integer(string='Revision Number', required=True, default=1)
    old_material = fields.Char(string='Old Material')
    new_material = fields.Char(string='New Material')
    change_reason_category = fields.Selection([
        ('cost_reduction', 'Cost Reduction'), ('supplier_change', 'Supplier Change'),
        ('buyer_request', 'Buyer Request'), ('material_availability', 'Material Availability'),
        ('quality_improvement', 'Quality Improvement'), ('production_issue', 'Production Issue'),
    ], string='Change Reason')
    change_reason = fields.Text(string='Change Reason Details')
    change_severity = fields.Selection([
        ('minor', 'Minor Change'), ('major', 'Major Change'),
    ], string='Change Severity', default='minor', tracking=True,
        help='Major changes (e.g. fabric change / material availability / quality driven) require the full '
             'Technical Manager → QA Manager → Buyer approval chain (SRS BOM Approval Matrix).')
    changed_by_id = fields.Many2one('res.users', string='Changed By', default=lambda s: s.env.user)
    changed_date = fields.Datetime(string='Changed Date', default=fields.Datetime.now)
    cost_impact = fields.Monetary(string='Cost Impact', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='bom_id.currency_id', store=True)
    effective_date = fields.Date(string='Effective Date')
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft', tracking=True)

    # BOM Approval Matrix — major change checkpoints (SRS section 39)
    technical_manager_approved = fields.Boolean(string='Technical Manager Approved')
    qa_manager_approved = fields.Boolean(string='QA Manager Approved')
    buyer_approved = fields.Boolean(string='Buyer Approved')

    @api.onchange('change_reason_category')
    def _onchange_change_reason_category(self):
        for rec in self:
            rec.change_severity = 'major' if rec.change_reason_category in MAJOR_CHANGE_REASONS else 'minor'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'change_severity' not in vals and vals.get('change_reason_category') in MAJOR_CHANGE_REASONS:
                vals['change_severity'] = 'major'
        records = super().create(vals_list)
        for rec in records:
            rec.bom_id.write({'revision_number': rec.revision_number})
            rec.bom_id.message_post(
                body=_('BOM revision #%s: %s → %s (%s)') % (
                    rec.revision_number, rec.old_material or '-', rec.new_material or '-',
                    rec.change_reason or '-'))
        return records

    def action_approve(self):
        for rec in self:
            if rec.change_severity == 'major' and not (
                    rec.technical_manager_approved and rec.qa_manager_approved and rec.buyer_approved):
                raise UserError(_('Major change: Technical Manager, QA Manager and Buyer must all approve '
                                   'before this revision can be approved.'))
            rec.write({'approval_status': 'approved'})
            rec.bom_id.write({'is_locked': True})

    def unlink(self):
        raise UserError(_('BOM Revision history cannot be deleted (SRS Record Rules). Archive the BOM instead.'))
