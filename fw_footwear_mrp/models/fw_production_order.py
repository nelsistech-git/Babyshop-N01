# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

STAGE_SEQUENCE = ['cutting', 'stitching', 'assembly', 'finishing']
STAGE_LABELS = {
    'cutting': 'Cutting',
    'stitching': 'Stitching / Upper',
    'assembly': 'Assembly / Lasting',
    'finishing': 'Finishing / Packing',
}


class FwProductionOrder(models.Model):
    _name = 'fw.production.order'
    _description = 'Footwear Production Order (Stage-wise Execution)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Production Order Ref.', required=True, copy=False,
                        default=lambda self: self.env['ir.sequence'].next_by_code(
                            'fw.production.order') or 'New')
    buyer_order_line_id = fields.Many2one('fw.buyer.order.line', string='Buyer Order Line',
                                           required=True, tracking=True)
    buyer_order_id = fields.Many2one(related='buyer_order_line_id.order_id',
                                      string='Buyer Order', store=True)
    style_id = fields.Many2one(related='buyer_order_line_id.style_id', string='Style',
                                store=True)
    color_id = fields.Many2one(related='buyer_order_line_id.color_id', string='Color',
                                store=True)

    bom_id = fields.Many2one('fw.bom.version', string='BOM Version',
                              domain="[('style_id', '=', style_id), ('state', '=', 'confirmed')]")
    factory_id = fields.Many2one('fw.factory', string='Factory', required=True, tracking=True)
    production_line_id = fields.Many2one('fw.production.line', string='Production Line',
                                          domain="[('factory_id', '=', factory_id)]",
                                          tracking=True)

    planned_qty = fields.Integer(string='Planned Qty (Pairs)', required=True, default=0)
    date_planned_start = fields.Date(string='Planned Start')
    date_planned_finish = fields.Date(string='Planned Finish')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('released', 'Released to Floor'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    stage_ids = fields.One2many('fw.production.stage.line', 'production_order_id',
                                 string='Process Stages')
    finished_qty = fields.Integer(string='Finished Qty (Pairs)', compute='_compute_finished_qty',
                                   store=True)
    completion_percent = fields.Float(string='Completion %', compute='_compute_finished_qty',
                                       store=True)

    mrp_production_id = fields.Many2one('mrp.production', string='Manufacturing Order',
                                         readonly=True, copy=False)

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.constrains('planned_qty')
    def _check_planned_qty_non_negative(self):
        for rec in self:
            if rec.planned_qty < 0:
                raise ValidationError("Planned quantity cannot be negative.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'fw.production.order') or 'New'
        return super().create(vals_list)

    @api.onchange('buyer_order_line_id')
    def _onchange_buyer_order_line_id(self):
        if self.buyer_order_line_id:
            self.planned_qty = self.buyer_order_line_id.total_qty
            if self.buyer_order_line_id.order_id.factory_id:
                self.factory_id = self.buyer_order_line_id.order_id.factory_id

    @api.depends('stage_ids.completed_qty', 'planned_qty')
    def _compute_finished_qty(self):
        for rec in self:
            finishing_stage = rec.stage_ids.filtered(lambda s: s.stage == 'finishing')
            rec.finished_qty = sum(finishing_stage.mapped('completed_qty'))
            rec.completion_percent = (rec.finished_qty / rec.planned_qty * 100.0) \
                if rec.planned_qty else 0.0

    def action_release(self):
        for rec in self:
            if not rec.stage_ids:
                stage_vals = []
                for idx, stage in enumerate(STAGE_SEQUENCE):
                    stage_vals.append((0, 0, {
                        'stage': stage,
                        'sequence': (idx + 1) * 10,
                        'planned_qty': rec.planned_qty,
                        'production_line_id': rec.production_line_id.id,
                    }))
                rec.stage_ids = stage_vals
        self.write({'state': 'released'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        for rec in self:
            if rec.finished_qty < rec.planned_qty:
                raise UserError(
                    "Finished quantity (%d) is less than planned quantity (%d). "
                    "Complete the Finishing stage first, or cancel remaining balance."
                    % (rec.finished_qty, rec.planned_qty))
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_create_mrp_production(self):
        self.ensure_one()
        if self.mrp_production_id:
            raise UserError("A Manufacturing Order is already linked to this production order.")
        if not self.style_id.product_tmpl_id:
            raise UserError(
                "The style '%s' has no linked Product. Please set a Product on the Style "
                "master before creating a Manufacturing Order." % self.style_id.name)
        product = self.style_id.product_tmpl_id.product_variant_id
        mo_vals = {
            'product_id': product.id,
            'product_qty': self.planned_qty,
            'product_uom_id': product.uom_id.id,
            'fw_style_id': self.style_id.id,
            'fw_buyer_order_id': self.buyer_order_id.id,
            'fw_factory_id': self.factory_id.id,
            'fw_production_line_id': self.production_line_id.id,
            'fw_production_order_id': self.id,
            'date_planned_start': self.date_planned_start,
            'date_planned_finished': self.date_planned_finish,
        }
        mrp_production = self.env['mrp.production'].create(mo_vals)
        self.mrp_production_id = mrp_production.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Manufacturing Order',
            'res_model': 'mrp.production',
            'view_mode': 'form',
            'res_id': mrp_production.id,
        }


class FwProductionStageLine(models.Model):
    _name = 'fw.production.stage.line'
    _description = 'Footwear Production Stage Line'
    _order = 'production_order_id, sequence'

    production_order_id = fields.Many2one('fw.production.order', string='Production Order',
                                           required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    stage = fields.Selection([
        ('cutting', 'Cutting'),
        ('stitching', 'Stitching / Upper'),
        ('assembly', 'Assembly / Lasting'),
        ('finishing', 'Finishing / Packing'),
    ], string='Process Stage', required=True)
    production_line_id = fields.Many2one('fw.production.line', string='Production Line')
    planned_qty = fields.Integer(string='Planned Qty', default=0)
    completed_qty = fields.Integer(string='Completed Qty', compute='_compute_completed_qty',
                                    store=True)
    defect_qty = fields.Integer(string='Defect Qty', compute='_compute_completed_qty',
                                 store=True)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], string='Status', default='pending')

    output_ids = fields.One2many('fw.production.daily.output', 'stage_line_id',
                                  string='Daily Output Entries')

    @api.constrains('planned_qty')
    def _check_planned_qty_non_negative(self):
        for rec in self:
            if rec.planned_qty < 0:
                raise ValidationError("Stage planned quantity cannot be negative.")

    @api.depends('output_ids.qty_produced', 'output_ids.defect_qty')
    def _compute_completed_qty(self):
        for rec in self:
            rec.completed_qty = sum(rec.output_ids.mapped('qty_produced'))
            rec.defect_qty = sum(rec.output_ids.mapped('defect_qty'))

    def action_start(self):
        self.write({'status': 'in_progress', 'start_date': fields.Date.context_today(self)})

    def action_done(self):
        self.write({'status': 'done', 'end_date': fields.Date.context_today(self)})
