# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class FwReworkOrder(models.Model):
    _name = 'fw.rework.order'
    _description = 'Footwear Rework / Repair Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Rework Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.rework.order') or 'New')
    source = fields.Selection([
        ('inline_qc', 'Inline QC'),
        ('aql_inspection', 'AQL Inspection'),
        ('other', 'Other'),
    ], string='Defect Source', required=True, default='inline_qc')
    inline_qc_id = fields.Many2one('fw.inline.qc', string='Source Inline QC')
    aql_inspection_id = fields.Many2one('fw.aql.inspection', string='Source AQL Inspection')

    production_order_id = fields.Many2one('fw.production.order', string='Production Order',
                                           required=True, tracking=True)
    style_id = fields.Many2one(related='production_order_id.style_id', string='Style',
                                store=True)

    defect_line_ids = fields.One2many('fw.rework.defect.line', 'rework_id',
                                       string='Defects to Rework')
    total_rework_qty = fields.Integer(string='Total Qty to Rework',
                                       compute='_compute_totals', store=True)

    assigned_to = fields.Many2one('hr.employee', string='Assigned Technician/Team')
    rework_start_date = fields.Date(string='Rework Start Date')
    rework_end_date = fields.Date(string='Rework End Date')

    reinspection_result = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Re-Inspection Result', default='pending', tracking=True)
    reinspection_notes = fields.Text(string='Re-Inspection Notes')

    scrapped_qty = fields.Integer(string='Scrapped Qty (Unrepairable)', default=0)
    reworked_qty = fields.Integer(string='Successfully Reworked Qty',
                                   compute='_compute_totals', store=True)

    @api.constrains('scrapped_qty')
    def _check_scrapped_qty_non_negative(self):
        for rec in self:
            if rec.scrapped_qty < 0:
                raise ValidationError("Scrapped Qty cannot be negative.")

    followup_rework_id = fields.Many2one('fw.rework.order', string='Follow-Up Rework Order',
                                          readonly=True, copy=False,
                                          help="If re-inspection failed, a new Rework Order "
                                               "can be created for another repair cycle.")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('reinspection', 'Awaiting Re-Inspection'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('fw.rework.order') or 'New'
        return super().create(vals_list)

    @api.depends('defect_line_ids.qty', 'scrapped_qty')
    def _compute_totals(self):
        for rec in self:
            rec.total_rework_qty = sum(rec.defect_line_ids.mapped('qty'))
            rec.reworked_qty = max(rec.total_rework_qty - (rec.scrapped_qty or 0), 0)

    @api.onchange('inline_qc_id')
    def _onchange_inline_qc_id(self):
        if self.inline_qc_id:
            self.production_order_id = self.inline_qc_id.production_order_id
            self.defect_line_ids = [(0, 0, {
                'defect_code_id': line.defect_code_id.id,
                'qty': line.qty,
            }) for line in self.inline_qc_id.defect_line_ids]

    @api.onchange('aql_inspection_id')
    def _onchange_aql_inspection_id(self):
        if self.aql_inspection_id:
            if self.aql_inspection_id.production_order_id:
                self.production_order_id = self.aql_inspection_id.production_order_id
            self.defect_line_ids = [(0, 0, {
                'defect_code_id': line.defect_code_id.id,
                'qty': line.qty,
            }) for line in self.aql_inspection_id.defect_line_ids]

    def action_start(self):
        for rec in self:
            if not rec.defect_line_ids:
                raise UserError("Please add at least one defect line before starting rework.")
        self.write({'state': 'in_progress'})

    def action_send_reinspection(self):
        self.write({'state': 'reinspection', 'reinspection_result': 'pending'})

    def action_reinspection_pass(self):
        self.write({'reinspection_result': 'pass', 'state': 'closed'})

    def action_reinspection_fail(self):
        self.write({'reinspection_result': 'fail'})

    def action_create_followup_rework(self):
        self.ensure_one()
        if self.followup_rework_id:
            raise UserError("A follow-up Rework Order already exists for this order.")
        followup = self.create({
            'source': self.source,
            'inline_qc_id': self.inline_qc_id.id,
            'aql_inspection_id': self.aql_inspection_id.id,
            'production_order_id': self.production_order_id.id,
            'assigned_to': self.assigned_to.id,
            'defect_line_ids': [(0, 0, {
                'defect_code_id': line.defect_code_id.id,
                'qty': line.qty,
            }) for line in self.defect_line_ids],
        })
        self.write({'followup_rework_id': followup.id, 'state': 'closed'})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Follow-Up Rework Order',
            'res_model': 'fw.rework.order',
            'view_mode': 'form',
            'res_id': followup.id,
        }

    def action_reset_draft(self):
        self.write({'state': 'draft', 'reinspection_result': 'pending'})


class FwReworkDefectLine(models.Model):
    _name = 'fw.rework.defect.line'
    _description = 'Rework Order Defect Line'
    _order = 'id'

    rework_id = fields.Many2one('fw.rework.order', string='Rework Order', required=True,
                                 ondelete='cascade')
    defect_code_id = fields.Many2one('fw.defect.code', string='Defect Code', required=True)
    qty = fields.Integer(string='Qty', required=True, default=1)
    remarks = fields.Char(string='Remarks')

    @api.constrains('qty')
    def _check_qty_non_negative(self):
        for rec in self:
            if rec.qty < 0:
                raise ValidationError("Defect Qty cannot be negative.")
