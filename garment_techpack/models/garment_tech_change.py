# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentTechChange(models.Model):
    """Tech Change Request (SRS section 18 revision workflow) — garment.tech.change."""
    _name = 'garment.tech.change'
    _description = 'Garment Tech Pack Change Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'change_number desc'

    change_number = fields.Char(string='Change Number', copy=False, readonly=True, default=lambda s: _('New'))
    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    requested_by_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user)
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today)
    change_reason = fields.Text(string='Change Reason')
    revision_type = fields.Selection([
        ('minor', 'Minor Revision'), ('major', 'Major Revision'),
    ], string='Revision Type', required=True, default='minor')
    impact_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='Impact Level', default='low', tracking=True,
        help='Set during the Impact Analysis stage of the Revision Workflow (SRS section 18).')
    buyer_reference = fields.Char(string='Buyer Reference')
    revision_deadline = fields.Date(string='Revision Deadline', tracking=True)

    state = fields.Selection([
        ('requested', 'Revision Requested'), ('technical_review', 'Technical Review'),
        ('impact_analysis', 'Impact Analysis'), ('department_review', 'Department Review'),
        ('approved', 'Approval'), ('released', 'New Version Released'),
    ], string='Status', default='requested', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('change_number', _('New')) == _('New'):
                vals['change_number'] = self.env['ir.sequence'].next_by_code('garment.tech.change') or _('New')
        return super().create(vals_list)

    def action_next_stage(self):
        flow = ['requested', 'technical_review', 'impact_analysis', 'department_review', 'approved', 'released']
        for rec in self:
            idx = flow.index(rec.state)
            if idx < len(flow) - 1:
                rec.state = flow[idx + 1]
            if rec.state == 'released':
                try:
                    current = float(rec.techpack_id.version or '1.0')
                except ValueError:
                    current = 1.0
                next_version = current + (1.0 if rec.revision_type == 'major' else 0.1)
                self.env['garment.techpack.version'].create({
                    'techpack_id': rec.techpack_id.id,
                    'version_number': '%.1f' % next_version,
                    'change_reason': rec.change_reason,
                    'revision_type': rec.revision_type,
                    'impact_level': rec.impact_level,
                    'buyer_reference': rec.buyer_reference,
                })
