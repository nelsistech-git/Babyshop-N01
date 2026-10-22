# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentBuyerComplaint(models.Model):
    """Buyer Complaint Management — SRS Buyer CRM section 22, with the
    Complaint Closure approval chain from section 39 (Department
    Investigation -> CAPA Completed -> QA Verification -> Management
    Approval -> Closed)."""
    _name = 'garment.buyer.complaint'
    _description = 'Garment Buyer Complaint'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'complaint_date desc'

    complaint_number = fields.Char(string='Complaint Number', copy=False, readonly=True,
                                    default=lambda s: _('New'))
    complaint_date = fields.Date(string='Complaint Date', default=fields.Date.context_today, required=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True, ondelete='cascade')
    order_reference = fields.Char(string='Order Reference',
                                   help='Free-text reference to the Sales/Production Order '
                                        '(garment_order_management) this complaint relates to.')

    complaint_category = fields.Selection([
        ('fabric_quality', 'Fabric Quality'),
        ('sewing_quality', 'Sewing Quality'),
        ('packing', 'Packing'),
        ('label', 'Label'),
        ('measurement', 'Measurement'),
        ('shade_variation', 'Shade Variation'),
        ('delay', 'Delay'),
        ('documentation', 'Documentation'),
        ('shipment', 'Shipment'),
        ('communication', 'Communication'),
        ('invoice', 'Invoice'),
        ('payment', 'Payment'),
        ('compliance', 'Compliance'),
    ], string='Complaint Category', required=True, tracking=True)

    description = fields.Text(string='Description')
    root_cause = fields.Text(string='Root Cause')
    assigned_department = fields.Selection([
        ('merchandising', 'Merchandising'),
        ('production', 'Production'),
        ('quality', 'Quality'),
        ('commercial', 'Commercial'),
        ('accounts', 'Accounts'),
        ('logistics', 'Logistics'),
        ('compliance', 'Compliance'),
    ], string='Assigned Department')
    responsible_user_id = fields.Many2one('res.users', string='Responsible Person')
    corrective_action = fields.Text(string='Corrective Action')
    preventive_action = fields.Text(string='Preventive Action (CAPA)')
    target_resolution_date = fields.Date(string='Target Resolution Date')
    actual_resolution_date = fields.Date(string='Actual Resolution Date')
    buyer_feedback = fields.Text(string='Buyer Feedback')

    closure_approved_by_id = fields.Many2one('res.users', string='Closure Approved By', readonly=True)
    closure_approval_date = fields.Date(string='Closure Approval Date', readonly=True)

    state = fields.Selection([
        ('logged', 'Complaint Logged'),
        ('investigation', 'Department Investigation'),
        ('capa_completed', 'CAPA Completed'),
        ('qa_verification', 'QA Verification'),
        ('management_approval', 'Management Approval'),
        ('closed', 'Closed'),
    ], string='Status', default='logged', tracking=True, group_expand='_expand_states')

    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Critical'),
    ], string='Priority', default='1')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['state'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('complaint_number', _('New')) == _('New'):
                vals['complaint_number'] = self.env['ir.sequence'].next_by_code('garment.buyer.complaint') or _('New')
        return super().create(vals_list)

    def action_start_investigation(self):
        self.write({'state': 'investigation'})

    def action_capa_complete(self):
        self.write({'state': 'capa_completed'})

    def action_qa_verify(self):
        self.write({'state': 'qa_verification'})

    def action_send_for_management_approval(self):
        self.write({'state': 'management_approval'})

    def action_close(self):
        for rec in self:
            rec.write({
                'state': 'closed',
                'closure_approved_by_id': self.env.user.id,
                'closure_approval_date': fields.Date.context_today(rec),
                'actual_resolution_date': rec.actual_resolution_date or fields.Date.context_today(rec),
            })
