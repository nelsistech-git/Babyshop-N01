# -*- coding: utf-8 -*-
"""Work Order, team assignment, inventory availability, reservation and
delivery (SRS 27 - 31, 34, 35, 41)."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero

from .gc_service_catalog import BILLING_POLICY_SELECTION

WO_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('ready', 'Ready'),
    ('assigned', 'Assigned'),
    ('material_pending', 'Material Pending'),
    ('ready_install', 'Ready for Installation'),
    ('installing', 'Installation Ongoing'),
    ('install_done', 'Installation Completed'),
    ('qc', 'Quality Check'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

MATERIAL_STATE_SELECTION = [
    ('none', 'No Material Required'),
    ('available', 'Available'),
    ('shortage', 'Shortage'),
    ('reserved', 'Reserved'),
    ('delivered', 'Delivered'),
]


class GcErmWorkOrder(models.Model):
    _name = 'gc.erm.work.order'
    _description = 'GC ERM Work Order'
    _inherit = ['gc.erm.document.mixin']
    _order = 'priority desc, start_date desc, id desc'

    _gc_sequence_code = 'gc.erm.work.order'
    _gc_sla_parameter = 'gc_erm.sla_implementation_days'
    _gc_closed_states = ('completed', 'cancelled')

    state = fields.Selection(
        WO_STATE_SELECTION, string='Status', default='draft', required=True,
        copy=False, tracking=True, index=True, group_expand='_group_expand_state')

    # ------------------------------------------------------------------
    # References (SRS 27)
    # ------------------------------------------------------------------
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order', required=True, ondelete='restrict',
        index=True, tracking=True, domain="[('state', '=', 'sale')]")
    proposal_id = fields.Many2one(
        'gc.erm.proposal', string='Proposal', ondelete='restrict', index=True)
    lead_id = fields.Many2one(
        'gc.erm.lead', string='Lead', ondelete='restrict', index=True)
    survey_id = fields.Many2one('gc.erm.survey', string='Survey')
    technical_report_id = fields.Many2one(
        'gc.erm.technical.report', string='Technical Report')
    boq_id = fields.Many2one('gc.erm.boq', string='BOQ', index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, index=True,
        tracking=True)
    contact_id = fields.Many2one('res.partner', string='Site Contact')

    service_ids = fields.Many2many(
        'gc.erm.service.catalog', string='Services')
    service_summary = fields.Char(
        string='Service', compute='_compute_service_summary', store=True)

    # ------------------------------------------------------------------
    # Location
    # ------------------------------------------------------------------
    street = fields.Char(string='Address')
    city = fields.Char(string='City')
    district = fields.Char(string='District')
    area = fields.Char(string='Area')
    service_location = fields.Char(string='Service Location')
    gps_latitude = fields.Float(string='GPS Latitude', digits=(10, 7))
    gps_longitude = fields.Float(string='GPS Longitude', digits=(10, 7))
    map_url = fields.Char(string='Map Link', compute='_compute_map_url')

    # ------------------------------------------------------------------
    # Planning and team (SRS 29)
    # ------------------------------------------------------------------
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one('project.task', string='Project Task', copy=False)
    manager_id = fields.Many2one(
        'res.users', string='Implementation Manager', tracking=True, index=True)
    team_id = fields.Many2one(
        'gc.erm.team', string='Implementation Team', tracking=True,
        domain="[('team_type', 'in', ('implementation', 'both'))]")
    team_leader_id = fields.Many2one('res.users', string='Team Leader')
    engineer_id = fields.Many2one(
        'res.users', string='Engineer', tracking=True, index=True)
    technician_ids = fields.Many2many(
        'res.users', 'gc_wo_technician_rel', 'wo_id', 'user_id',
        string='Technicians')
    start_date = fields.Date(string='Start Date', tracking=True)
    schedule_date = fields.Date(string='Schedule Date', tracking=True)
    expected_completion = fields.Date(
        string='Expected Completion', tracking=True)
    actual_completion = fields.Date(
        string='Actual Completion', readonly=True, copy=False)
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1', index=True, tracking=True)
    is_delayed = fields.Boolean(
        string='Delayed', compute='_compute_is_delayed', store=True)

    installation_requirements = fields.Html(
        string='Installation Requirements', sanitize=True)
    special_requirements = fields.Text(string='Special Requirements')
    remarks = fields.Text(string='Remarks')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'gc_wo_attachment_rel', 'wo_id', 'attachment_id',
        string='Technical Documents')

    # ------------------------------------------------------------------
    # Materials and inventory (SRS 30 / 31 / 34)
    # ------------------------------------------------------------------
    line_ids = fields.One2many(
        'gc.erm.work.order.line', 'work_order_id', string='Required Materials',
        copy=True)
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        default=lambda self: self._default_warehouse(),
        help='Warehouse checked for material availability and used for the '
             'delivery order.')
    material_state = fields.Selection(
        MATERIAL_STATE_SELECTION, string='Material Status',
        compute='_compute_material_state', store=True, tracking=True)
    total_required_qty = fields.Float(
        string='Required Qty', compute='_compute_material_totals', store=True)
    total_available_qty = fields.Float(
        string='Available Qty', compute='_compute_material_totals', store=True)
    total_shortage_qty = fields.Float(
        string='Shortage Qty', compute='_compute_material_totals', store=True)
    last_stock_check = fields.Datetime(
        string='Last Inventory Check', readonly=True, copy=False)

    # Only outgoing transfers count as deliveries to the implementation team.
    # Purchase receipts are linked to the same work order for traceability but
    # must never be mistaken for a delivery (SRS 35).
    picking_ids = fields.One2many(
        'stock.picking', 'gc_work_order_id', string='Deliveries',
        domain=[('picking_type_code', '=', 'outgoing')])
    receipt_ids = fields.One2many(
        'stock.picking', 'gc_work_order_id', string='Receipts',
        domain=[('picking_type_code', '=', 'incoming')])
    picking_count = fields.Integer(compute='_compute_operation_counts')
    receipt_count = fields.Integer(compute='_compute_operation_counts')
    delivery_state = fields.Char(
        string='Delivery Status', compute='_compute_delivery_state')
    procurement_ids = fields.One2many(
        'gc.erm.procurement.request', 'work_order_id',
        string='Procurement Requests')
    procurement_count = fields.Integer(compute='_compute_operation_counts')
    purchase_order_count = fields.Integer(compute='_compute_operation_counts')
    installation_ids = fields.One2many(
        'gc.erm.installation', 'work_order_id', string='Installations')
    installation_count = fields.Integer(compute='_compute_operation_counts')
    invoice_count = fields.Integer(compute='_compute_operation_counts')

    # ------------------------------------------------------------------
    # Billing (SRS 41 / 43)
    # ------------------------------------------------------------------
    billing_policy = fields.Selection(
        BILLING_POLICY_SELECTION, string='Billing Policy', required=True,
        default='full', tracking=True)
    advance_percent = fields.Float(string='Advance %', default=0.0)
    installation_percent = fields.Float(string='Installation %', default=0.0)
    completion_percent = fields.Float(string='Completion %', default=0.0)
    billing_ready = fields.Boolean(
        string='Billing Ready', compute='_compute_billing_ready', store=True,
        tracking=True)
    billing_blocked_reason = fields.Char(
        string='Billing Blocked Because', compute='_compute_billing_ready',
        store=True)
    amount_total = fields.Monetary(
        string='Order Total', related='sale_order_id.amount_total', store=True,
        currency_field='currency_id')
    amount_invoiced = fields.Monetary(
        string='Invoiced', compute='_compute_invoice_amounts',
        currency_field='currency_id')
    amount_residual = fields.Monetary(
        string='Outstanding', compute='_compute_invoice_amounts',
        currency_field='currency_id')

    # ------------------------------------------------------------------
    # Defaults / compute
    # ------------------------------------------------------------------
    @api.model
    def _default_warehouse(self):
        return self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1)

    @api.model
    def _group_expand_state(self, states, domain, order=None):
        return [key for key, _label in WO_STATE_SELECTION]

    @api.depends('gps_latitude', 'gps_longitude')
    def _compute_map_url(self):
        for wo in self:
            if wo.gps_latitude or wo.gps_longitude:
                wo.map_url = (
                    'https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=17/%s/%s'
                    % (wo.gps_latitude, wo.gps_longitude,
                       wo.gps_latitude, wo.gps_longitude))
            else:
                wo.map_url = False

    @api.depends('service_ids')
    def _compute_service_summary(self):
        for wo in self:
            wo.service_summary = ', '.join(wo.service_ids.mapped('name')) or ''

    @api.depends('line_ids.required_qty', 'line_ids.available_qty',
                 'line_ids.shortage_qty')
    def _compute_material_totals(self):
        for wo in self:
            wo.total_required_qty = sum(wo.line_ids.mapped('required_qty'))
            wo.total_available_qty = sum(wo.line_ids.mapped('available_qty'))
            wo.total_shortage_qty = sum(wo.line_ids.mapped('shortage_qty'))

    @api.depends('line_ids.shortage_qty', 'line_ids.required_qty',
                 'picking_ids.state')
    def _compute_material_state(self):
        for wo in self:
            storable = wo.line_ids.filtered(
                lambda l: l.product_id.type == 'product')
            if not storable:
                wo.material_state = 'none'
                continue
            done_pickings = wo.picking_ids.filtered(lambda p: p.state == 'done')
            if done_pickings:
                wo.material_state = 'delivered'
                continue
            if float_compare(sum(storable.mapped('shortage_qty')), 0.0,
                             precision_digits=4) > 0:
                wo.material_state = 'shortage'
                continue
            assigned = wo.picking_ids.filtered(
                lambda p: p.state in ('assigned', 'confirmed', 'waiting'))
            wo.material_state = 'reserved' if assigned else 'available'

    def _compute_operation_counts(self):
        Purchase = self.env['purchase.order']
        Move = self.env['account.move']
        for wo in self:
            wo.picking_count = len(wo.picking_ids)
            wo.receipt_count = len(wo.receipt_ids)
            wo.procurement_count = len(wo.procurement_ids)
            wo.installation_count = len(wo.installation_ids)
            wo.purchase_order_count = Purchase.search_count(
                [('gc_work_order_id', '=', wo.id)])
            wo.invoice_count = Move.search_count([
                ('gc_work_order_id', '=', wo.id),
                ('move_type', 'in', ('out_invoice', 'out_refund'))])

    @api.depends('picking_ids.state')
    def _compute_delivery_state(self):
        labels = dict(self.env['stock.picking']._fields['state'].selection)
        for wo in self:
            pickings = wo.picking_ids
            if not pickings:
                wo.delivery_state = _('No delivery')
            elif all(p.state == 'done' for p in pickings):
                wo.delivery_state = _('Done')
            elif any(p.state == 'done' for p in pickings):
                wo.delivery_state = _('Partially Delivered')
            elif any(p.state == 'cancel' for p in pickings) and \
                    all(p.state == 'cancel' for p in pickings):
                wo.delivery_state = _('Cancelled')
            else:
                pending = pickings.filtered(lambda p: p.state != 'cancel')[:1]
                wo.delivery_state = labels.get(pending.state, pending.state) \
                    if pending else _('Waiting')

    @api.depends('expected_completion', 'state', 'actual_completion')
    def _compute_is_delayed(self):
        today = fields.Date.context_today(self)
        for wo in self:
            wo.is_delayed = bool(
                wo.expected_completion and not wo.actual_completion
                and wo.expected_completion < today
                and wo.state not in ('completed', 'cancelled'))

    @api.depends('state', 'billing_policy', 'sale_order_id.state',
                 'installation_ids.state', 'installation_ids.result',
                 'picking_ids.state')
    def _compute_billing_ready(self):
        """SRS 41 -- billing readiness rules."""
        for wo in self:
            ready, reason = wo._evaluate_billing_ready()
            wo.billing_ready = ready
            wo.billing_blocked_reason = reason

    def _evaluate_billing_ready(self):
        self.ensure_one()
        if not self.sale_order_id or self.sale_order_id.state != 'sale':
            return False, _('The sales order is not confirmed.')
        policy = self.billing_policy
        if policy in ('advance', 'advance_final'):
            # Advance invoicing is allowed as soon as the order is confirmed.
            return True, False
        if policy == 'delivery':
            if self.picking_ids and all(
                    p.state in ('done', 'cancel') for p in self.picking_ids) \
                    and any(p.state == 'done' for p in self.picking_ids):
                return True, False
            return False, _('Delivery is not completed yet.')
        if policy == 'recurring':
            return False, _('Recurring billing is handled in a later phase.')
        # 'full' and 'milestone' both require a successful installation
        # whenever installation is required for the ordered services.
        if not self._installation_required():
            return True, False
        successful = self.installation_ids.filtered(
            lambda i: i.state == 'done' and i.result in ('success', 'partial'))
        if successful:
            return True, False
        return False, _('A successful installation report is required.')

    def _installation_required(self):
        self.ensure_one()
        if self.service_ids:
            return any(self.service_ids.mapped('installation_required'))
        return bool(self.line_ids)

    def _compute_invoice_amounts(self):
        for wo in self:
            invoices = self.env['account.move'].search([
                ('gc_work_order_id', '=', wo.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
            ])
            signed_total = sum(
                inv.amount_total_signed for inv in invoices)
            signed_residual = sum(
                inv.amount_residual_signed for inv in invoices)
            wo.amount_invoiced = signed_total
            wo.amount_residual = signed_residual

    # ------------------------------------------------------------------
    # Constraints (SRS 66 / BR-006)
    # ------------------------------------------------------------------
    @api.constrains('sale_order_id')
    def _check_sale_order_confirmed(self):
        for wo in self:
            if wo.sale_order_id.state != 'sale' and \
                    not self.env.context.get('gc_bypass_so_check'):
                raise ValidationError(_(
                    'Customer acceptance is required before creating the work '
                    'order. Sales order %s is not confirmed.',
                    wo.sale_order_id.name))

    @api.constrains('advance_percent', 'installation_percent',
                    'completion_percent', 'billing_policy')
    def _check_milestones(self):
        for wo in self:
            if wo.billing_policy != 'milestone':
                continue
            total = (wo.advance_percent + wo.installation_percent
                     + wo.completion_percent)
            if abs(total - 100.0) > 0.01:
                raise ValidationError(_(
                    'Milestone percentages of work order %(name)s must add up '
                    'to 100%%, they currently add up to %(total).2f%%.',
                    name=wo.name, total=total))

    @api.constrains('start_date', 'expected_completion')
    def _check_dates(self):
        for wo in self:
            if wo.start_date and wo.expected_completion and \
                    wo.expected_completion < wo.start_date:
                raise ValidationError(_(
                    'The expected completion date cannot be before the start '
                    'date.'))

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        for wo in self:
            order = wo.sale_order_id
            if not order:
                continue
            wo.partner_id = order.partner_id
            wo.proposal_id = order.gc_proposal_id
            wo.lead_id = order.gc_lead_id
            wo.survey_id = order.gc_survey_id
            wo.boq_id = order.gc_boq_id
            wo.company_id = order.company_id
            wo.currency_id = order.currency_id
            survey = order.gc_survey_id
            if survey:
                wo.street = survey.street
                wo.city = survey.city
                wo.district = survey.district
                wo.area = survey.area
                wo.service_location = survey.service_location
                wo.gps_latitude = survey.gps_latitude
                wo.gps_longitude = survey.gps_longitude
                wo.contact_id = survey.contact_id
                wo.service_ids = [(6, 0, survey.service_ids.ids)]
            services = wo.service_ids
            if services:
                wo.billing_policy = services[0].billing_policy
                wo.advance_percent = services[0].advance_percent
                wo.installation_percent = services[0].installation_percent
                wo.completion_percent = services[0].completion_percent

    @api.onchange('team_id')
    def _onchange_team_id(self):
        for wo in self:
            if wo.team_id:
                wo.team_leader_id = wo.team_id.leader_id
                if not wo.engineer_id:
                    wo.engineer_id = wo.team_id.leader_id

    # ------------------------------------------------------------------
    # Material line generation
    # ------------------------------------------------------------------
    def action_load_materials_from_boq(self):
        """Populate the required materials from the BOQ / sales order."""
        for wo in self:
            if wo.state not in ('draft', 'ready', 'assigned', 'material_pending'):
                raise UserError(_(
                    'Materials can only be loaded before the installation '
                    'starts.'))
            wo.line_ids.unlink()
            vals = []
            source_lines = wo.boq_id.line_ids if wo.boq_id else \
                self.env['gc.erm.boq.line']
            if source_lines:
                for line in source_lines:
                    if line.product_id.type not in ('product', 'consu'):
                        continue
                    vals.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'required_qty': line.quantity,
                        'uom_id': (line.uom_id or line.product_id.uom_id).id,
                        'boq_line_id': line.id,
                    }))
            else:
                for line in wo.sale_order_id.order_line:
                    if line.display_type or \
                            line.product_id.type not in ('product', 'consu'):
                        continue
                    vals.append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'required_qty': line.product_uom_qty,
                        'uom_id': line.product_uom.id,
                    }))
            wo.line_ids = vals
            wo.action_check_inventory()
        return True

    # ------------------------------------------------------------------
    # Inventory availability (SRS 30 / 31)
    # ------------------------------------------------------------------
    def action_check_inventory(self):
        """Recompute available and shortage quantities from Odoo stock."""
        for wo in self:
            wo.line_ids._compute_availability()
            wo.last_stock_check = fields.Datetime.now()
            wo._compute_material_totals()
            wo._compute_material_state()
            if wo.state in ('ready', 'assigned', 'material_pending',
                            'ready_install'):
                if wo.material_state == 'shortage':
                    if wo.state != 'material_pending':
                        wo.with_context(gc_bypass_lock=True)._gc_transition(
                            'material_pending',
                            comment=_('Material shortage detected during the '
                                      'inventory check.'))
                        wo._gc_notify(
                            'gc_erm_lead_to_billing.mail_template_gc_material_shortage')
                elif wo.material_state in ('available', 'reserved', 'delivered') \
                        and wo.state == 'material_pending':
                    wo.with_context(gc_bypass_lock=True)._gc_transition(
                        'ready_install',
                        comment=_('All required materials are available.'))
            wo.message_post(body=_(
                'Inventory check: required %(req).2f, available %(avail).2f, '
                'shortage %(short).2f.',
                req=wo.total_required_qty, avail=wo.total_available_qty,
                short=wo.total_shortage_qty))
        return True

    # ------------------------------------------------------------------
    # Workflow (SRS 28 / 29)
    # ------------------------------------------------------------------
    def action_confirm(self):
        for wo in self:
            if wo.state != 'draft':
                raise UserError(_('Only a draft work order can be confirmed.'))
            if wo.sale_order_id.state != 'sale':
                raise UserError(_(
                    'Customer acceptance is required before creating the work '
                    'order.'))
            wo._gc_transition(
                'ready', comment=_('Work order confirmed.'),
                allowed_from=('draft',))
            wo._gc_link_sale_pickings()
            if not wo.line_ids:
                wo.action_load_materials_from_boq()
            else:
                wo.action_check_inventory()
        return True

    def action_assign_team(self):
        for wo in self:
            if wo.state not in ('ready', 'assigned', 'material_pending',
                                'ready_install'):
                raise UserError(_(
                    'The team can only be assigned on a confirmed work order '
                    'that has not started its installation yet.'))
            if not (wo.team_id or wo.engineer_id):
                raise UserError(_(
                    'Select an implementation team or an engineer before '
                    'assigning work order %s.', wo.name))
            if wo.material_state == 'shortage':
                target_state = 'material_pending'
            elif wo.state == 'ready_install':
                # Material is already available: re-assigning the team must not
                # push the work order backwards in the workflow.
                target_state = 'ready_install'
            else:
                target_state = 'assigned'
            wo._gc_transition(
                target_state, comment=_('Implementation team assigned.'))
            for user in (wo.engineer_id | wo.team_leader_id | wo.technician_ids):
                wo._gc_schedule_activity(
                    user, summary=_('Work Order %s assigned', wo.name),
                    note=_('Customer: %(partner)s, location: %(loc)s.',
                           partner=wo.partner_id.display_name,
                           loc=wo.service_location or wo.street or ''),
                    days=1)
            wo._gc_notify(
                'gc_erm_lead_to_billing.mail_template_gc_work_order_assigned')
        return True

    def action_set_ready_for_installation(self):
        for wo in self:
            if wo.state == 'ready_install':
                continue  # already ready, nothing to do
            if wo.state not in ('ready', 'assigned', 'material_pending'):
                raise UserError(_(
                    'Only a confirmed or assigned work order can be marked '
                    'ready for installation.'))
            wo.action_check_inventory()
            if wo.state == 'ready_install':
                continue  # the inventory check already moved it forward
            if wo.material_state == 'shortage':
                raise UserError(_(
                    'Required materials are not available for work order %s. '
                    'Create a procurement request first.', wo.name))
            wo._gc_transition(
                'ready_install', comment=_('Ready for installation.'))
        return True

    def action_start_installation(self):
        for wo in self:
            if wo.state != 'ready_install':
                raise UserError(_(
                    'The work order must be ready for installation first.'))
            wo._gc_transition(
                'installing', comment=_('Installation started.'),
                allowed_from=('ready_install',))
        return True

    def action_installation_done(self):
        """Called by the installation record when it is completed."""
        for wo in self:
            if wo.state in ('installing', 'ready_install'):
                wo._gc_transition(
                    'install_done', comment=_('Installation completed.'))
        return True

    def action_start_qc(self):
        for wo in self:
            if wo.state != 'install_done':
                raise UserError(_(
                    'Quality check can only start after installation.'))
            wo._gc_transition('qc', comment=_('Quality check started.'),
                              allowed_from=('install_done',))
        return True

    def action_complete(self):
        for wo in self:
            if wo.state not in ('install_done', 'qc'):
                raise UserError(_(
                    'The installation must be completed before closing the '
                    'work order.'))
            open_installations = wo.installation_ids.filtered(
                lambda i: i.state not in ('done', 'cancelled'))
            if open_installations:
                raise UserError(_(
                    'Installation %s is still open.',
                    open_installations[0].name))
            wo._gc_transition(
                'completed', comment=_('Work order completed.'),
                extra_vals={'actual_completion': fields.Date.context_today(self)})
            if wo.task_id:
                stage = self.env['project.task.type'].search(
                    [('project_ids', 'in', wo.project_id.ids)], order='sequence desc',
                    limit=1)
                if stage:
                    wo.task_id.stage_id = stage
        return True

    def action_reset_draft(self):
        for wo in self:
            if wo.state not in ('ready', 'cancelled'):
                raise UserError(_(
                    'Only a ready or cancelled work order can be reset.'))
            wo._gc_transition('draft', comment=_('Reset to draft.'))
        return True

    def action_cancel(self):
        for wo in self:
            active_pickings = wo.picking_ids.filtered(
                lambda p: p.state not in ('done', 'cancel'))
            active_pickings.action_cancel()
            if wo.picking_ids.filtered(lambda p: p.state == 'done'):
                raise UserError(_(
                    'Work order %s has delivered materials and cannot be '
                    'cancelled. Create a return first.', wo.name))
            wo._gc_transition('cancelled', comment=_('Work order cancelled.'))
        return True

    # ------------------------------------------------------------------
    # Procurement (SRS 32 / BR-007)
    # ------------------------------------------------------------------
    def action_create_procurement_request(self):
        self.ensure_one()
        self.action_check_inventory()
        shortage_lines = self.line_ids.filtered(
            lambda l: float_compare(l.shortage_qty, 0.0, precision_digits=4) > 0)
        if not shortage_lines:
            raise UserError(_(
                'There is no material shortage on work order %s.', self.name))
        existing = self.procurement_ids.filtered(
            lambda p: p.state not in ('cancelled', 'received'))
        if existing:
            raise UserError(_(
                'Procurement request %s is still open for this work order.',
                existing[0].name))
        request = self.env['gc.erm.procurement.request'].create({
            'work_order_id': self.id,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'requested_by_id': self.env.user.id,
            'required_date': self.start_date or fields.Date.context_today(self),
            'priority': self.priority,
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'required_qty': line.required_qty,
                'available_qty': line.available_qty,
                'shortage_qty': line.shortage_qty,
                'uom_id': line.uom_id.id,
                'work_order_line_id': line.id,
            }) for line in shortage_lines],
        })
        self.message_post(body=_('Procurement request %s created.', request.name))
        self._gc_notify(
            'gc_erm_lead_to_billing.mail_template_gc_material_shortage')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Procurement Request'),
            'res_model': 'gc.erm.procurement.request',
            'res_id': request.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Delivery and reservation (SRS 34 / 35)
    # ------------------------------------------------------------------
    def action_create_delivery(self):
        """Create a standard ``stock.picking`` for the implementation team."""
        self.ensure_one()
        storable = self.line_ids.filtered(
            lambda l: l.product_id.type in ('product', 'consu'))
        if not storable:
            raise UserError(_(
                'Work order %s has no stockable material to deliver.', self.name))
        self.action_check_inventory()
        if self.material_state == 'shortage':
            raise UserError(_(
                'Required materials are not available. Complete the '
                'procurement before creating the delivery.'))
        # SRS 35 / design principle 2 -- never duplicate an Odoo delivery.
        # A confirmed sales order already generates its own outgoing transfer,
        # so the work order adopts it instead of creating a second one.
        self._gc_link_sale_pickings()
        open_picking = self.picking_ids.filtered(
            lambda p: p.state not in ('done', 'cancel'))
        if open_picking:
            open_picking.action_assign()
            self._compute_material_state()
            self.message_post(body=_(
                'Delivery %s reserved for the implementation team.',
                ', '.join(open_picking.mapped('name'))))
            return self.action_view_pickings()
        if self.picking_ids.filtered(lambda p: p.state == 'done'):
            raise UserError(_(
                'The materials of work order %s have already been delivered.',
                self.name))
        warehouse = self.warehouse_id or self._default_warehouse()
        if not warehouse:
            raise UserError(_('No warehouse is configured for this company.'))
        picking_type = warehouse.out_type_id
        picking = self.env['stock.picking'].create({
            'partner_id': (self.contact_id or self.partner_id).id,
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id
            or warehouse.lot_stock_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id
            or self.env.ref('stock.stock_location_customers').id,
            'scheduled_date': fields.Datetime.now(),
            'origin': self.name,
            'company_id': self.company_id.id,
            'gc_work_order_id': self.id,
            'gc_sale_order_id': self.sale_order_id.id,
            'gc_team_id': self.team_id.id,
            'move_ids_without_package': [(0, 0, {
                'name': line.name or line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.required_qty,
                'product_uom': (line.uom_id or line.product_id.uom_id).id,
                'location_id': picking_type.default_location_src_id.id
                or warehouse.lot_stock_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id
                or self.env.ref('stock.stock_location_customers').id,
                'company_id': self.company_id.id,
            }) for line in storable],
        })
        picking.action_confirm()
        # SRS 34 -- use the standard Odoo reservation mechanism.
        picking.action_assign()
        self.message_post(body=_('Delivery %s created and reserved.',
                                 picking.name))
        self._compute_material_state()
        return self.action_view_pickings()

    def _gc_link_sale_pickings(self):
        """Attach the sales order's own transfers to this work order."""
        for wo in self:
            pickings = wo.sale_order_id.picking_ids.filtered(
                lambda p: p.state != 'cancel' and not p.gc_work_order_id)
            if pickings:
                pickings.write({
                    'gc_work_order_id': wo.id,
                    'gc_sale_order_id': wo.sale_order_id.id,
                    'gc_team_id': wo.team_id.id or False,
                })
        return True

    def action_reserve_stock(self):
        for wo in self:
            pickings = wo.picking_ids.filtered(
                lambda p: p.state not in ('done', 'cancel'))
            if not pickings:
                raise UserError(_(
                    'Create the delivery order of %s before reserving stock.',
                    wo.name))
            pickings.action_assign()
            wo._compute_material_state()
        return True

    # ------------------------------------------------------------------
    # Installation (SRS 36 / BR-008)
    # ------------------------------------------------------------------
    def action_create_installation(self):
        self.ensure_one()
        if self.state not in ('ready_install', 'installing', 'assigned'):
            raise UserError(_(
                'The work order must be ready for installation before an '
                'installation record can be created.'))
        installation = self.env['gc.erm.installation'].create({
            'work_order_id': self.id,
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'team_id': self.team_id.id,
            'engineer_id': self.engineer_id.id or self.env.user.id,
            'installation_date': self.schedule_date
            or fields.Date.context_today(self),
        })
        if self.state == 'ready_install':
            self.action_start_installation()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Installation'),
            'res_model': 'gc.erm.installation',
            'res_id': installation.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Project task (SRS 27)
    # ------------------------------------------------------------------
    def action_create_project_task(self):
        self.ensure_one()
        if self.task_id:
            return self.action_view_task()
        if not self.project_id:
            raise UserError(_(
                'Select a project on work order %s first.', self.name))
        task = self.env['project.task'].create({
            'name': _('%(wo)s - %(partner)s', wo=self.name,
                      partner=self.partner_id.display_name),
            'project_id': self.project_id.id,
            'partner_id': self.partner_id.id,
            'user_ids': [(6, 0, (self.engineer_id | self.team_leader_id).ids)],
            'date_deadline': self.expected_completion,
            'company_id': self.company_id.id,
        })
        self.task_id = task
        return self.action_view_task()

    # ------------------------------------------------------------------
    # Billing (SRS 42)
    # ------------------------------------------------------------------
    def action_open_invoice_wizard(self):
        self.ensure_one()
        if not self.billing_ready:
            raise UserError(_(
                'Billing conditions have not been satisfied: %s',
                self.billing_blocked_reason or _('unknown reason')))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Invoice'),
            'res_model': 'gc.erm.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_work_order_id': self.id},
        }

    # ------------------------------------------------------------------
    # Smart buttons (SRS 46)
    # ------------------------------------------------------------------
    def _gc_action_window(self, name, model, domain, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': name, 'res_model': model,
            'view_mode': 'tree,form', 'domain': domain,
            'context': dict(context or {}),
        }

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'sale.order',
            'res_id': self.sale_order_id.id, 'view_mode': 'form',
        }

    def action_view_pickings(self):
        return self._gc_action_window(
            _('Deliveries'), 'stock.picking',
            [('gc_work_order_id', '=', self.id),
             ('picking_type_code', '=', 'outgoing')])

    def action_view_receipts(self):
        return self._gc_action_window(
            _('Receipts'), 'stock.picking',
            [('gc_work_order_id', '=', self.id),
             ('picking_type_code', '=', 'incoming')])

    def action_view_procurements(self):
        return self._gc_action_window(
            _('Procurement Requests'), 'gc.erm.procurement.request',
            [('work_order_id', '=', self.id)])

    def action_view_purchase_orders(self):
        return self._gc_action_window(
            _('Purchase Orders'), 'purchase.order',
            [('gc_work_order_id', '=', self.id)])

    def action_view_installations(self):
        return self._gc_action_window(
            _('Installations'), 'gc.erm.installation',
            [('work_order_id', '=', self.id)])

    def action_view_invoices(self):
        return self._gc_action_window(
            _('Invoices'), 'account.move',
            [('gc_work_order_id', '=', self.id),
             ('move_type', 'in', ('out_invoice', 'out_refund'))])

    def action_view_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'project.task',
            'res_id': self.task_id.id, 'view_mode': 'form',
        }

    @api.depends('name', 'partner_id')
    def _compute_display_name(self):
        for wo in self:
            wo.display_name = '%s - %s' % (wo.name, wo.partner_id.name) \
                if wo.partner_id else wo.name

    # ------------------------------------------------------------------
    # Cron (SRS 80)
    # ------------------------------------------------------------------
    @api.model
    def _cron_check_work_order_delay(self):
        today = fields.Date.context_today(self)
        delayed = self.search([
            ('state', 'not in', ('completed', 'cancelled')),
            ('expected_completion', '<', today),
        ])
        for wo in delayed:
            wo._compute_is_delayed()
            responsible = wo.manager_id or wo.engineer_id
            if responsible:
                wo._gc_schedule_activity(
                    responsible, summary=_('Delayed work order %s', wo.name),
                    note=_('Expected completion was %s.', wo.expected_completion),
                    days=0)
        return True


