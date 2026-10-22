# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Material Master (SRS sections 7-8) — garment.material. Introduces the
canonical item master that BOM, Purchase and Sample have so far
referenced only as free text (material_name / material_reference Char
fields). Those earlier modules are not retrofitted today, but this
model is the natural foundation for that in a future iteration.
"""
from datetime import date

from odoo import api, fields, models, _


class GarmentMaterial(models.Model):
    _name = 'garment.material'
    _description = 'Garment Material Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    material_code = fields.Char(string='Item Code', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Item Name', required=True, tracking=True)
    category = fields.Selection([
        ('fabric', 'Fabric'), ('yarn', 'Yarn'), ('accessories', 'Accessories'), ('chemical', 'Chemical'),
        ('spare_parts', 'Spare Parts'), ('finished_goods', 'Finished Goods'), ('packaging', 'Packaging'),
    ], string='Category', required=True, tracking=True)
    uom = fields.Char(string='Unit', required=True)
    specification = fields.Char(string='Specification')
    supplier_id = fields.Many2one('res.partner', string='Preferred Supplier')
    default_warehouse_id = fields.Many2one('garment.warehouse', string='Default Warehouse')

    minimum_stock = fields.Float(string='Minimum Stock')
    maximum_stock = fields.Float(string='Maximum Stock')
    reorder_level = fields.Float(string='Reorder Level')
    valuation_method = fields.Selection([
        ('fifo', 'FIFO'), ('average_cost', 'Average Cost'), ('standard_cost', 'Standard Cost'),
    ], string='Valuation Method', default='average_cost')
    standard_cost = fields.Monetary(string='Standard/Average Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    move_ids = fields.One2many('garment.stock.move', 'material_id', string='Stock Moves')
    on_hand_qty = fields.Float(string='On-Hand Quantity', compute='_compute_quantities', store=True)
    reserved_qty = fields.Float(string='Reserved Quantity', compute='_compute_quantities', store=True)
    available_qty = fields.Float(string='Available Quantity', compute='_compute_quantities', store=True)
    inventory_value = fields.Monetary(string='Inventory Value', compute='_compute_quantities', store=True,
                                       currency_field='currency_id')
    stock_status = fields.Selection([
        ('normal', 'Normal'), ('low_stock', 'Low Stock'), ('excess_stock', 'Excess Stock'), ('out_of_stock', 'Out of Stock'),
    ], string='Stock Status', compute='_compute_quantities', store=True)
    last_movement_date = fields.Date(string='Last Movement Date', compute='_compute_quantities', store=True)

    ai_reorder_note = fields.Text(string='AI Reorder Suggestion', readonly=True)
    ai_slow_moving_note = fields.Text(string='AI Slow-Moving Analysis', readonly=True)
    ai_last_run = fields.Datetime(string='AI Last Analyzed', readonly=True)

    # Cycle Counting / ABC Classification (SRS section 33 "Cycle Counting").
    abc_classification = fields.Selection([
        ('a', 'A - High Value (Count Frequently)'),
        ('b', 'B - Medium Value'),
        ('c', 'C - Low Value'),
    ], string='ABC Classification', tracking=True, copy=False)

    # Stock Aging / Slow-Moving / Dead Stock analysis (SRS: Stock Aging
    # Report, Slow Moving Inventory Management, AI Dead Stock Detection).
    stock_age_days = fields.Integer(string='Stock Age (Days)', compute='_compute_aging', store=True)
    aging_bucket = fields.Selection([
        ('0_30', '0-30 Days'), ('31_90', '31-90 Days'), ('90_plus', '90+ Days'),
    ], string='Aging Bucket', compute='_compute_aging', store=True)
    is_slow_moving = fields.Boolean(string='Slow Moving (90+ Days Idle)', compute='_compute_aging', store=True)
    is_dead_stock = fields.Boolean(string='Dead Stock (240+ Days Idle)', compute='_compute_aging', store=True)

    # Batch/Lot & Chemical Safety fields (SRS sections 15-16 "Chemical Store
    # Management" / "Chemical Safety Control", section 34 "Batch & Lot
    # Tracking"). Kept on the material master for non-fabric categories;
    # fabric already tracks batch/expiry at the roll level.
    batch_number = fields.Char(string='Batch Number')
    expiry_date = fields.Date(string='Expiry Date')
    expiry_alert = fields.Boolean(string='Expiry Risk (<=30 Days)', compute='_compute_expiry_alert', store=True)
    hazard_category = fields.Selection([
        ('none', 'None'), ('flammable', 'Flammable'), ('corrosive', 'Corrosive'),
        ('toxic', 'Toxic'), ('other', 'Other'),
    ], string='Hazard Category', default='none')
    storage_condition = fields.Char(string='Storage Requirement', help='e.g. temperature/humidity requirement.')

    # Accessories fields (SRS: Accessories Inventory Information / Bangladesh
    # Accessories Store Requirements — Color Matching, Buyer Approval).
    color = fields.Char(string='Color')
    size = fields.Char(string='Size')
    buyer_approval_status = fields.Selection([
        ('not_required', 'Not Required'), ('pending', 'Pending Buyer Approval'),
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Buyer Approval Status', default='not_required')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('material_code_uniq', 'unique(material_code, company_id)', 'Item Code must be unique per company!'),
    ]

    @api.depends('move_ids.quantity', 'move_ids.move_type', 'move_ids.state')
    def _compute_quantities(self):
        in_types = ('receipt', 'return', 'adjustment_in')
        out_types = ('issue', 'transfer_out', 'adjustment_out')
        for rec in self:
            done_moves = rec.move_ids.filtered(lambda m: m.state == 'done')
            on_hand = sum(m.quantity for m in done_moves if m.move_type in in_types)
            on_hand -= sum(m.quantity for m in done_moves if m.move_type in out_types)
            reserved = sum(m.quantity for m in done_moves if m.move_type == 'reservation')
            rec.on_hand_qty = on_hand
            rec.reserved_qty = reserved
            rec.available_qty = on_hand - reserved
            rec.inventory_value = on_hand * (rec.standard_cost or 0.0)
            if on_hand <= 0:
                rec.stock_status = 'out_of_stock'
            elif rec.minimum_stock and on_hand < rec.minimum_stock:
                rec.stock_status = 'low_stock'
            elif rec.maximum_stock and on_hand > rec.maximum_stock:
                rec.stock_status = 'excess_stock'
            else:
                rec.stock_status = 'normal'
            last_move = done_moves.sorted('move_date', reverse=True)[:1]
            rec.last_movement_date = last_move.move_date if last_move else False

    @api.depends('last_movement_date')
    def _compute_aging(self):
        today = date.today()
        for rec in self:
            age = (today - rec.last_movement_date).days if rec.last_movement_date else 0
            rec.stock_age_days = age
            rec.is_slow_moving = age >= 90
            rec.is_dead_stock = age >= 240
            if age <= 30:
                rec.aging_bucket = '0_30'
            elif age <= 90:
                rec.aging_bucket = '31_90'
            else:
                rec.aging_bucket = '90_plus'

    @api.depends('expiry_date')
    def _compute_expiry_alert(self):
        today = date.today()
        for rec in self:
            rec.expiry_alert = bool(rec.expiry_date and (rec.expiry_date - today).days <= 30)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('material_code', _('New')) == _('New'):
                vals['material_code'] = self.env['ir.sequence'].next_by_code('garment.material') or _('New')
        return super().create(vals_list)

    def action_run_ai_analysis(self):
        ai_engine = self.env['garment.ai.engine']
        for rec in self:
            reorder_note = ai_engine.suggest_material_reorder(rec)
            slow_note = ai_engine.detect_slow_moving_material(rec)
            rec.write({
                'ai_reorder_note': reorder_note,
                'ai_slow_moving_note': slow_note,
                'ai_last_run': fields.Datetime.now(),
            })
        return True

    def action_classify_abc(self):
        """ABC Classification (SRS section 33 "Cycle Counting"): ranks every
        material in the company by inventory value — top 20% of items = A
        (count frequently), next 30% = B, remainder = C."""
        materials = self.env['garment.material'].search(
            [('company_id', '=', self.env.company.id)], order='inventory_value desc')
        total = len(materials)
        if not total:
            return True
        a_cut = max(1, int(round(total * 0.2)))
        b_cut = max(a_cut, int(round(total * 0.5)))
        for idx, mat in enumerate(materials):
            if idx < a_cut:
                mat.abc_classification = 'a'
            elif idx < b_cut:
                mat.abc_classification = 'b'
            else:
                mat.abc_classification = 'c'
        return True

    def action_create_purchase_requisition(self):
        """Low Stock / Reorder Level Alert (SRS section 53 "Low Stock Alert
        -> Create Purchase Suggestion"). Raises a Purchase Requisition
        (garment_purchase) pre-filled from this material's shortage."""
        Requisition = self.env['garment.purchase.requisition']
        Line = self.env['garment.purchase.request.line']
        category_map = {
            'fabric': 'fabric', 'yarn': 'fabric', 'accessories': 'trim',
            'packaging': 'packaging',
        }
        requisitions = self.env['garment.purchase.requisition']
        for rec in self:
            target = rec.reorder_level or rec.minimum_stock or 0.0
            shortage = max(0.0, target - rec.available_qty)
            req = Requisition.create({
                'source': 'manual',
                'request_department': 'Warehouse',
                'priority': 'critical' if rec.stock_status == 'out_of_stock' else 'high',
                'required_for_order': _('Reorder - %s') % (rec.material_code or rec.name),
            })
            Line.create({
                'requisition_id': req.id,
                'material_category': category_map.get(rec.category, 'other'),
                'material_name': rec.name,
                'specification': rec.specification,
                'color': rec.color,
                'uom': rec.uom,
                'required_qty': shortage or target or 1.0,
                'available_stock': rec.available_qty,
                'supplier_id': rec.supplier_id.id,
            })
            requisitions |= req
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Requisitions'),
            'res_model': 'garment.purchase.requisition',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', requisitions.ids)],
        }

    def _cron_daily_warehouse_alerts(self):
        """Scheduled action (Low Stock Alert / Expiry Alert / Dead Stock
        Alert, SRS section 53 "Inventory Workflow Automation"). Refreshes
        the stored aging fields (they depend on today's date, not just on
        last_movement_date) and schedules a To-Do activity for the
        Warehouse Manager group on every material that newly needs review,
        skipping materials that already carry an open activity of the same
        kind to avoid daily duplicate noise.
        """
        materials = self.search([])
        materials._compute_aging()
        manager_group = self.env.ref('garment_warehouse.group_warehouse_manager', raise_if_not_found=False)
        user = (manager_group.users[:1] if manager_group and manager_group.users else self.env.user)
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return True

        def _needs_activity(mat, summary):
            # Odoo removes an activity from activity_ids once it is marked
            # done, so any remaining match here is still open.
            return not mat.activity_ids.filtered(lambda a: a.summary == summary)

        for mat in materials.filtered(lambda m: m.stock_status in ('low_stock', 'out_of_stock')):
            summary = _('Low Stock Alert: %s') % mat.name
            if _needs_activity(mat, summary):
                mat.activity_schedule(
                    'mail.mail_activity_data_todo', summary=summary,
                    note=_('On-hand %.2f %s is below minimum stock %.2f — raise a purchase requisition.') % (
                        mat.on_hand_qty, mat.uom, mat.minimum_stock),
                    user_id=user.id)
        for mat in materials.filtered('expiry_alert'):
            summary = _('Expiry Alert: %s') % mat.name
            if _needs_activity(mat, summary):
                mat.activity_schedule(
                    'mail.mail_activity_data_todo', summary=summary,
                    note=_('Expires on %s (within 30 days).') % mat.expiry_date, user_id=user.id)
        for mat in materials.filtered('is_dead_stock'):
            summary = _('Dead Stock Alert: %s') % mat.name
            if _needs_activity(mat, summary):
                mat.activity_schedule(
                    'mail.mail_activity_data_todo', summary=summary,
                    note=_('No movement in %d+ days — review for alternate use or clearance.') % mat.stock_age_days,
                    user_id=user.id)
        return True
