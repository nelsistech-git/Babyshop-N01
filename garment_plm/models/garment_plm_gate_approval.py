# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
PLM Gate Approval (SRS sections 18, 46) — garment.plm.gate.approval.

Sign-off per role required to pass a PLM stage gate:
Designer -> Merchandiser -> Buyer -> Technical -> Production
(mirrors SRS section 18/46's 6-level Product Approval Workflow, applied at
the stage-gate level).
"""
from odoo import api, fields, models, _


class GarmentPlmGateApproval(models.Model):
    _name = 'garment.plm.gate.approval'
    _description = 'Garment PLM Gate Sign-Off'
    _order = 'gate_id, sequence, id'

    gate_id = fields.Many2one('garment.plm.stage.gate', string='Stage Gate', required=True, ondelete='cascade')
    project_id = fields.Many2one(related='gate_id.project_id', string='PLM Project', store=True, readonly=True)
    stage = fields.Selection(related='gate_id.stage', string='Stage', store=True, readonly=True)
    sequence = fields.Integer(string='Sequence', default=10)

    approval_level = fields.Selection([
        ('designer', 'Designer Approval'),
        ('merchandising', 'Merchandising Approval'),
        ('technical', 'Technical Approval'),
        ('quality', 'Quality Approval'),
        ('buyer', 'Buyer Approval'),
        ('production', 'Production Approval'),
    ], string='Approval Level', required=True)

    approver_id = fields.Many2one('res.users', string='Approver', tracking=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending', tracking=True)
    approval_date = fields.Datetime(string='Decision Date', copy=False)
    comments = fields.Text(string='Comments')

    def action_approve(self):
        self.write({'status': 'approved', 'approval_date': fields.Datetime.now(),
                    'approver_id': self.env.user.id})

    def action_reject(self):
        self.write({'status': 'rejected', 'approval_date': fields.Datetime.now(),
                    'approver_id': self.env.user.id})
