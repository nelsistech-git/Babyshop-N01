# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentProductionIssue(models.Model):
    """Unified Production Issue / Delay / Andon Alert record. Merges
    'Production Delay Management' (Production Management SRS s.18, Planning
    & MES SRS s.48, MES SRS s.18), 'Production Alert / Andon System'
    (Production Management SRS s.19, MES SRS s.19/40, Shop Floor SRS s.42)
    and 'Production Issue Management' (Shop Floor SRS s.29) into a single
    floor-to-management ticket."""
    _name = 'garment.production.issue'
    _description = 'Garment Production Issue / Delay'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reported_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', copy=False, readonly=True, default=lambda s: _('New'))
    production_order_id = fields.Many2one('garment.production.order', string='Production Order', tracking=True)
    line_id = fields.Many2one('garment.production.line', string='Production Line')
    machine_id = fields.Many2one('garment.production.machine', string='Machine')

    issue_type = fields.Selection([
        ('material_shortage', 'Material Shortage'), ('machine_breakdown', 'Machine Breakdown'),
        ('worker_shortage', 'Worker / Manpower Shortage'), ('quality_issue', 'Quality Issue'),
        ('planning_issue', 'Planning Issue'), ('power_problem', 'Power Problem'),
        ('low_output', 'Low Production Output'), ('low_efficiency', 'Line Efficiency Drop'),
        ('deadline_risk', 'Deadline / Delay Risk'), ('other', 'Other'),
    ], string='Issue Type', required=True, tracking=True)
    andon_status = fields.Selection([
        ('green', 'Running'), ('yellow', 'Warning'), ('red', 'Problem'),
    ], string='Andon Signal', default='yellow', tracking=True)

    reported_date = fields.Datetime(string='Reported On', default=fields.Datetime.now)
    reported_by_id = fields.Many2one('res.users', string='Reported By', default=lambda s: s.env.user)
    description = fields.Text(string='Description')

    impact_qty = fields.Float(string='Impact (PCS Lost)')
    delay_days = fields.Float(string='Delay (Days)')
    expected_date = fields.Date(string='Expected Date')
    actual_date = fields.Date(string='Actual/Revised Date')

    status = fields.Selection([
        ('open', 'Open'), ('in_progress', 'In Progress'), ('resolved', 'Resolved'),
    ], string='Status', default='open', tracking=True)
    resolution = fields.Text(string='Resolution / Action Taken')
    resolved_by_id = fields.Many2one('res.users', string='Resolved By')
    resolved_date = fields.Datetime(string='Resolved On')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.production.issue') or _('New')
        return super().create(vals_list)

    def action_start_progress(self):
        self.write({'status': 'in_progress'})

    def action_resolve(self):
        self.write({'status': 'resolved', 'resolved_by_id': self.env.user.id, 'resolved_date': fields.Datetime.now()})
