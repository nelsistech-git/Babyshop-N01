# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentPurchaseOrder(models.Model):
    """Purchase Order (SRS sections 19-20) — garment.purchase.order.
    Approval tier is determined by total value against the dedicated
    Purchase Approval Matrix thresholds (SRS section 42), which supersede
    the smaller illustrative numbers used in the section 19 example —
    see IMPLEMENTATION_NOTES.md."""
    _name = 'garment.purchase.order'
    _description = 'Garment Purchase Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'order_date desc'

    po_number = fields.Char(string='PO Number', copy=False, readonly=True, default=lambda s: _('New'))
    requisition_id = fields.Many2one('garment.purchase.requisition', string='Purchase Requisition')
    rfq_id = fields.Many2one('garment.purchase.rfq', string='RFQ Reference')
    contract_id = fields.Many2one('garment.purchase.contract', string='Contract / Blanket Agreement')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True, tracking=True)
    style_id = fields.Many2one('garment.style', string='Style')
    order_date = fields.Date(string='Order Date', default=fields.Date.context_today)
    delivery_date = fields.Date(string='Delivery Date')
    terms_conditions = fields.Text(string='Terms & Conditions')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterms')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    # Local / Import Purchase Management (SRS sections 27-29, 52)
    purchase_type = fields.Selection([
        ('local', 'Local Purchase'), ('import', 'Import Purchase'),
    ], string='Purchase Type', default='local', required=True, tracking=True)
    # Local Purchase Data (SRS section 27)
    vat_percentage = fields.Float(string='VAT (%)')
    vat_amount = fields.Monetary(string='VAT Amount', compute='_compute_vat_amount', store=True,
                                  currency_field='currency_id')
    delivery_location = fields.Char(string='Delivery Location')
    # Import Purchase Information (SRS sections 28-29, 52)
    pi_number = fields.Char(string='Proforma Invoice Number')
    supplier_country_id = fields.Many2one('res.country', string='Supplier Country')
    lc_number = fields.Char(string='LC Number')
    bank_name = fields.Char(string='Bank')
    shipment_date = fields.Date(string='Shipment Date')
    eta_date = fields.Date(string='ETA')
    port_of_entry = fields.Char(string='Port')
    freight_cost = fields.Monetary(string='Freight Cost', currency_field='currency_id')
    insurance_cost = fields.Monetary(string='Insurance Cost', currency_field='currency_id')
    cf_charges = fields.Monetary(string='C&F Charges', currency_field='currency_id')
    landed_cost = fields.Monetary(string='Landed Cost', compute='_compute_landed_cost', store=True,
                                   currency_field='currency_id',
                                   help='Total Value + Freight + Insurance + C&F Charges.')
    import_stage = fields.Selection([
        ('pi_received', 'PI Received'), ('lc_opening', 'LC Opening'), ('shipment', 'Shipment'),
        ('customs_clearance', 'Customs Clearance'), ('warehouse_receipt', 'Warehouse Receipt'),
    ], string='Import Stage', help='Import Purchase Workflow (SRS section 28).')

    line_ids = fields.One2many('garment.purchase.order.line', 'order_id', string='Order Lines')
    total_value = fields.Monetary(string='Total Value', compute='_compute_total_value', store=True,
                                   currency_field='currency_id')
    approval_tier = fields.Selection([
        ('purchase_manager', 'Purchase Manager (< 50,000 BDT)'),
        ('director', 'Director (50,000 - 5 Lakh BDT)'),
        ('finance_director', 'Finance + Director (5 - 20 Lakh BDT)'),
        ('managing_director', 'Managing Director (> 20 Lakh BDT)'),
    ], string='Approval Tier', compute='_compute_approval_tier', store=True)

    delivery_ids = fields.One2many('garment.purchase.delivery', 'order_id', string='Deliveries')
    approval_ids = fields.One2many('garment.purchase.approval', 'order_id', string='Approvals')
    delivery_count = fields.Integer(compute='_compute_counts')

    # Purchase Exception Management (SRS section 43)
    exception_type = fields.Selection([
        ('price_increase', 'Price Exceeds Previous Purchase'), ('delivery_delay', 'Delivery Delay'),
        ('supplier_unavailable', 'Supplier Unavailable'), ('quantity_variation', 'Quantity Variation'),
        ('budget_exceeded', 'Budget Exceeded'),
    ], string='Exception Type', tracking=True)
    exception_note = fields.Text(string='Exception Note')
    requires_exception_approval = fields.Boolean(string='Requires Exception Approval', default=False, tracking=True)

    # Purchase Budget Control (SRS section 44) — a self-contained check since
    # garment_purchase cannot depend on garment_finance's garment.budget
    # without creating a dependency cycle (garment_finance already depends on
    # garment_supplier, which depends on garment_purchase). See notes.
    department_budget_amount = fields.Monetary(string='Department Budget (Period)', currency_field='currency_id')
    budget_status = fields.Selection([
        ('within_budget', 'Within Budget'), ('exceeded', 'Exceeded'), ('not_set', 'Not Set'),
    ], string='Budget Status', compute='_compute_budget_status', store=True)

    # Purchase Invoice Matching (SRS section 35): three-way match of
    # Purchase Order + Goods Receipt + Supplier Invoice.
    invoice_ids = fields.Many2many('account.move', 'garment_purchase_order_account_move_rel', 'order_id',
                                    'move_id', string='Supplier Invoices',
                                    domain=[('move_type', '=', 'in_invoice')])
    invoiced_amount = fields.Monetary(string='Invoiced Amount', compute='_compute_invoiced_amount', store=True,
                                       currency_field='currency_id')
    received_qty_total = fields.Float(string='Total Received Quantity', compute='_compute_invoiced_amount',
                                       store=True)
    match_status = fields.Selection([
        ('pending_grn', 'Pending Goods Receipt'), ('pending_invoice', 'Pending Invoice'),
        ('matched', 'Matched'), ('mismatch', 'Mismatch'),
    ], string='3-Way Match Status', compute='_compute_invoiced_amount', store=True)

    # Supplier RFQ Portal Integration (SRS section 15): supplier can confirm the PO online.
    supplier_confirmed = fields.Boolean(string='Confirmed by Supplier', default=False, copy=False)
    supplier_confirmation_date = fields.Datetime(string='Supplier Confirmation Date', copy=False)

    status = fields.Selection([
        ('draft', 'Draft'), ('pending_approval', 'Pending Approval'), ('approved', 'Approved'),
        ('sent', 'Sent to Supplier'), ('partially_received', 'Partially Received'),
        ('received', 'Fully Received'), ('closed', 'Closed'), ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('line_ids.line_total')
    def _compute_total_value(self):
        for rec in self:
            rec.total_value = sum(rec.line_ids.mapped('line_total'))

    @api.depends('total_value')
    def _compute_approval_tier(self):
        # Purchase Approval Matrix thresholds (SRS section 42, BDT):
        # <50,000 Purchase Manager | 50,000-5 Lakh Director |
        # 5-20 Lakh Finance+Director | >20 Lakh Managing Director.
        for rec in self:
            if rec.total_value > 2000000:
                rec.approval_tier = 'managing_director'
            elif rec.total_value > 500000:
                rec.approval_tier = 'finance_director'
            elif rec.total_value > 50000:
                rec.approval_tier = 'director'
            else:
                rec.approval_tier = 'purchase_manager'

    @api.depends('vat_percentage', 'total_value')
    def _compute_vat_amount(self):
        for rec in self:
            rec.vat_amount = (rec.total_value or 0.0) * (rec.vat_percentage or 0.0) / 100.0

    @api.depends('total_value', 'freight_cost', 'insurance_cost', 'cf_charges')
    def _compute_landed_cost(self):
        for rec in self:
            rec.landed_cost = (rec.total_value or 0.0) + (rec.freight_cost or 0.0) + \
                (rec.insurance_cost or 0.0) + (rec.cf_charges or 0.0)

    @api.depends('department_budget_amount', 'total_value')
    def _compute_budget_status(self):
        for rec in self:
            if not rec.department_budget_amount:
                rec.budget_status = 'not_set'
            elif rec.total_value > rec.department_budget_amount:
                rec.budget_status = 'exceeded'
            else:
                rec.budget_status = 'within_budget'

    @api.depends('invoice_ids.amount_total', 'invoice_ids.state', 'delivery_ids.delivered_qty', 'line_ids.quantity',
                 'total_value')
    def _compute_invoiced_amount(self):
        for rec in self:
            posted_invoices = rec.invoice_ids.filtered(lambda m: m.state == 'posted')
            rec.invoiced_amount = sum(posted_invoices.mapped('amount_total'))
            rec.received_qty_total = sum(rec.delivery_ids.mapped('delivered_qty'))
            ordered_qty = sum(rec.line_ids.mapped('quantity'))
            if not rec.received_qty_total:
                rec.match_status = 'pending_grn'
            elif not rec.invoiced_amount:
                rec.match_status = 'pending_invoice'
            elif rec.received_qty_total < ordered_qty or abs(rec.invoiced_amount - rec.total_value) > 0.01:
                rec.match_status = 'mismatch'
            else:
                rec.match_status = 'matched'

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.depends('delivery_ids')
    def _compute_counts(self):
        for rec in self:
            rec.delivery_count = len(rec.delivery_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('po_number', _('New')) == _('New'):
                vals['po_number'] = self.env['ir.sequence'].next_by_code('garment.purchase.order') or _('New')
        return super().create(vals_list)

    def action_create_from_quotation(self, quotation):
        """Create a PO line set from a selected supplier quotation."""
        self.ensure_one()
        self.env['garment.purchase.order.line'].create({
            'order_id': self.id,
            'material_name': quotation.material_name,
            'quantity': quotation.rfq_id.quantity,
            'uom': quotation.rfq_id.uom,
            'unit_price': quotation.price,
        })

    def action_submit_for_approval(self):
        self.action_check_exceptions()
        self.action_generate_approvals()
        self.write({'status': 'pending_approval'})

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_send_to_supplier(self):
        self.write({'status': 'sent'})

    def action_view_deliveries(self):
        self.ensure_one()
        return {'name': _('Deliveries'), 'type': 'ir.actions.act_window', 'res_model': 'garment.purchase.delivery',
                'view_mode': 'tree,form', 'domain': [('order_id', '=', self.id)],
                'context': {'default_order_id': self.id}}

    def action_generate_approvals(self):
        """Create the approval chain implied by the Purchase Approval
        Matrix tier (SRS section 42) — the "Finance + Director" tier
        raises two parallel approval records."""
        Approval = self.env['garment.purchase.approval']
        tier_levels = {
            'purchase_manager': ['purchase_manager'],
            'director': ['director'],
            'finance_director': ['finance', 'director'],
            'managing_director': ['managing_director'],
        }
        for rec in self:
            if rec.approval_ids:
                continue
            for seq, level in enumerate(tier_levels.get(rec.approval_tier, []), start=1):
                Approval.create({
                    'order_id': rec.id, 'sequence': seq * 10, 'approval_level': level,
                })
        return True

    def action_check_exceptions(self):
        """Purchase Exception Management (SRS section 43): flags a price
        increase versus the last purchase of the same material from the
        same supplier, and a budget-exceeded condition."""
        for rec in self:
            exceptions = []
            for line in rec.line_ids:
                if line.previous_price and line.unit_price > line.previous_price * 1.10:
                    exceptions.append(_('Fabric/material price increased: "%(material)s" previous %(prev).2f, '
                                         'current %(cur).2f.') % {
                        'material': line.material_name, 'prev': line.previous_price, 'cur': line.unit_price})
            if rec.budget_status == 'exceeded':
                exceptions.append(_('Purchase value %(total).2f exceeds department budget %(budget).2f.') % {
                    'total': rec.total_value, 'budget': rec.department_budget_amount})
            if exceptions:
                rec.exception_type = 'budget_exceeded' if rec.budget_status == 'exceeded' else 'price_increase'
                rec.exception_note = '\n'.join(exceptions)
                rec.requires_exception_approval = True
                rec.message_post(body=_('<b>Purchase Exception Detected</b><br/>%s') % '<br/>'.join(exceptions))
            else:
                rec.requires_exception_approval = False
        return True

    def action_verify_invoice_match(self):
        """Purchase Invoice Matching (SRS section 35): recompute the
        three-way match (PO + Goods Receipt + Supplier Invoice)."""
        self._compute_invoiced_amount()
        return True

    def action_supplier_confirm(self):
        """Supplier RFQ/PO Portal Integration (SRS section 15): supplier
        confirms the PO online."""
        self.write({'supplier_confirmed': True, 'supplier_confirmation_date': fields.Datetime.now()})
        return True
