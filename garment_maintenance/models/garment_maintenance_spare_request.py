# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Spare Parts Purchase Request / Reorder (Maintenance & Asset Mgmt SRS
sec. 25, CMMS SRS sec. 26-27): "Stock Below Minimum -> Purchase Request
-> Approval -> Supplier Order -> Receive Parts" / "Technician Request ->
Maintenance Manager Approval -> Store Issue -> Usage Update -> Cost
Update". The spare part master is the shared ``garment.material``
(garment_warehouse); on approval this model raises a REAL
``garment.purchase.requisition`` (garment_purchase, whose ``source``
selection already includes a 'maintenance' option) instead of
re-implementing procurement. See IMPLEMENTATION_NOTES.md.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarmentMaintenanceSpareRequest(models.Model):
    _name = 'garment.maintenance.spare.request'
    _description = 'Garment Maintenance Spare Parts Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'

    name = fields.Char(string='Request No.', copy=False, readonly=True, default=lambda s: _('New'))
    material_id = fields.Many2one('garment.material', string='Spare Part', required=True,
                                   domain=[('category', '=', 'spare_parts')], tracking=True)
    workorder_id = fields.Many2one('garment.maintenance.workorder', string='Work Order')
    requested_qty = fields.Float(string='Requested Quantity', required=True, default=1.0)
    current_stock = fields.Float(string='Current Stock', related='material_id.on_hand_qty')
    minimum_stock = fields.Float(string='Minimum Stock', related='material_id.minimum_stock')
    reason = fields.Selection([
        ('below_minimum', 'Stock Below Minimum'),
        ('workorder_shortage', 'Work Order Shortage'),
        ('planned_pm', 'Planned Preventive Maintenance'),
    ], string='Reason', default='below_minimum', required=True)

    requested_by_id = fields.Many2one('garment.hr.employee', string='Requested By',
                                       domain=[('is_maintenance_technician', '=', True)])
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By (Store/Manager)')
    approval_date = fields.Datetime(string='Approval Date')

    requisition_id = fields.Many2one('garment.purchase.requisition', string='Purchase Requisition', copy=False,
                                      readonly=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('po_requested', 'Purchase Requisition Raised'),
        ('issued', 'Issued from Stock'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.maintenance.spare.request') or _('New')
        return super().create(vals_list)

    def action_approve(self):
        self.write({
            'status': 'approved',
            'approved_by_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })

    def action_reject(self):
        self.write({'status': 'rejected'})

    def action_issue_from_stock(self):
        """Store Officer directly issues from existing stock (no purchase needed)."""
        for rec in self:
            if rec.status != 'approved':
                raise UserError(_('Only an approved request can be issued.'))
            warehouse = rec.material_id.default_warehouse_id
            if warehouse:
                self.env['garment.stock.move'].create({
                    'material_id': rec.material_id.id,
                    'warehouse_id': warehouse.id,
                    'move_type': 'issue',
                    'quantity': rec.requested_qty,
                    'order_reference': rec.workorder_id.name or rec.name,
                    'reference': _('Spare request %s') % rec.name,
                })
            rec.status = 'issued'

    def action_create_purchase_requisition(self):
        """Raise a real Purchase Requisition (garment_purchase) — the
        automatic reorder workflow — instead of a duplicate PO model."""
        Requisition = self.env['garment.purchase.requisition']
        for rec in self:
            if rec.status != 'approved':
                raise UserError(_('Only an approved request can be sent to Purchase.'))
            requisition = Requisition.create({
                'source': 'maintenance',
                'request_department': 'Maintenance',
                'requested_by_id': self.env.user.id,
                'priority': 'high' if rec.reason == 'below_minimum' else 'medium',
                'line_ids': [(0, 0, {
                    'material_category': 'other',
                    'material_name': rec.material_id.name,
                    'specification': rec.material_id.specification,
                    'uom': rec.material_id.uom,
                    'required_qty': rec.requested_qty,
                    'available_stock': rec.material_id.on_hand_qty,
                    'supplier_id': rec.material_id.supplier_id.id,
                })],
            })
            rec.write({'requisition_id': requisition.id, 'status': 'po_requested'})
        return True
