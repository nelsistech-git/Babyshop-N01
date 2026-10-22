# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentBomApproval(models.Model):
    """BOM Approval Workflow (SRS section 17) — garment.bom.approval."""
    _name = 'garment.bom.approval'
    _description = 'Garment BOM Approval'
    _order = 'sequence'

    bom_id = fields.Many2one('garment.bom', string='BOM', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    approval_stage = fields.Selection([
        ('merchandiser_review', 'Merchandiser Review'), ('technical_team', 'Technical Team'),
        ('costing_team', 'Costing Team'), ('purchase_team', 'Purchase Team'),
        ('production_team', 'Production Team'), ('final_approval', 'Final Approval'),
    ], string='Approval Stage', required=True)
    approver_id = fields.Many2one('res.users', string='Approver')
    status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    approval_date = fields.Datetime(string='Approval Date')
    comments = fields.Text(string='Comments')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            # Notification System (SRS 45): "BOM approval pending" alert.
            rec.bom_id.message_post(
                body=_('BOM approval pending: %s.') % dict(rec._fields['approval_stage'].selection).get(rec.approval_stage))
            if rec.approver_id:
                rec.bom_id.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=rec.approver_id.id,
                    summary=_('BOM Approval: %s') % dict(rec._fields['approval_stage'].selection).get(rec.approval_stage),
                    note=_('BOM "%s" is waiting for your approval at stage "%s".') % (
                        rec.bom_id.bom_number, dict(rec._fields['approval_stage'].selection).get(rec.approval_stage)))
        return records

    def action_approve(self):
        self.write({'status': 'approved', 'approval_date': fields.Datetime.now(), 'approver_id': self.env.user.id})

    def action_reject(self):
        self.write({'status': 'rejected', 'approval_date': fields.Datetime.now(), 'approver_id': self.env.user.id})
