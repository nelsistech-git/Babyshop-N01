# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentECR(models.Model):
    """Engineering Change Request (SRS section 24) — garment.ecr."""
    _name = 'garment.ecr'
    _description = 'Garment Engineering Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'ecr_number desc'

    ecr_number = fields.Char(string='ECR Number', copy=False, readonly=True, default=lambda s: _('New'))
    style_id = fields.Many2one('garment.style', string='Style', required=True, ondelete='cascade')
    requested_by_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user)
    department = fields.Char(string='Department')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1')
    change_category = fields.Selection([
        ('design', 'Design'), ('measurement', 'Measurement'), ('fabric', 'Fabric'), ('trim', 'Trim'),
        ('pattern', 'Pattern'), ('packaging', 'Packaging'), ('artwork', 'Artwork'), ('label', 'Label'),
        ('technical_spec', 'Technical Specification'), ('compliance', 'Compliance'),
    ], string='Change Category', required=True)
    description = fields.Text(string='Description')
    business_reason = fields.Text(string='Business Reason')
    impact_analysis = fields.Text(string='Impact Analysis')

    state = fields.Selection([
        ('draft', 'Draft'), ('technical_review', 'Technical Review'), ('merchandising_review', 'Merchandising Review'),
        ('qa_review', 'QA Review'), ('approval', 'Approval'), ('implemented', 'Implemented'), ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ecr_number', _('New')) == _('New'):
                vals['ecr_number'] = self.env['ir.sequence'].next_by_code('garment.ecr') or _('New')
        return super().create(vals_list)

    def action_next_stage(self):
        flow = ['draft', 'technical_review', 'merchandising_review', 'qa_review', 'approval', 'implemented', 'closed']
        for rec in self:
            idx = flow.index(rec.state)
            if idx < len(flow) - 1:
                rec.state = flow[idx + 1]
