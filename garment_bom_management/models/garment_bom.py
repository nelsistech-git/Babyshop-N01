# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# BOM Status Workflow (SRS section 6) -> BOM Approval Workflow stage (SRS
# section 17) mapping. Not every status needs a matching approval-trail
# record (e.g. 'merchandising_approval' is a second merchandiser sign-off
# and does not open a new stage record).
STATUS_TO_APPROVAL_STAGE = {
    'material_review': 'merchandiser_review',
    'technical_approval': 'technical_team',
    'costing_approval': 'costing_team',
    'production_approved': 'production_team',
    'active': 'final_approval',
}


class GarmentBom(models.Model):
    """BOM Master (SRS sections 5-7) — garment.bom. Connects Style → Tech
    Pack → BOM → Costing → Purchase Planning → Inventory → Production →
    Accounting."""
    _name = 'garment.bom'
    _description = 'Garment Bill of Materials'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'bom_number'

    bom_number = fields.Char(string='BOM Number', copy=False, readonly=True, default=lambda s: _('New'))
    barcode = fields.Char(string='Barcode', copy=False,
                          help='Scannable barcode for this BOM (SRS 42 Barcode & RFID Integration).')
    bom_type = fields.Selection([
        ('production', 'Production BOM'), ('sample', 'Sample BOM'), ('costing', 'Costing BOM'),
        ('buyer', 'Buyer BOM'), ('production_floor', 'Production Floor BOM'),
    ], string='BOM Type', default='production', required=True, tracking=True)

    # General Information
    style_id = fields.Many2one('garment.style', string='Style', required=True, tracking=True)
    buyer_id = fields.Many2one('garment.buyer', string='Buyer', related='style_id.buyer_id', store=True)
    brand = fields.Char(related='style_id.brand', string='Brand', store=True)
    season = fields.Char(related='style_id.season', string='Season', store=True)
    collection = fields.Char(related='style_id.collection', string='Collection', store=True)
    style_category_id = fields.Many2one('garment.style.category', related='style_id.style_category_id',
                                        string='Product Category', store=True)
    product_type = fields.Char(string='Product Type')
    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack Reference',
                                  domain="[('style_id', '=', style_id)]")
    version = fields.Char(string='Version', default='1.0')
    revision_number = fields.Integer(string='Revision Number', default=0)
    created_by_id = fields.Many2one('res.users', string='Created By', default=lambda s: s.env.user)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True)

    # Product Information (header)
    style_color_id = fields.Many2one('garment.style.color', string='Colorway',
                                     domain="[('style_id', '=', style_id)]")
    size_set_id = fields.Many2one('garment.size.set', string='Size Range')
    order_quantity = fields.Integer(string='Order Quantity', default=1)
    delivery_date = fields.Date(string='Delivery Date')
    factory = fields.Char(string='Factory')
    production_unit = fields.Char(string='Production Unit')

    # Commercial Information
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)
    target_cost = fields.Monetary(string='Target Cost', currency_field='currency_id')
    fob_price = fields.Monetary(string='FOB Price', currency_field='currency_id')
    profit_margin = fields.Float(string='Profit Margin (%)')

    # Status Workflow (SRS section 6)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('material_review', 'Material Review'),
        ('technical_approval', 'Technical Approval'),
        ('merchandising_approval', 'Merchandising Approval'),
        ('costing_approval', 'Costing Approval'),
        ('production_approved', 'Production Approved'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')
    is_locked = fields.Boolean(string='Locked (Approved)', default=False, copy=False)

    # Relations
    line_ids = fields.One2many('garment.bom.line', 'bom_id', string='Consolidated Material Lines',
                               help='Auto-synced from Fabric/Trim/Packaging BOM — this is the list read by '
                                    'Production Material Issue and Purchase Requirement Planning.')
    fabric_bom_ids = fields.One2many('garment.fabric.bom', 'bom_id', string='Fabric BOM')
    trim_bom_ids = fields.One2many('garment.trim.bom', 'bom_id', string='Trim BOM')
    packaging_bom_ids = fields.One2many('garment.packaging.bom', 'bom_id', string='Packaging BOM')
    consumption_ids = fields.One2many('garment.material.consumption', 'bom_id', string='Size/Color Consumption')
    alternative_ids = fields.One2many('garment.material.alternative', 'bom_id', string='Alternative Materials')
    supplier_ids = fields.One2many('garment.bom.supplier', 'bom_id', string='Supplier Mapping')
    approval_ids = fields.One2many('garment.bom.approval', 'bom_id', string='Approvals')
    revision_ids = fields.One2many('garment.bom.revision', 'bom_id', string='Revisions')
    reservation_ids = fields.One2many('garment.material.reservation', 'bom_id', string='Material Reservations')

    # Cost Summary (SRS section 20)
    fabric_cost_total = fields.Monetary(string='Fabric Cost', compute='_compute_cost_summary', store=True,
                                        currency_field='currency_id')
    trim_cost_total = fields.Monetary(string='Trim Cost', compute='_compute_cost_summary', store=True,
                                      currency_field='currency_id')
    packaging_cost_total = fields.Monetary(string='Packaging Cost', compute='_compute_cost_summary', store=True,
                                           currency_field='currency_id')
    processing_cost = fields.Monetary(string='Processing Cost', currency_field='currency_id')
    total_material_cost = fields.Monetary(string='Total Material Cost', compute='_compute_cost_summary', store=True,
                                          currency_field='currency_id')
    cost_per_piece = fields.Monetary(string='Cost Per Piece', compute='_compute_cost_summary', store=True,
                                     currency_field='currency_id')

    # BOM Cost Variance Management (SRS section 40)
    actual_material_cost = fields.Monetary(string='Actual Material Cost (Per Piece)', currency_field='currency_id',
                                           copy=False,
                                           help='Actual production consumption cost per piece, entered manually '
                                                'or pulled from Production Cost via "Compute Cost Variance".')
    cost_variance = fields.Monetary(string='Cost Variance', compute='_compute_cost_variance', store=True,
                                    currency_field='currency_id')
    material_variance = fields.Monetary(string='Material Variance', currency_field='currency_id', copy=False)
    consumption_variance = fields.Monetary(string='Consumption Variance', currency_field='currency_id', copy=False)
    price_variance = fields.Monetary(string='Price Variance', currency_field='currency_id', copy=False)
    wastage_variance = fields.Monetary(string='Wastage Variance', currency_field='currency_id', copy=False)

    # Material Reservation / Availability (SRS section 27)
    material_availability_pct = fields.Float(string='Material Availability %',
                                             compute='_compute_material_availability', store=True)

    # AI Assist
    ai_suggested_note = fields.Text(string='AI BOM Suggestion', readonly=True)
    ai_consumption_note = fields.Text(string='AI Consumption Prediction', readonly=True)
    ai_cost_optimization_note = fields.Text(string='AI Cost Optimization', readonly=True)
    ai_risk_note = fields.Text(string='AI Risk Detection', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('bom_number_uniq', 'unique(bom_number, company_id)', 'BOM Number must be unique per company!'),
    ]

    @api.depends('fabric_bom_ids.line_cost', 'trim_bom_ids.line_cost', 'packaging_bom_ids.line_cost',
                 'processing_cost', 'order_quantity')
    def _compute_cost_summary(self):
        for rec in self:
            rec.fabric_cost_total = sum(rec.fabric_bom_ids.mapped('line_cost'))
            rec.trim_cost_total = sum(rec.trim_bom_ids.mapped('line_cost'))
            rec.packaging_cost_total = sum(rec.packaging_bom_ids.mapped('line_cost'))
            rec.total_material_cost = (rec.fabric_cost_total + rec.trim_cost_total
                                       + rec.packaging_cost_total + (rec.processing_cost or 0.0))
            rec.cost_per_piece = (rec.total_material_cost / rec.order_quantity) if rec.order_quantity else 0.0

    @api.depends('actual_material_cost', 'cost_per_piece')
    def _compute_cost_variance(self):
        for rec in self:
            rec.cost_variance = (rec.actual_material_cost or 0.0) - (rec.cost_per_piece or 0.0)

    @api.depends('reservation_ids.available_qty', 'reservation_ids.required_qty')
    def _compute_material_availability(self):
        for rec in self:
            required = sum(rec.reservation_ids.mapped('required_qty'))
            available = sum(rec.reservation_ids.mapped('available_qty'))
            rec.material_availability_pct = (available / required * 100.0) if required else 100.0

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        # FIXED: Set barcode in vals BEFORE calling super().create() to avoid triggering write() on locked records
        for vals in vals_list:
            if vals.get('bom_number', _('New')) == _('New'):
                vals['bom_number'] = self.env['ir.sequence'].next_by_code('garment.bom') or _('New')

            if not vals.get('barcode') and vals.get('bom_number'):
                vals['barcode'] = vals['bom_number']

        return super().create(vals_list)

    def write(self, vals):
        # FIXED: Allow certain internal/system fields to be updated even if the BOM is locked
        safe_fields = {'status', 'is_locked', 'approved_by_id', 'barcode', 'message_follower_ids', 'message_ids',
                       'activity_ids'}

        for rec in self:
            if rec.is_locked and not self.env.user.has_group('garment_bom_management.group_bom_administrator') \
                    and any(f not in safe_fields for f in vals.keys()):
                raise UserError(_('BOM "%s" is locked (Approved). Raise a BOM Revision to modify it.') % rec.bom_number)

        old_cost = {rec.id: rec.cost_per_piece for rec in self} if 'processing_cost' in vals else {}
        res = super().write(vals)

        # Notification System (SRS 45): alert on a material cost increase.
        for rec in self:
            if rec.id in old_cost and old_cost[rec.id] and rec.cost_per_piece > old_cost[rec.id] * 1.05:
                rec.message_post(body=_('Cost per piece increased from %.2f to %.2f (+%.1f%%).') % (
                    old_cost[rec.id], rec.cost_per_piece,
                    (rec.cost_per_piece - old_cost[rec.id]) / old_cost[rec.id] * 100.0))
        return res

    # ------------------------------------------------------------------
    # BOM Status Workflow (SRS section 6) + BOM Approval Workflow (SRS 17)
    # ------------------------------------------------------------------
    def _create_or_get_approval_stage(self, stage):
        self.ensure_one()
        existing = self.approval_ids.filtered(lambda a: a.approval_stage == stage)
        if existing:
            return existing[0]
        return self.env['garment.bom.approval'].create({'bom_id': self.id, 'approval_stage': stage})

    def _advance_status(self, status):
        stage = STATUS_TO_APPROVAL_STAGE.get(status)
        for rec in self:
            rec.status = status
            if stage:
                rec._create_or_get_approval_stage(stage)
            rec.message_post(body=_('BOM moved to status: %s') % dict(rec._fields['status'].selection).get(status))

    def action_submit_material_review(self):
        self._advance_status('material_review')

    def action_submit_technical_approval(self):
        self._advance_status('technical_approval')

    def action_submit_merchandising_approval(self):
        self._advance_status('merchandising_approval')

    def action_submit_costing_approval(self):
        self._advance_status('costing_approval')

    def action_submit_production_approved(self):
        self.action_sync_material_lines()
        self._advance_status('production_approved')

    def action_approve_final(self):
        self.action_sync_material_lines()
        for rec in self:
            rec._create_or_get_approval_stage('final_approval').action_approve()
        self.write({'status': 'active', 'is_locked': True, 'approved_by_id': self.env.user.id})

    def action_close(self):
        self.write({'status': 'closed'})

    # ------------------------------------------------------------------
    # Consolidated Material Lines (SRS section 8 / 25 Manufacturing
    # Integration / MODEL_MAP: garment_production links to garment.bom.line
    # for material issue) — kept in sync with the category-specific BOMs.
    # ------------------------------------------------------------------
    def action_sync_material_lines(self):
        for rec in self:
            rec.line_ids.unlink()
            vals = []
            for f in rec.fabric_bom_ids:
                vals.append((0, 0, {
                    'material_category': 'fabric',
                    'material_code': f.fabric_code or f.buyer_material_code or '',
                    'material_name': f.fabric_name or dict(f._fields['fabric_role'].selection).get(f.fabric_role, ''),
                    'description': f.composition,
                    'specification': f.gsm and ('GSM %s' % f.gsm) or '',
                    'uom': f.uom,
                    'required_qty': f.required_qty,
                    'unit_price': f.unit_price,
                    'supplier_id': f.supplier_id.id,
                    'buyer_material_code': f.buyer_material_code,
                    'source_ref': 'garment.fabric.bom,%s' % f.id,
                }))
            for t in rec.trim_bom_ids:
                vals.append((0, 0, {
                    'material_category': 'trim',
                    'material_code': t.buyer_material_code or '',
                    'material_name': dict(t._fields['trim_type'].selection).get(t.trim_type, ''),
                    'description': t.description,
                    'specification': t.size_spec,
                    'uom': t.uom,
                    'required_qty': t.required_qty,
                    'unit_price': t.unit_price,
                    'supplier_id': t.supplier_id.id,
                    'buyer_material_code': t.buyer_material_code,
                    'source_ref': 'garment.trim.bom,%s' % t.id,
                }))
            for p in rec.packaging_bom_ids:
                vals.append((0, 0, {
                    'material_category': 'packaging',
                    'material_code': p.buyer_material_code or '',
                    'material_name': dict(p._fields['packaging_type'].selection).get(p.packaging_type, ''),
                    'description': p.description,
                    'specification': p.dimension,
                    'uom': p.uom,
                    'required_qty': p.required_qty,
                    'unit_price': p.unit_price,
                    'supplier_id': p.supplier_id.id,
                    'buyer_material_code': p.buyer_material_code,
                    'source_ref': 'garment.packaging.bom,%s' % p.id,
                }))
            rec.line_ids = vals
        return True

    # ------------------------------------------------------------------
    # Purchase Requirement (SRS section 23)
    # ------------------------------------------------------------------
    def action_generate_purchase_requirement(self):
        """Summarize which material lines still need purchasing
        (Purchase Qty = Requirement - Available Stock - Incoming Stock),
        and post it to the chatter. Actual PO creation is out of this
        module's scope (no hard 'purchase' dependency) — see
        IMPLEMENTATION_NOTES.md."""
        for rec in self:
            lines = []
            for source in (rec.fabric_bom_ids, rec.trim_bom_ids, rec.packaging_bom_ids):
                for line in source:
                    if line.purchase_qty > 0:
                        name = getattr(line, 'fabric_name', None) or getattr(line, 'description',
                                                                             None) or line.display_name
                        lines.append('- %s: purchase %.2f %s' % (name, line.purchase_qty, line.uom or ''))
            if lines:
                rec.message_post(body=_('Purchase Requirement:\n%s') % '\n'.join(lines))
            else:
                rec.message_post(
                    body=_('Purchase Requirement: no shortage — all materials covered by available/incoming stock.'))
        return True

    # ------------------------------------------------------------------
    # BOM Cost Variance (SRS section 40)
    # ------------------------------------------------------------------
    def action_compute_cost_variance(self):
        ProductionOrder = self.env.get('garment.production.order')
        ProductionCost = self.env.get('garment.production.cost')
        for rec in self:
            actual = rec.actual_material_cost
            if ProductionOrder is not None and ProductionCost is not None and 'bom_id' in ProductionOrder._fields:
                orders = ProductionOrder.sudo().search([('bom_id', '=', rec.id)])
                if orders:
                    costs = ProductionCost.sudo().search([('production_order_id', 'in', orders.ids)])
                    if costs:
                        total_qty = sum(orders.mapped(
                            'order_quantity')) if 'order_quantity' in ProductionOrder._fields else rec.order_quantity
                        total_material = sum(costs.mapped('material_cost'))
                        actual = (total_material / total_qty) if total_qty else actual
            rec.actual_material_cost = actual
            rec.price_variance = (actual or 0.0) - (rec.cost_per_piece or 0.0)
            rec.material_variance = rec.price_variance
            # consumption_variance / wastage_variance stay manually editable: a true
            # auto-derivation needs actual per-line consumption data (garment.production.consumption),
            # which this module does not hard-depend on — see IMPLEMENTATION_NOTES.md.
        return True

    # ------------------------------------------------------------------
    # Automatic BOM Creation (SRS 37.1 / 19)
    # ------------------------------------------------------------------
    def action_import_from_style(self):
        """Populate an initial Fabric/Trim BOM from the linked Style's fabric
        and trim specification lines (SRS 'AI Automatic BOM Creation' seed
        data, made deterministic/copy-based rather than AI-generated)."""
        for rec in self:
            Fabric = self.env['garment.fabric.bom']
            for fl in rec.style_id.fabric_line_ids:
                Fabric.create({
                    'bom_id': rec.id, 'fabric_role': fl.fabric_role, 'composition': fl.composition,
                    'gsm': fl.gsm, 'width': fl.width, 'supplier_id': fl.supplier_id.id,
                    'mill': fl.mill, 'country_of_origin_id': fl.country_of_origin_id.id,
                })
            Trim = self.env['garment.trim.bom']
            for tl in rec.style_id.trim_line_ids:
                Trim.create({
                    'bom_id': rec.id, 'trim_type': tl.trim_type, 'description': tl.description,
                    'supplier_id': tl.supplier_id.id, 'color': tl.color,
                })
        return True

    def action_import_from_techpack(self):
        """Populate Trim (Label) and Packaging BOM lines from the linked
        Tech Pack's Label/Packaging specifications (SRS 37.1)."""
        for rec in self:
            if not rec.techpack_id:
                raise UserError(_('Set a Tech Pack Reference first.'))
            Trim = self.env['garment.trim.bom']
            for label in rec.techpack_id.label_spec_ids:
                Trim.create({
                    'bom_id': rec.id, 'trim_type': 'label',
                    'description': label.label_code or dict(label._fields['label_type'].selection).get(label.label_type,
                                                                                                       ''),
                    'color': label.color, 'size_spec': label.size,
                    'label_type': dict(label._fields['label_type'].selection).get(label.label_type, ''),
                    'label_material': label.material,
                    'label_position': label.position,
                    'supplier_id': label.supplier_id.id,
                })
            Packaging = self.env['garment.packaging.bom']
            spec = rec.techpack_id.packaging_spec_ids[:1]
            if spec:
                spec = spec[0]
                if spec.poly_bag_type:
                    Packaging.create({'bom_id': rec.id, 'packaging_type': 'poly_bag',
                                      'description': spec.poly_bag_type, 'dimension': spec.poly_bag_size})
                if spec.carton_type:
                    Packaging.create({'bom_id': rec.id, 'packaging_type': 'master_carton',
                                      'description': spec.carton_type, 'dimension': spec.carton_dimension})
                if spec.hanger_requirement:
                    Packaging.create({'bom_id': rec.id, 'packaging_type': 'hanger', 'description': 'Hanger'})
                if spec.tissue_requirement:
                    Packaging.create({'bom_id': rec.id, 'packaging_type': 'tissue', 'description': 'Tissue Paper'})
                if spec.barcode_requirement:
                    Packaging.create({'bom_id': rec.id, 'packaging_type': 'barcode', 'description': 'Barcode Sticker'})
        return True

    def action_run_ai_analysis(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            suggestion = ai_engine.suggest_bom_from_style(rec)
            consumption_note = ai_engine.predict_bom_consumption(rec)
            cost_note = ai_engine.suggest_bom_cost_optimization(rec)
            risk_note = ai_engine.suggest_bom_risk_detection(rec)
            rec.write({
                'ai_suggested_note': suggestion,
                'ai_consumption_note': consumption_note,
                'ai_cost_optimization_note': cost_note,
                'ai_risk_note': risk_note,
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    def action_view_approvals(self):
        self.ensure_one()
        return {'name': _('Approvals'), 'type': 'ir.actions.act_window', 'res_model': 'garment.bom.approval',
                'view_mode': 'tree,form', 'domain': [('bom_id', '=', self.id)],
                'context': {'default_bom_id': self.id}}

    def action_view_revisions(self):
        self.ensure_one()
        return {'name': _('Revisions'), 'type': 'ir.actions.act_window', 'res_model': 'garment.bom.revision',
                'view_mode': 'tree,form', 'domain': [('bom_id', '=', self.id)],
                'context': {'default_bom_id': self.id}}

    def action_view_reservations(self):
        self.ensure_one()
        return {'name': _('Material Reservations'), 'type': 'ir.actions.act_window',
                'res_model': 'garment.material.reservation', 'view_mode': 'tree,form',
                'domain': [('bom_id', '=', self.id)],
                'context': {'default_bom_id': self.id, 'default_style_id': self.style_id.id}}

    def action_view_production_orders(self):
        """Smart button — soft cross-module lookup, since garment_production
        depends on this module and not the other way round."""
        self.ensure_one()
        ProductionOrder = self.env.get('garment.production.order')
        if ProductionOrder is None:
            raise UserError(_('The Production module is not installed.'))
        return {'name': _('Production Orders'), 'type': 'ir.actions.act_window',
                'res_model': 'garment.production.order', 'view_mode': 'tree,form',
                'domain': [('bom_id', '=', self.id)]}

    def action_open_compare_wizard(self):
        self.ensure_one()
        return {'name': _('Compare BOM Versions'), 'type': 'ir.actions.act_window',
                'res_model': 'garment.bom.compare.wizard', 'view_mode': 'form', 'target': 'new',
                'context': {'default_bom_id_1': self.id}}