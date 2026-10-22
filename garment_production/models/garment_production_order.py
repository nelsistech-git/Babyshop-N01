# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentProductionOrder(models.Model):
    """Production Order (Manufacturing Order) — created after planning
    approval; the central document linking BOM, routing, work centers and
    every shop-floor department. See Production Management SRS s.12,
    Planning & MES SRS s.13, MES SRS s.6-7/14, Shop Floor SRS s.11."""
    _name = 'garment.production.order'
    _description = 'Garment Production Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Production Order Number', copy=False, readonly=True, default=lambda s: _('New'))

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    order_id = fields.Many2one('garment.order', string='Sales/Production Order')
    order_confirmation_id = fields.Many2one('garment.merch.order.confirmation', string='Order Confirmation')
    handover_id = fields.Many2one('garment.merch.handover', string='Merchandising Handover')
    plan_id = fields.Many2one('garment.production.plan', string='Production Plan')
    tna_id = fields.Many2one('garment.tna', string='TNA')

    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    bom_id = fields.Many2one('garment.bom', string='BOM')
    routing_id = fields.Many2one('garment.operation.routing', string='Routing',
                                  domain="[('style_id', '=', style_id)]")
    production_line_id = fields.Many2one('garment.production.line', string='Production Line', tracking=True)

    quantity = fields.Float(string='Order Quantity (PCS)', required=True, tracking=True)
    uom = fields.Char(string='UoM', default='PCS')
    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date')
    deadline = fields.Date(string='Delivery Deadline', tracking=True)
    priority = fields.Selection([
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent'),
    ], string='Priority', default='normal', tracking=True)

    status = fields.Selection([
        ('draft', 'Draft'), ('planned', 'Planned'), ('released', 'Released'),
        ('material_check', 'Material Availability Check'), ('running', 'Running'),
        ('hold', 'Hold'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')
    progress_stage = fields.Selection([
        ('not_started', 'Not Started'), ('running', 'Running'), ('delayed', 'Delayed'), ('completed', 'Completed'),
    ], string='Progress Stage', compute='_compute_progress_stage', store=True)

    # Department-wise real-time progress (SRS s.17 Production Progress Tracking)
    cutting_qty = fields.Float(string='Cutting Output (PCS)', compute='_compute_department_progress', store=True)
    sewing_qty = fields.Float(string='Sewing Output (PCS)', compute='_compute_department_progress', store=True)
    washing_qty = fields.Float(string='Washing Output (PCS)', compute='_compute_department_progress', store=True)
    finishing_qty = fields.Float(string='Finishing Output (PCS)', compute='_compute_department_progress', store=True)
    packing_qty = fields.Float(string='Packing Output (PCS)', compute='_compute_department_progress', store=True)
    cutting_pct = fields.Float(string='Cutting %', compute='_compute_department_progress', store=True)
    sewing_pct = fields.Float(string='Sewing %', compute='_compute_department_progress', store=True)
    washing_pct = fields.Float(string='Washing %', compute='_compute_department_progress', store=True)
    finishing_pct = fields.Float(string='Finishing %', compute='_compute_department_progress', store=True)
    packing_pct = fields.Float(string='Packing %', compute='_compute_department_progress', store=True)

    # Relations
    work_order_ids = fields.One2many('garment.work.order', 'production_order_id', string='Work Orders')
    material_issue_ids = fields.One2many('garment.production.material.issue', 'production_order_id',
                                          string='Material Issues')
    consumption_ids = fields.One2many('garment.production.consumption', 'production_order_id',
                                       string='Material Consumption')
    cutting_order_ids = fields.One2many('garment.cutting.order', 'production_order_id', string='Cutting Orders')
    entry_ids = fields.One2many('garment.production.entry', 'production_order_id', string='Production Entries')
    washing_order_ids = fields.One2many('garment.washing.order', 'production_order_id', string='Washing Orders')
    finishing_order_ids = fields.One2many('garment.finishing.order', 'production_order_id', string='Finishing Orders')
    packing_order_ids = fields.One2many('garment.packing.order', 'production_order_id', string='Packing Orders')
    issue_ids = fields.One2many('garment.production.issue', 'production_order_id', string='Issues / Delays')
    rework_ids = fields.One2many('garment.production.rework', 'production_order_id', string='Rework')
    wip_ids = fields.One2many('garment.wip.tracking', 'production_order_id', string='WIP Tracking')
    cost_ids = fields.One2many('garment.production.cost', 'production_order_id', string='Cost Records')
    approval_ids = fields.One2many('garment.production.approval', 'production_order_id', string='Approvals')

    work_order_count = fields.Integer(compute='_compute_counts')
    issue_count = fields.Integer(compute='_compute_counts')
    entry_count = fields.Integer(compute='_compute_counts')

    # AI Optimization (SRS s.39-40 Production Management / s.38-40 Planning & MES)
    ai_predicted_completion_date = fields.Date(string='AI Predicted Completion Date', readonly=True)
    ai_delay_risk = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='AI Delay Risk', readonly=True)
    ai_insight = fields.Text(string='AI Insight', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Production Order Number must be unique per company!'),
    ]

    @api.depends('entry_ids.output_qty', 'entry_ids.department', 'quantity')
    def _compute_department_progress(self):
        for rec in self:
            totals = {'cutting': 0.0, 'sewing': 0.0, 'washing': 0.0, 'finishing': 0.0, 'packing': 0.0}
            for entry in rec.entry_ids:
                if entry.department in totals:
                    totals[entry.department] += entry.output_qty
            rec.cutting_qty = totals['cutting']
            rec.sewing_qty = totals['sewing']
            rec.washing_qty = totals['washing']
            rec.finishing_qty = totals['finishing']
            rec.packing_qty = totals['packing']
            qty = rec.quantity or 1.0
            rec.cutting_pct = min(100.0, totals['cutting'] / qty * 100.0)
            rec.sewing_pct = min(100.0, totals['sewing'] / qty * 100.0)
            rec.washing_pct = min(100.0, totals['washing'] / qty * 100.0)
            rec.finishing_pct = min(100.0, totals['finishing'] / qty * 100.0)
            rec.packing_pct = min(100.0, totals['packing'] / qty * 100.0)

    @api.depends('status', 'packing_pct', 'deadline')
    def _compute_progress_stage(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.status in ('draft', 'planned'):
                rec.progress_stage = 'not_started'
            elif rec.status == 'completed' or rec.packing_pct >= 100.0:
                rec.progress_stage = 'completed'
            elif rec.deadline and rec.deadline < today and rec.packing_pct < 100.0:
                rec.progress_stage = 'delayed'
            else:
                rec.progress_stage = 'running'

    def _compute_counts(self):
        for rec in self:
            rec.work_order_count = len(rec.work_order_ids)
            rec.issue_count = len(rec.issue_ids)
            rec.entry_count = len(rec.entry_ids)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.production.order') or _('New')
        return super().create(vals_list)

    def action_release(self):
        self.write({'status': 'released'})

    def action_start(self):
        self.write({'status': 'running', 'start_date': self.start_date or fields.Date.context_today(self)})

    def action_hold(self):
        self.write({'status': 'hold'})

    def action_complete(self):
        self.write({'status': 'completed', 'end_date': fields.Date.context_today(self)})

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_view_work_orders(self):
        self.ensure_one()
        return {
            'name': _('Work Orders'), 'type': 'ir.actions.act_window', 'res_model': 'garment.work.order',
            'view_mode': 'tree,form', 'domain': [('production_order_id', '=', self.id)],
            'context': {'default_production_order_id': self.id},
        }

    def action_view_issues(self):
        self.ensure_one()
        return {
            'name': _('Issues / Delays'), 'type': 'ir.actions.act_window', 'res_model': 'garment.production.issue',
            'view_mode': 'tree,form', 'domain': [('production_order_id', '=', self.id)],
            'context': {'default_production_order_id': self.id},
        }

    def action_view_entries(self):
        self.ensure_one()
        return {
            'name': _('Production Entries'), 'type': 'ir.actions.act_window', 'res_model': 'garment.production.entry',
            'view_mode': 'tree,form', 'domain': [('production_order_id', '=', self.id)],
            'context': {'default_production_order_id': self.id},
        }

    def action_run_ai_forecast(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            completion_date, risk, insight = ai_engine.predict_production_completion(rec)
            rec.write({'ai_predicted_completion_date': completion_date, 'ai_delay_risk': risk,
                       'ai_insight': insight, 'ai_last_run': fields.Datetime.now()})