class GcErmWorkOrderLine(models.Model):
    _name = 'gc.erm.work.order.line'
    _description = 'GC ERM Work Order Material Line'
    _order = 'work_order_id, sequence, id'

    work_order_id = fields.Many2one(
        'gc.erm.work.order', string='Work Order', required=True,
        ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        related='work_order_id.company_id', store=True, index=True)
    product_id = fields.Many2one(
        'product.product', string='Product', required=True)
    name = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    boq_line_id = fields.Many2one(
        'gc.erm.boq.line', string='BOQ Line', ondelete='set null')

    required_qty = fields.Float(
        string='Required Qty', default=1.0, required=True,
        digits='Product Unit of Measure')
    available_qty = fields.Float(
        string='Available Qty', readonly=True,
        digits='Product Unit of Measure')
    reserved_qty = fields.Float(
        string='Reserved Qty', compute='_compute_reserved_qty',
        digits='Product Unit of Measure')
    shortage_qty = fields.Float(
        string='Shortage Qty', readonly=True, digits='Product Unit of Measure',
        help='Required Qty - Available Qty, never negative.')
    availability = fields.Selection([
        ('available', 'Available'),
        ('shortage', 'Not Available'),
    ], string='Availability', readonly=True, default='shortage')
    remarks = fields.Char(string='Remarks')

    def _compute_availability(self):
        """SRS 30 -- Shortage = Required Qty - Available Qty.

        "Available" means available *to this work order*: the free stock of the
        warehouse plus whatever the work order's own delivery has already
        reserved. Without the second term a work order would report a shortage
        as soon as Odoo reserved the goods for its own delivery order.
        """
        for line in self:
            product = line.product_id
            if product.type != 'product':
                # Services and consumables are always considered available.
                line.available_qty = line.required_qty
                line.shortage_qty = 0.0
                line.availability = 'available'
                continue
            warehouse = line.work_order_id.warehouse_id
            ctx_product = product.with_company(line.company_id)
            if warehouse:
                ctx_product = ctx_product.with_context(warehouse=warehouse.id)
            available = ctx_product.free_qty + line._own_reserved_qty()
            line.available_qty = available
            shortage = line.required_qty - available
            line.shortage_qty = shortage if shortage > 0 else 0.0
            line.availability = 'shortage' if shortage > 0 else 'available'
        return True

    def _own_reserved_qty(self):
        """Quantity already reserved by this work order's own deliveries."""
        self.ensure_one()
        moves = self.work_order_id.picking_ids.filtered(
            lambda p: p.state not in ('done', 'cancel')).move_ids.filtered(
                lambda m: m.product_id == self.product_id
                and m.state not in ('done', 'cancel'))
        return sum(moves.mapped('quantity'))

    @api.depends('work_order_id.picking_ids.state',
                 'work_order_id.picking_ids.move_ids.quantity')
    def _compute_reserved_qty(self):
        for line in self:
            moves = line.work_order_id.picking_ids.filtered(
                lambda p: p.state not in ('done', 'cancel')).move_ids.filtered(
                    lambda m: m.product_id == line.product_id)
            line.reserved_qty = sum(moves.mapped('quantity'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.display_name
                line.uom_id = line.product_id.uom_id

    @api.constrains('required_qty')
    def _check_required_qty(self):
        for line in self:
            if float_is_zero(line.required_qty, precision_digits=4) or \
                    line.required_qty < 0:
                raise ValidationError(_(
                    'The required quantity of "%s" must be greater than zero.',
                    line.product_id.display_name))
