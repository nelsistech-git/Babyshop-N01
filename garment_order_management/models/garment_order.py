# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Header fields restricted once the order is locked after confirmation (SRS
# section 44 - Order Locking System: "Restricted changes: Quantity, Price,
# Delivery Date, Style Information"). Order-line quantity/price/style is
# guarded the same way in garment.order.line.write(). Everything else on
# the header (status updates, progress, risk, material/capacity tracking,
# documents...) stays freely editable while locked.
_LOCKED_HEADER_FIELDS = {'style_id', 'delivery_date', 'shipment_date'}


class GarmentOrder(models.Model):
    """Order Master (SRS sections 6-8, 39, 41) - garment.order.

    The central Sales/Production Order document of the Nelsis Smart Garment
    suite: it links the Buyer (garment.buyer), the confirmed Style
    (garment.style) and the Merchandising hand-over
    (garment.merch.order.confirmation) that originated it, and carries the
    order number, style/colorway/size breakdown, quantities, ship dates,
    order value and full status workflow that Production, Shipment and
    Finance modules hook into.
    """
    _name = 'garment.order'
    _description = 'Garment Buyer Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'order_date desc, name desc'
    _rec_name = 'name'

    # ------------------------------------------------------------------
    # Order Master / Buyer PO Information (SRS 6, 8)
    # ------------------------------------------------------------------
    name = fields.Char(string='Order Number', copy=False, readonly=True, index=True,
                        default=lambda s: _('New'), help='Natural key used by Production, Shipment '
                                                           'and Finance modules to reference this order.')
    buyer_po_number = fields.Char(string='Buyer PO Number', tracking=True)
    po_date = fields.Date(string='PO Date')
    buyer_reference = fields.Char(string='Buyer Reference')
    contract_number = fields.Char(string='Contract Number')

    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    brand = fields.Char(string='Brand')
    buying_house = fields.Char(string='Buying House')
    season = fields.Char(string='Season')
    collection = fields.Char(string='Collection')

    merch_order_confirmation_id = fields.Many2one(
        'garment.merch.order.confirmation', string='Origin Order Confirmation', tracking=True,
        help='The Merchandising order-confirmation hand-over this order was raised from.')
    quotation_id = fields.Many2one('garment.merch.quotation', string='Origin Quotation',
                                    related='merch_order_confirmation_id.quotation_id', store=True, readonly=True)

    style_id = fields.Many2one('garment.style', string='Style (Primary)', tracking=True,
                                help='Primary/lead style of this order. Additional styles are carried on the '
                                     'Order Lines below (an order can contain multiple styles).')
    product_category_id = fields.Many2one('garment.style.category', string='Product Category',
                                           related='style_id.style_category_id', store=True, readonly=True)
    bom_id = fields.Many2one('garment.bom', string='BOM Reference', tracking=True,
                              domain="[('style_id', '=', style_id)]",
                              help='Order-wise BOM link (SRS section 23) used for material requirement planning.')
    costing_id = fields.Many2one('garment.costing', string='Approved Costing', tracking=True,
                                  domain="[('style_id', '=', style_id)]",
                                  groups='base.group_user',
                                  help='Approved cost sheet used for cost verification and profitability.')
    tna_id = fields.Many2one('garment.tna', string='TNA Plan', tracking=True,
                              help='Time & Action plan governing this order.')

    order_date = fields.Date(string='Order Date', default=fields.Date.context_today, tracking=True)
    delivery_date = fields.Date(string='Delivery Date', tracking=True)
    shipment_date = fields.Date(string='Shipment Date', tracking=True)

    factory = fields.Char(string='Factory')
    production_unit = fields.Char(string='Production Unit')
    merchandiser_id = fields.Many2one('res.users', string='Merchandiser', default=lambda s: s.env.user,
                                       tracking=True)

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda s: s.env.company.currency_id)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    shipment_term = fields.Selection([
        ('fob', 'FOB'), ('cif', 'CIF'), ('cfr', 'CFR'), ('exw', 'EXW'),
    ], string='Shipment Terms')
    delivery_location = fields.Char(string='Delivery Location')
    port_of_loading = fields.Char(string='Port of Loading')
    port_of_destination = fields.Char(string='Port of Destination')

    # ------------------------------------------------------------------
    # Bangladesh Export Order Standards (SRS section 51)
    # ------------------------------------------------------------------
    buyer_country_id = fields.Many2one('res.country', string='Buyer Country')
    hs_code = fields.Char(string='HS Code')
    export_category = fields.Char(string='Export Category')
    shipment_mode = fields.Selection([
        ('sea', 'Sea'), ('air', 'Air'), ('courier', 'Courier'), ('multimodal', 'Multimodal'),
    ], string='Shipment Mode')
    forwarder_details = fields.Char(string='Forwarder Details')

    # ------------------------------------------------------------------
    # Quantity / Value roll-ups (from Order Lines - SRS section 10)
    # ------------------------------------------------------------------
    line_ids = fields.One2many('garment.order.line', 'order_id', string='Order Lines')
    quantity = fields.Integer(string='Total Order Quantity', compute='_compute_line_totals', store=True,
                               tracking=True)
    order_value = fields.Monetary(string='Total Order Value', compute='_compute_line_totals', store=True,
                                   currency_field='currency_id', tracking=True)

    shipment_ids = fields.One2many('garment.order.shipment', 'order_id', string='Shipments')
    shipped_qty = fields.Integer(string='Shipped Quantity', compute='_compute_shipment_totals', store=True)
    balance_qty = fields.Integer(string='Balance Quantity', compute='_compute_shipment_totals', store=True,
                                  help='Order Quantity - Shipped Quantity (SRS section 29).')

    allocation_ids = fields.One2many('garment.order.allocation', 'order_id', string='Factory Allocations')
    risk_ids = fields.One2many('garment.order.risk', 'order_id', string='Risk Factors')
    document_ids = fields.One2many('garment.order.document', 'order_id', string='Document Checklist')
    revision_ids = fields.One2many('garment.order.revision', 'order_id', string='Revisions')
    approval_ids = fields.One2many('garment.order.approval', 'order_id', string='Approval Stages')
    delay_ids = fields.One2many('garment.order.delay', 'order_id', string='Delays')

    line_count = fields.Integer(compute='_compute_counts')
    shipment_count = fields.Integer(compute='_compute_counts')
    allocation_count = fields.Integer(compute='_compute_counts')
    risk_count = fields.Integer(compute='_compute_counts')
    document_count = fields.Integer(compute='_compute_counts')
    revision_count = fields.Integer(compute='_compute_counts')
    delay_count = fields.Integer(compute='_compute_counts')
    techpack_count = fields.Integer(compute='_compute_style_linked_counts',
                                     help='Tech Packs auto-retrieved from the linked Style (SRS section 11).')
    sample_count = fields.Integer(compute='_compute_style_linked_counts',
                                   help='Samples auto-retrieved from the linked Style (SRS section 11).')

    # ------------------------------------------------------------------
    # Status Workflow (SRS section 7)
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('po_received', 'PO Received'),
        ('confirmed', 'Order Confirmed'),
        ('tna_created', 'TNA Created'),
        ('material_planning', 'Material Planning'),
        ('production_running', 'Production Running'),
        ('quality_checking', 'Quality Checking'),
        ('ready_for_shipment', 'Ready For Shipment'),
        ('shipped', 'Shipped'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Order Status', default='draft', tracking=True, group_expand='_expand_states')

    is_locked = fields.Boolean(string='Locked', default=False, copy=False,
                                help='Set automatically on confirmation (SRS section 44). Quantity, price, '
                                     'delivery date and style changes then require an Order Revision.')
    locked_date = fields.Datetime(string='Locked On', readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Order Validation checkpoints (SRS section 16)
    # ------------------------------------------------------------------
    sample_approval_done = fields.Boolean(string='Sample Approval Completed')

    # ------------------------------------------------------------------
    # Material Requirement Planning / Availability (SRS 24-25)
    # ------------------------------------------------------------------
    fabric_consumption_per_pc = fields.Float(string='Fabric Consumption / Pc (KG)', digits=(16, 3))
    required_fabric_qty = fields.Float(string='Required Fabric (KG)', compute='_compute_required_fabric',
                                        store=True, digits=(16, 3),
                                        help='Order Quantity x BOM Consumption (SRS section 24).')
    material_status = fields.Selection([
        ('available', 'Available - Ready'),
        ('partial', 'Partial - Some Shortage'),
        ('shortage', 'Shortage - Purchase Required'),
        ('delayed', 'Delayed - Supplier Issue'),
    ], string='Material Status', default='shortage', tracking=True)
    available_stock_qty = fields.Float(string='Available Stock')
    reserved_stock_qty = fields.Float(string='Reserved Stock')
    incoming_purchase_qty = fields.Float(string='Incoming Purchase')
    shortage_qty = fields.Float(string='Shortage Quantity', compute='_compute_shortage', store=True)
    materials_planned = fields.Boolean(string='Materials Planned')

    # ------------------------------------------------------------------
    # Production Capacity Check (SRS section 26)
    # ------------------------------------------------------------------
    capacity_required_qty = fields.Integer(string='Capacity Required (pcs)')
    capacity_available_qty = fields.Integer(string='Capacity Available (pcs)')
    capacity_shortage_qty = fields.Integer(string='Capacity Shortage (pcs)', compute='_compute_capacity_shortage',
                                            store=True)
    production_capacity_available = fields.Boolean(string='Production Capacity Confirmed')

    # ------------------------------------------------------------------
    # Order Tracking / Progress (SRS sections 30-31)
    # ------------------------------------------------------------------
    material_progress = fields.Float(string='Material %', default=0.0)
    cutting_progress = fields.Float(string='Cutting %', default=0.0)
    sewing_progress = fields.Float(string='Sewing %', default=0.0)
    finishing_progress = fields.Float(string='Finishing %', default=0.0)
    inspection_progress = fields.Float(string='Inspection %', default=0.0)
    progress = fields.Float(string='Overall Progress (%)', compute='_compute_progress', store=True, tracking=True)

    # ------------------------------------------------------------------
    # Risk / AI Order Intelligence (SRS sections 18-19, 46-48)
    # ------------------------------------------------------------------
    risk_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], string='Risk Level', default='low', tracking=True)
    risk_score = fields.Float(string='Risk Score (%)', default=0.0)
    ai_risk_reason = fields.Text(string='AI Risk Reason', readonly=True)
    ai_recommendation = fields.Text(string='AI Recommendation', readonly=True)
    ai_predicted_shipment_date = fields.Date(string='AI Predicted Shipment Date', readonly=True)
    ai_delay_probability = fields.Float(string='AI Delay Probability (%)', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    # ==================================================================
    # Compute methods
    # ==================================================================
    @api.depends('line_ids.quantity', 'line_ids.total_value')
    def _compute_line_totals(self):
        for rec in self:
            rec.quantity = sum(rec.line_ids.mapped('quantity'))
            rec.order_value = sum(rec.line_ids.mapped('total_value'))

    @api.depends('quantity', 'shipment_ids.shipped_qty', 'shipment_ids.status')
    def _compute_shipment_totals(self):
        for rec in self:
            shipped = sum(rec.shipment_ids.filtered(lambda s: s.status == 'shipped').mapped('shipped_qty'))
            rec.shipped_qty = shipped
            rec.balance_qty = (rec.quantity or 0) - shipped

    @api.depends('line_ids', 'shipment_ids', 'allocation_ids', 'risk_ids', 'document_ids', 'revision_ids',
                 'delay_ids')
    def _compute_counts(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.shipment_count = len(rec.shipment_ids)
            rec.allocation_count = len(rec.allocation_ids)
            rec.risk_count = len(rec.risk_ids)
            rec.document_count = len(rec.document_ids)
            rec.revision_count = len(rec.revision_ids)
            rec.delay_count = len(rec.delay_ids)

    def _compute_style_linked_counts(self):
        for rec in self:
            if rec.style_id:
                rec.techpack_count = self.env['garment.techpack'].search_count(
                    [('style_id', '=', rec.style_id.id)])
                rec.sample_count = self.env['garment.sample'].search_count(
                    [('style_id', '=', rec.style_id.id)])
            else:
                rec.techpack_count = 0
                rec.sample_count = 0

    @api.depends('quantity', 'fabric_consumption_per_pc')
    def _compute_required_fabric(self):
        for rec in self:
            rec.required_fabric_qty = (rec.quantity or 0) * (rec.fabric_consumption_per_pc or 0.0)

    @api.depends('available_stock_qty', 'reserved_stock_qty', 'incoming_purchase_qty', 'required_fabric_qty')
    def _compute_shortage(self):
        for rec in self:
            usable = (rec.available_stock_qty or 0.0) - (rec.reserved_stock_qty or 0.0) \
                + (rec.incoming_purchase_qty or 0.0)
            rec.shortage_qty = max(0.0, (rec.required_fabric_qty or 0.0) - usable)

    @api.depends('capacity_required_qty', 'capacity_available_qty')
    def _compute_capacity_shortage(self):
        for rec in self:
            rec.capacity_shortage_qty = max(0, (rec.capacity_required_qty or 0) - (rec.capacity_available_qty or 0))

    @api.depends('material_progress', 'cutting_progress', 'sewing_progress', 'finishing_progress',
                 'inspection_progress')
    def _compute_progress(self):
        for rec in self:
            values = [rec.material_progress, rec.cutting_progress, rec.sewing_progress,
                      rec.finishing_progress, rec.inspection_progress]
            rec.progress = sum(values) / len(values) if values else 0.0

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['state'].selection]

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = '/my/orders/%s' % rec.id

    # ==================================================================
    # Onchange
    # ==================================================================
    @api.onchange('merch_order_confirmation_id')
    def _onchange_merch_order_confirmation_id(self):
        oc = self.merch_order_confirmation_id
        if oc:
            self.buyer_id = oc.buyer_id
            self.style_id = oc.style_id
            self.buyer_po_number = self.buyer_po_number or oc.buyer_po_number
            self.delivery_date = oc.delivery_date
            self.shipment_date = oc.shipment_date
            self.factory = oc.factory
            self.production_unit = oc.production_unit
            self.merchandiser_id = oc.merchandiser_id
            self.currency_id = oc.currency_id

    # ==================================================================
    # CRUD
    # ==================================================================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.order') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        is_manager = self.env.user.has_group('garment_order_management.group_order_manager')
        for rec in self:
            if rec.state == 'closed' and not is_manager:
                raise UserError(_('Order "%s" is Closed and is read-only (SRS section 43).') % rec.name)
            if rec.is_locked and not is_manager and any(f in _LOCKED_HEADER_FIELDS for f in vals.keys()):
                raise UserError(_(
                    'Order "%s" is locked after confirmation. Delivery/shipment date and style '
                    'changes require an Order Revision (SRS section 44).') % rec.name)
        return super().write(vals)

    # ==================================================================
    # Validation rules (SRS section 16)
    # ==================================================================
    def _check_confirmation_prerequisites(self):
        self.ensure_one()
        errors = []
        if not (self.costing_id and self.costing_id.status == 'approved'):
            errors.append(_('Approved costing is required.'))
        if not (self.bom_id and self.bom_id.status in ('production_approved', 'active')):
            errors.append(_('Approved BOM is required.'))
        if not self.buyer_po_number:
            errors.append(_('Buyer PO Number is required.'))
        if not self.delivery_date:
            errors.append(_('Delivery Date is required.'))
        if not self.sample_approval_done:
            errors.append(_('Sample approval must be completed.'))
        if not self.line_ids:
            errors.append(_('At least one Order Line (style/color/size/qty) is required.'))
        if errors:
            raise UserError(_('Order cannot be confirmed:\n- %s') % '\n- '.join(errors))

    def _check_production_release_prerequisites(self):
        self.ensure_one()
        errors = []
        if not (self.bom_id and self.bom_id.status in ('production_approved', 'active')):
            errors.append(_('BOM must be approved.'))
        if not (self.tna_id and self.tna_id.status in ('active', 'monitoring')):
            errors.append(_('An active TNA is required.'))
        if not self.materials_planned:
            errors.append(_('Materials must be planned.'))
        if not self.production_capacity_available:
            errors.append(_('Production capacity must be confirmed available.'))
        if errors:
            raise UserError(_('Order cannot be released to Production:\n- %s') % '\n- '.join(errors))

    def _check_size_breakdown(self):
        for rec in self:
            for line in rec.line_ids:
                if line.size_ids:
                    total = sum(line.size_ids.mapped('quantity'))
                    if total != line.quantity:
                        raise UserError(_(
                            'Order "%s": size breakdown for style "%s" totals %s pcs but the line quantity '
                            'is %s pcs.') % (rec.name, line.style_id.display_name, total, line.quantity))

    # ==================================================================
    # Status workflow actions (SRS section 7)
    # ==================================================================
    def action_receive_po(self):
        self.write({'state': 'po_received'})

    def action_confirm(self):
        for rec in self:
            rec._check_confirmation_prerequisites()
            rec._check_size_breakdown()
            rec.write({'state': 'confirmed', 'is_locked': True, 'locked_date': fields.Datetime.now()})
            rec._log_approval_stage('order_received')
            rec._log_approval_stage('management_approval')

    def action_mark_tna_created(self):
        for rec in self:
            if not rec.tna_id:
                raise UserError(_('Link a TNA Plan before marking TNA Created.'))
            rec.write({'state': 'tna_created'})

    def action_start_material_planning(self):
        self.write({'state': 'material_planning'})

    def action_release_to_production(self):
        for rec in self:
            rec._check_production_release_prerequisites()
            rec.write({'state': 'production_running'})
            rec.message_post(body=_(
                'Order released to Production. Style: %s | Qty: %s pcs | BOM: %s | Factory: %s. '
                'A Manufacturing/Production Order should now be raised in Production Management, '
                'linked back to this order.') % (
                rec.style_id.display_name or '-', rec.quantity, rec.bom_id.display_name or '-',
                rec.factory or '-'))

    def action_start_quality_checking(self):
        self.write({'state': 'quality_checking'})

    def action_ready_for_shipment(self):
        self.write({'state': 'ready_for_shipment'})

    def action_ship(self):
        for rec in self:
            if not rec.shipment_ids:
                raise UserError(_('Add at least one Shipment record before marking the order Shipped.'))
            rec.write({'state': 'shipped'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_close(self):
        self.write({'state': 'closed', 'is_locked': True, 'locked_date': fields.Datetime.now()})

    def action_cancel(self):
        for rec in self:
            if rec.state in ('shipped', 'completed', 'closed'):
                raise UserError(_('Order "%s" can no longer be cancelled (already %s).') % (
                    rec.name, rec.state))
            rec.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft', 'is_locked': False, 'locked_date': False})

    def action_lock_order(self):
        self.write({'is_locked': True, 'locked_date': fields.Datetime.now()})

    def action_unlock_order(self):
        self.write({'is_locked': False})

    def _log_approval_stage(self, stage):
        self.ensure_one()
        self.env['garment.order.approval'].create({
            'order_id': self.id, 'stage': stage, 'status': 'approved',
            'approver_id': self.env.user.id, 'date': fields.Date.context_today(self),
        })

    # ==================================================================
    # AI Order Intelligence (SRS sections 19, 46-48)
    # ==================================================================
    def action_run_ai_risk_prediction(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            score, level, reason, recommendation = ai_engine.predict_order_risk(rec)
            rec.write({
                'risk_score': score, 'risk_level': level.lower(),
                'ai_risk_reason': reason, 'ai_recommendation': recommendation,
                'ai_last_run': fields.Datetime.now(),
            })
            rec.env['garment.order.risk'].create({
                'order_id': rec.id, 'risk_category': 'production', 'risk_factor': 'AI Prediction',
                'risk_score': score, 'risk_level': level.lower(), 'source': 'ai',
                'reason': reason, 'recommendation': recommendation,
                'identified_date': fields.Date.context_today(rec),
            })
        return True

    def action_run_ai_delivery_prediction(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            predicted_date, delay_probability = ai_engine.predict_order_delivery(rec)
            rec.write({
                'ai_predicted_shipment_date': predicted_date, 'ai_delay_probability': delay_probability,
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    def action_run_ai_optimization(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            recommendation = ai_engine.optimize_order_allocation(rec)
            rec.write({'ai_recommendation': recommendation, 'ai_last_run': fields.Datetime.now()})
        return True

    # ==================================================================
    # Smart button actions
    # ==================================================================
    def action_view_lines(self):
        self.ensure_one()
        return {
            'name': _('Order Lines'), 'type': 'ir.actions.act_window', 'res_model': 'garment.order.line',
            'view_mode': 'tree,form', 'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }

    def action_view_shipments(self):
        self.ensure_one()
        return {
            'name': _('Shipments'), 'type': 'ir.actions.act_window', 'res_model': 'garment.order.shipment',
            'view_mode': 'tree,form', 'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }

    def action_view_allocations(self):
        self.ensure_one()
        return {
            'name': _('Factory Allocations'), 'type': 'ir.actions.act_window',
            'res_model': 'garment.order.allocation', 'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)], 'context': {'default_order_id': self.id},
        }

    def action_view_risks(self):
        self.ensure_one()
        return {
            'name': _('Risk Factors'), 'type': 'ir.actions.act_window', 'res_model': 'garment.order.risk',
            'view_mode': 'tree,form', 'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }

    def action_view_documents(self):
        self.ensure_one()
        return {
            'name': _('Document Checklist'), 'type': 'ir.actions.act_window',
            'res_model': 'garment.order.document', 'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)], 'context': {'default_order_id': self.id},
        }

    def action_view_revisions(self):
        self.ensure_one()
        return {
            'name': _('Revisions'), 'type': 'ir.actions.act_window', 'res_model': 'garment.order.revision',
            'view_mode': 'tree,form', 'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }

    def action_view_delays(self):
        self.ensure_one()
        return {
            'name': _('Delays'), 'type': 'ir.actions.act_window', 'res_model': 'garment.order.delay',
            'view_mode': 'tree,form', 'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }

    def action_view_techpacks(self):
        self.ensure_one()
        return {
            'name': _('Tech Packs'), 'type': 'ir.actions.act_window', 'res_model': 'garment.techpack',
            'view_mode': 'tree,form', 'domain': [('style_id', '=', self.style_id.id)],
        }

    def action_view_samples(self):
        self.ensure_one()
        return {
            'name': _('Samples'), 'type': 'ir.actions.act_window', 'res_model': 'garment.sample',
            'view_mode': 'tree,form', 'domain': [('style_id', '=', self.style_id.id)],
        }

    def action_create_revision(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('New Order Revision'),
            'res_model': 'garment.order.revision', 'view_mode': 'form', 'target': 'new',
            'context': {'default_order_id': self.id, 'default_requested_by_id': self.env.user.id,
                        'default_revision_number': len(self.revision_ids) + 1},
        }
