# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Maintenance Work Order — the central CMMS document. Consolidates
Breakdown Maintenance (Maintenance & Asset Mgmt SRS sec. 15-19, CMMS SRS
sec. 15-17), Preventive Maintenance execution (both SRS, sec. 13/14 &
11/14), Calibration jobs and the Maintenance / Spare / Repair Approval
Workflows (Maintenance & Asset Mgmt SRS sec. 45, CMMS SRS sec. 27 & 30)
into ONE work order model with a ``wo_type`` discriminator, the same way
garment_quality unified every inspection stage into one
``garment.quality.inspection`` model.

Downtime integration: this model does NOT re-model machine downtime.
A breakdown Work Order links to the SAME ``garment.machine.downtime``
record already created on the shop floor (garment_production) via
``downtime_id``; completing the Work Order is what resolves that
downtime event (calls its own ``action_resolve()``) and returns the
machine to Running status. See IMPLEMENTATION_NOTES.md.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError

PRIORITY_RESPONSE_HOURS = {
    'critical': 0.5,   # Immediate
    'high': 8.0,        # Same Day
    'medium': 48.0,      # Within 48 Hours
    'low': 168.0,        # Planned (1 week)
}


class GarmentMaintenanceWorkorder(models.Model):
    _name = 'garment.maintenance.workorder'
    _description = 'Garment Maintenance Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reported_date desc, id desc'

    name = fields.Char(string='Work Order No.', copy=False, readonly=True, default=lambda s: _('New'))
    wo_type = fields.Selection([
        ('breakdown', 'Breakdown'),
        ('preventive', 'Preventive'),
        ('calibration', 'Calibration'),
        ('inspection', 'Inspection'),
        ('amc', 'AMC / Contract Service'),
    ], string='Work Order Type', required=True, default='breakdown', tracking=True)

    # ------------------------------------------------------------------
    # Equipment linkage — production machines reuse garment.production.machine
    # (garment_production); non-production equipment uses garment.asset.
    # ------------------------------------------------------------------
    equipment_type = fields.Selection([
        ('machine', 'Production Machine'),
        ('asset', 'Other Asset'),
    ], string='Equipment Type', default='machine', required=True, tracking=True)
    machine_id = fields.Many2one('garment.production.machine', string='Machine', tracking=True)
    asset_id = fields.Many2one('garment.asset', string='Asset', tracking=True)
    equipment_name = fields.Char(string='Equipment', compute='_compute_equipment_name', store=True)

    downtime_id = fields.Many2one(
        'garment.machine.downtime', string='Downtime Event', tracking=True,
        domain="[('machine_id', '=', machine_id), ('status', '=', 'open')]",
        help='The shop-floor downtime record (garment_production) this Work Order resolves. '
             'Completing this Work Order closes that downtime record automatically.')
    plan_id = fields.Many2one('garment.maintenance.plan', string='PM Plan', tracking=True)
    contract_id = fields.Many2one('garment.maintenance.contract', string='AMC Contract')
    calibration_id = fields.Many2one('garment.calibration', string='Calibration Record')

    problem_description = fields.Text(string='Problem / Task Description')
    priority = fields.Selection([
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ], string='Priority', default='medium', required=True, tracking=True)
    response_due_datetime = fields.Datetime(string='Response Due By', compute='_compute_response_due', store=True)
    production_impact = fields.Text(string='Production Impact')

    reported_by_id = fields.Many2one('res.users', string='Reported By', default=lambda s: s.env.user)
    reported_date = fields.Datetime(string='Reported Date', default=fields.Datetime.now, required=True)
    engineer_id = fields.Many2one('garment.hr.employee', string='Inspecting Engineer',
                                   domain=[('is_maintenance_technician', '=', True)])
    technician_id = fields.Many2one('garment.hr.employee', string='Technician', tracking=True,
                                     domain=[('is_maintenance_technician', '=', True)])

    checklist_id = fields.Many2one('garment.maintenance.checklist', string='Checklist Template')
    checklist_line_ids = fields.One2many('garment.maintenance.workorder.checklist.line', 'workorder_id',
                                          string='Checklist Execution')
    spare_line_ids = fields.One2many('garment.maintenance.workorder.spare.line', 'workorder_id',
                                      string='Spare Parts Used')

    start_datetime = fields.Datetime(string='Repair Start')
    end_datetime = fields.Datetime(string='Repair / Test Completed')
    downtime_hours = fields.Float(string='Downtime (Hours)', compute='_compute_downtime_hours', store=True)
    production_loss_qty = fields.Float(string='Production Loss (PCS)')

    action_taken = fields.Text(string='Action Taken / Root Cause')
    test_result = fields.Selection([
        ('pending', 'Pending'),
        ('pass', 'Pass'),
        ('fail', 'Fail'),
    ], string='Testing Result', default='pending')

    # ------------------------------------------------------------------
    # Cost tracking (Maintenance & Asset Mgmt SRS sec. 31, CMMS SRS sec. 19)
    # ------------------------------------------------------------------
    labor_hours = fields.Float(string='Labor Hours')
    labor_rate = fields.Monetary(string='Labor Rate / Hour', currency_field='currency_id')
    labor_cost = fields.Monetary(string='Labor Cost', compute='_compute_costs', store=True, currency_field='currency_id')
    spare_cost = fields.Monetary(string='Spare Parts Cost', compute='_compute_costs', store=True, currency_field='currency_id')
    external_provider_id = fields.Many2one('garment.supplier', string='External Service Provider')
    external_service_cost = fields.Monetary(string='External Service Cost', currency_field='currency_id')
    total_cost = fields.Monetary(string='Total Maintenance Cost', compute='_compute_costs', store=True,
                                  currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    # ------------------------------------------------------------------
    # Approval workflow (Repair Approval — both SRS)
    # ------------------------------------------------------------------
    cost_estimate = fields.Monetary(string='Cost Estimate', currency_field='currency_id')
    approval_status = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending Manager Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='not_required', tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    approval_date = fields.Datetime(string='Approval Date')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('testing', 'Testing'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('machine_id.machine_number', 'machine_id.name', 'asset_id.name', 'asset_id.asset_code')
    def _compute_equipment_name(self):
        for rec in self:
            if rec.equipment_type == 'machine' and rec.machine_id:
                rec.equipment_name = rec.machine_id.name or rec.machine_id.machine_number
            elif rec.equipment_type == 'asset' and rec.asset_id:
                rec.equipment_name = '%s [%s]' % (rec.asset_id.name, rec.asset_id.asset_code)
            else:
                rec.equipment_name = False

    @api.depends('priority', 'reported_date')
    def _compute_response_due(self):
        for rec in self:
            if rec.reported_date:
                hours = PRIORITY_RESPONSE_HOURS.get(rec.priority, 48.0)
                rec.response_due_datetime = fields.Datetime.add(rec.reported_date, hours=hours)
            else:
                rec.response_due_datetime = False

    @api.depends('start_datetime', 'end_datetime', 'downtime_id.duration_minutes')
    def _compute_downtime_hours(self):
        for rec in self:
            if rec.downtime_id and rec.downtime_id.duration_minutes:
                rec.downtime_hours = rec.downtime_id.duration_minutes / 60.0
            elif rec.start_datetime and rec.end_datetime:
                rec.downtime_hours = (rec.end_datetime - rec.start_datetime).total_seconds() / 3600.0
            else:
                rec.downtime_hours = 0.0

    @api.depends('labor_hours', 'labor_rate', 'spare_line_ids.subtotal', 'external_service_cost')
    def _compute_costs(self):
        for rec in self:
            rec.labor_cost = (rec.labor_hours or 0.0) * (rec.labor_rate or 0.0)
            rec.spare_cost = sum(rec.spare_line_ids.mapped('subtotal'))
            rec.total_cost = rec.labor_cost + rec.spare_cost + (rec.external_service_cost or 0.0)

    @api.onchange('equipment_type')
    def _onchange_equipment_type(self):
        self.machine_id = False
        self.asset_id = False

    @api.onchange('checklist_id')
    def _onchange_checklist_id(self):
        if self.checklist_id:
            self.checklist_line_ids = [(5, 0, 0)] + [(0, 0, {
                'checklist_line_id': line.id,
                'check_item': line.check_item,
            }) for line in self.checklist_id.line_ids]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.maintenance.workorder') or _('New')
        records = super().create(vals_list)
        for rec in records:
            if rec.checklist_id and not rec.checklist_line_ids:
                rec.checklist_line_ids = [(0, 0, {
                    'checklist_line_id': line.id,
                    'check_item': line.check_item,
                }) for line in rec.checklist_id.line_ids]
        return records

    def _set_equipment_status(self, status):
        for rec in self:
            if rec.equipment_type == 'machine' and rec.machine_id:
                rec.machine_id.status = status
            elif rec.equipment_type == 'asset' and rec.asset_id:
                asset_state_map = {'breakdown': 'breakdown', 'maintenance': 'under_maintenance', 'running': 'active'}
                rec.asset_id.state = asset_state_map.get(status, rec.asset_id.state)

    def action_assign(self):
        for rec in self:
            if not rec.technician_id:
                raise UserError(_('Assign a technician before starting this work order.'))
            rec.write({'state': 'assigned'})
            rec._set_equipment_status('breakdown' if rec.wo_type == 'breakdown' else 'maintenance')

    def action_start(self):
        for rec in self:
            rec.write({'state': 'in_progress', 'start_datetime': fields.Datetime.now()})
            rec._set_equipment_status('maintenance')

    def action_submit_for_approval(self):
        self.write({'state': 'testing', 'approval_status': 'pending'})

    def action_approve(self):
        self.write({
            'approval_status': 'approved',
            'approved_by_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })

    def action_reject(self):
        self.write({'approval_status': 'rejected'})

    def action_complete(self):
        for rec in self:
            if rec.approval_status == 'pending':
                raise UserError(_('This work order is pending manager approval.'))
            vals = {
                'state': 'completed',
                'end_datetime': rec.end_datetime or fields.Datetime.now(),
            }
            rec.write(vals)
            # Resolve the linked shop-floor downtime event (garment_production) —
            # this Work Order is what closes it, not a duplicate downtime record.
            if rec.downtime_id and rec.downtime_id.status == 'open':
                rec.downtime_id.write({'action_taken': rec.action_taken or rec.downtime_id.action_taken})
                rec.downtime_id.action_resolve()
            rec._set_equipment_status('running')
            # Roll the PM schedule forward when this closes a preventive plan job.
            if rec.plan_id:
                rec.plan_id.action_advance_schedule(done_date=fields.Date.context_today(rec))
        return True

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_view_downtime(self):
        self.ensure_one()
        return {
            'name': _('Downtime Event'), 'type': 'ir.actions.act_window', 'res_model': 'garment.machine.downtime',
            'view_mode': 'form', 'res_id': self.downtime_id.id,
        }


class GarmentMaintenanceWorkorderChecklistLine(models.Model):
    _name = 'garment.maintenance.workorder.checklist.line'
    _description = 'Garment Maintenance Work Order Checklist Execution Line'
    _order = 'sequence, id'

    workorder_id = fields.Many2one('garment.maintenance.workorder', string='Work Order',
                                    required=True, ondelete='cascade')
    checklist_line_id = fields.Many2one('garment.maintenance.checklist.line', string='Checklist Item')
    sequence = fields.Integer(default=10)
    check_item = fields.Char(string='Check Item', required=True)
    result = fields.Selection([
        ('pass', 'OK'),
        ('fail', 'Not OK'),
        ('na', 'N/A'),
    ], string='Result', default='pass')
    remark = fields.Char(string='Remark')


class GarmentMaintenanceWorkorderSpareLine(models.Model):
    """Spare Parts Issue Management (Maintenance & Asset Mgmt SRS sec.
    24, CMMS SRS sec. 18). Spare parts are NOT re-modeled as a separate
    master — this line consumes the shared Material Master
    (``garment.material``, category Spare Parts, from garment_warehouse)
    and posts a real ``garment.stock.move`` so the material's on-hand
    quantity actually decreases. See IMPLEMENTATION_NOTES.md."""
    _name = 'garment.maintenance.workorder.spare.line'
    _description = 'Garment Maintenance Work Order Spare Part Line'
    _order = 'id'

    workorder_id = fields.Many2one('garment.maintenance.workorder', string='Work Order',
                                    required=True, ondelete='cascade')
    material_id = fields.Many2one('garment.material', string='Spare Part', required=True,
                                   domain=[('category', '=', 'spare_parts')])
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    unit_cost = fields.Monetary(string='Unit Cost', currency_field='currency_id')
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='workorder_id.currency_id', store=True)
    move_id = fields.Many2one('garment.stock.move', string='Stock Move', readonly=True, copy=False)
    issue_date = fields.Date(string='Issue Date', default=fields.Date.context_today)

    @api.depends('quantity', 'unit_cost')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = (rec.quantity or 0.0) * (rec.unit_cost or 0.0)

    @api.onchange('material_id')
    def _onchange_material_id(self):
        if self.material_id:
            self.unit_cost = self.material_id.standard_cost

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            line._post_stock_move()
        return lines

    def _post_stock_move(self):
        for line in self:
            if line.move_id or not line.material_id:
                continue
            warehouse = line.material_id.default_warehouse_id
            if not warehouse:
                continue
            move = self.env['garment.stock.move'].create({
                'material_id': line.material_id.id,
                'warehouse_id': warehouse.id,
                'move_type': 'issue',
                'quantity': line.quantity,
                'move_date': line.issue_date or fields.Date.context_today(self),
                'issue_department': False,
                'order_reference': line.workorder_id.name,
                'reference': _('Maintenance Work Order %s') % (line.workorder_id.name or ''),
                'remarks': _('Spare part issued for maintenance work order.'),
            })
            line.move_id = move.id
