# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentShipment(models.Model):
    """Shipment Master (SRS sections 7-9, 49) — garment.shipment. Air and
    Courier Shipment Management (SRS sections 31-32) are folded in as
    mode-conditional fields rather than separate models, matching the
    SRS's own 10-model DB design table."""
    _name = 'garment.shipment'
    _description = 'Garment Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'shipment_date desc'

    shipment_no = fields.Char(string='Shipment Number', copy=False, readonly=True, default=lambda s: _('New'))
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', required=True, tracking=True)
    order_confirmation_id = fields.Many2one('garment.merch.order.confirmation', string='Export Order')
    style_id = fields.Many2one('garment.style', string='Style')
    invoice_reference = fields.Char(string='Invoice Reference')
    quantity = fields.Integer(string='Quantity (PCS)')
    shipment_date = fields.Date(string='Shipment Date', required=True, tracking=True)
    destination = fields.Char(string='Destination', required=True)
    mode = fields.Selection([
        ('sea', 'Sea'), ('air', 'Air'), ('road', 'Road'), ('courier', 'Courier'),
    ], string='Mode of Transport', default='sea', required=True, tracking=True)

    status = fields.Selection([
        ('planning', 'Shipment Planning'), ('allocation', 'Allocation'), ('booking', 'Container Booking'),
        ('loading', 'Loading'), ('port', 'Port'), ('vessel_departed', 'Vessel Departed'),
        ('in_transit', 'In Transit'), ('delivered', 'Buyer Delivery'),
    ], string='Status', default='planning', tracking=True, group_expand='_expand_states')

    forwarder_id = fields.Many2one('garment.forwarder', string='Freight Forwarder')
    shipping_line_id = fields.Many2one('garment.shipping.line', string='Shipping Line')

    # Air Shipment fields (SRS section 31)
    airline = fields.Char(string='Airline')
    awb_number = fields.Char(string='AWB Number')
    flight_number = fields.Char(string='Flight Number')
    air_weight_kg = fields.Float(string='Weight (KG)')

    # Courier Shipment fields (SRS section 32)
    courier_company = fields.Char(string='Courier Company')
    courier_tracking_number = fields.Char(string='Courier Tracking Number')
    courier_pickup_date = fields.Date(string='Courier Pickup Date')

    allocation_ids = fields.One2many('garment.shipment.allocation', 'shipment_id', string='Allocations')
    container_ids = fields.One2many('garment.container', 'shipment_id', string='Containers')
    freight_ids = fields.One2many('garment.freight', 'shipment_id', string='Freight Costs')
    bl_ids = fields.One2many('garment.bill.lading', 'shipment_id', string='Bills of Lading')
    document_ids = fields.One2many('garment.shipment.document', 'shipment_id', string='Documents')
    trip_ids = fields.One2many('garment.transport.trip', 'shipment_id', string='Transport Trips')

    allocation_count = fields.Integer(compute='_compute_counts')
    container_count = fields.Integer(compute='_compute_counts')
    total_freight_cost = fields.Monetary(string='Total Freight Cost', compute='_compute_counts',
                                          currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    ai_delay_risk_note = fields.Text(string='AI Delay Risk', readonly=True)
    # AI Freight Cost Prediction + AI Route Optimization (SRS sections 37, 39)
    ai_freight_prediction_note = fields.Text(string='AI Freight Cost Prediction', readonly=True)
    ai_route_optimization_note = fields.Text(string='AI Route Optimization', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    # Delivery Completion Automation (SRS section 52)
    is_closed = fields.Boolean(string='Closed', copy=False, tracking=True)
    closed_date = fields.Datetime(string='Closed On', copy=False, readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('shipment_no_uniq', 'unique(shipment_no, company_id)', 'Shipment Number must be unique per company!'),
    ]

    @api.depends('allocation_ids', 'container_ids', 'freight_ids.total_cost')
    def _compute_counts(self):
        for rec in self:
            rec.allocation_count = len(rec.allocation_ids)
            rec.container_count = len(rec.container_ids)
            rec.total_freight_cost = sum(rec.freight_ids.mapped('total_cost'))

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('shipment_no', _('New')) == _('New'):
                vals['shipment_no'] = self.env['ir.sequence'].next_by_code('garment.shipment') or _('New')
        records = super().create(vals_list)
        for rec in records:
            # Buyer Shipment Portal / Buyer Notification System (SRS sections
            # 34-35): follow the buyer's partner so portal + email
            # notifications reach them on every message_post milestone.
            if rec.buyer_id.partner_id:
                rec.message_subscribe(partner_ids=rec.buyer_id.partner_id.ids)
        return records

    def action_run_ai_analysis(self):
        """AI Logistics Optimization (SRS sections 37-40): delay prediction,
        freight cost prediction and route optimization in one pass."""
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            rec.write({
                'ai_delay_risk_note': ai_engine.predict_shipment_delay(rec),
                'ai_freight_prediction_note': ai_engine.predict_freight_cost(rec),
                'ai_route_optimization_note': ai_engine.suggest_route_optimization(rec),
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    def action_view_containers(self):
        self.ensure_one()
        return {'name': _('Containers'), 'type': 'ir.actions.act_window', 'res_model': 'garment.container',
                'view_mode': 'tree,form', 'domain': [('shipment_id', '=', self.id)],
                'context': {'default_shipment_id': self.id}}

    def action_confirm_shipment_ready(self):
        """Shipment Allocation -> Container Booking handover (SRS section 9
        'Ready' status + section 52 automation): moves the shipment from
        Allocation into Container Booking once every allocation line is
        fully allocated, and notifies followers ('Shipment Ready')."""
        for rec in self:
            if rec.status != 'allocation':
                continue
            pending = rec.allocation_ids.filtered(lambda a: a.status != 'ready')
            if pending:
                raise UserError(_('%d allocation line(s) are not yet Ready — allocate the full '
                                   'required quantity before confirming.') % len(pending))
            rec.status = 'booking'
            rec.message_post(body=_('Shipment Ready: all allocations are complete, shipment moved to '
                                     'Container Booking.'))
        return True

    def action_generate_container_requirement(self):
        """Container Booking Automation (SRS section 52): Shipment Created ->
        Container Requirement Generated -> Booking Request Sent ->
        Confirmation Received -> Container Assigned. Generates draft
        (Booked) container placeholders sized from the total allocated
        carton quantity, one per ~700 cartons (an average 40 HC carton
        load), so the shipment coordinator has a starting booking request
        instead of creating containers from scratch."""
        Container = self.env['garment.container']
        for rec in self:
            total_cartons = sum(rec.allocation_ids.mapped('carton_qty'))
            if not total_cartons:
                raise UserError(_('No carton quantity allocated yet — allocate the shipment first.'))
            existing = len(rec.container_ids)
            required = max(1, -(-total_cartons // 700))  # ceil division
            to_create = required - existing
            for i in range(to_create):
                Container.create({
                    'shipment_id': rec.id,
                    'container_no': _('DRAFT-%s-%d') % (rec.shipment_no or 'NEW', existing + i + 1),
                    'size': '40hc',
                    'shipping_line_id': rec.shipping_line_id.id,
                    'status': 'booked',
                })
            if to_create > 0:
                rec.message_post(body=_('Container Requirement Generated: %d container(s) auto-created '
                                         '(booking request) for %d cartons.') % (to_create, total_cartons))
        return True

    def _check_delivery_completion(self):
        """Delivery Completion Automation (SRS section 52): Container
        Delivered -> Update Shipment Status -> Notify Buyer -> Close
        Shipment. Called from garment.container.action_next_status()."""
        for rec in self:
            if rec.is_closed or not rec.container_ids:
                continue
            if all(c.status == 'delivered' for c in rec.container_ids):
                rec.write({'status': 'delivered', 'is_closed': True, 'closed_date': fields.Datetime.now()})
                rec.message_post(body=_('Delivery Completed: all containers delivered — shipment closed '
                                         'and buyer notified.'))

    def _cron_check_logistics_alerts(self):
        """Logistics Alert System (SRS section 19): Shipment Delay Alert and
        Document Missing Alert, raised as scheduled mail.activity records on
        the responsible user (or the shipment's creator as fallback). Skips
        raising a duplicate activity if one with the same summary is still
        open on the shipment."""
        ai_engine = self.env['garment.ai.engine']
        open_shipments = self.search([('is_closed', '=', False), ('status', '!=', 'delivered')])
        for rec in open_shipments:
            note = ai_engine.predict_shipment_delay(rec)
            rec.ai_delay_risk_note = note
            responsible_id = rec.create_uid.id or self.env.user.id

            delay_summary = _('Shipment Delay Alert: %s') % rec.shipment_no
            if note.startswith('Delay Risk: HIGH') and not rec.activity_ids.filtered(
                    lambda a: a.summary == delay_summary):
                rec.activity_schedule('mail.mail_activity_data_todo', summary=delay_summary,
                                       note=note, user_id=responsible_id)

            required_docs = ['bill_of_lading', 'freight_invoice'] if rec.mode == 'sea' else ['airway_bill']
            have_docs = set(rec.document_ids.mapped('document_type'))
            missing = [d for d in required_docs if d not in have_docs]
            doc_summary = _('Document Missing Alert: %s') % rec.shipment_no
            if missing and not rec.activity_ids.filtered(lambda a: a.summary == doc_summary):
                rec.activity_schedule('mail.mail_activity_data_todo', summary=doc_summary,
                                       note=_('Required document(s) still pending: %s') % ', '.join(missing),
                                       user_id=responsible_id)
        return True
