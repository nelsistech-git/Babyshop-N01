# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentSupplierCapa(models.Model):
    """Supplier Corrective Action Management / CAPA (SRS section 28) —
    garment.supplier.capa."""
    _name = 'garment.supplier.capa'
    _description = 'Garment Supplier Corrective Action'
    _inherit = ['mail.thread']
    _order = 'due_date'

    supplier_id = fields.Many2one('garment.supplier', string='Supplier', required=True, ondelete='cascade')
    audit_id = fields.Many2one('garment.supplier.audit', string='Related Audit')
    issue = fields.Text(string='Issue', required=True)
    root_cause = fields.Text(string='Root Cause')
    corrective_action = fields.Text(string='Corrective Action')
    responsible_person_id = fields.Many2one('res.users', string='Responsible Person')
    due_date = fields.Date(string='Due Date')
    completion_status = fields.Selection([
        ('open', 'Open'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('overdue', 'Overdue'),
    ], string='Completion Status', default='open', tracking=True)

    def action_mark_completed(self):
        self.write({'completion_status': 'completed'})
