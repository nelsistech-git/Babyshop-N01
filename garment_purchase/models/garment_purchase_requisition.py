# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentPurchaseRequisition(models.Model):
    """Purchase Requisition (SRS sections 7-12) — garment.purchase.requisition."""
    _name = 'garment.purchase.requisition'
    _description = 'Garment Purchase Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    pr_number = fields.Char(string='PR Number', copy=False, readonly=True, default=lambda s: _('New'))
    source = fields.Selection([
        ('bom', 'BOM'), ('production_order', 'Production Order'), ('planning', 'Planning Department'),
        ('manual', 'Manual Request'), ('maintenance', 'Maintenance Department'),
    ], string='PR Source', default='manual', required=True)
    bom_id = fields.Many2one('garment.bom', string='BOM Reference')
    style_id = fields.Many2one('garment.style', string='Style')
    order_id = fields.Many2one('garment.order', string='Related Order',
                                help='Garment Order this material requirement traces back to '
                                     '(SRS section 48 database relationship: Order -> Material '
                                     'Requirement -> Purchase Requisition).')
    material_type = fields.Selection([
        ('fabric', 'Fabric'), ('trim', 'Trim/Accessory'), ('packaging', 'Packaging'), ('other', 'Other'),
    ], string='Material Type', help='Header-level material type (SRS section 49 model example). '
                                     'Individual lines may still mix categories.')
    request_department = fields.Char(string='Request Department',
                                      help='Free-text department label — kept for backward compatibility '
                                           'with callers such as garment_maintenance spare-part reorders. '
                                           'Use department_id for a real link where available.')
    department_id = fields.Many2one('garment.hr.department', string='Requesting Department')
    requested_by_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user)
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)
    required_date = fields.Date(string='Required Date')
    required_for_order = fields.Char(string='Required For Order')
    priority = fields.Selection([
        ('critical', 'Critical (Production Stopping Risk)'), ('high', 'High (Within 7 Days)'),
        ('medium', 'Medium (Within 15 Days)'), ('low', 'Low (Future Requirement)'),
    ], string='Priority', default='medium', tracking=True)

    line_ids = fields.One2many('garment.purchase.request.line', 'requisition_id', string='Requisition Lines')
    rfq_ids = fields.One2many('garment.purchase.rfq', 'requisition_id', string='RFQs')
    rfq_count = fields.Integer(compute='_compute_counts')
    line_count = fields.Integer(compute='_compute_counts')
    has_shortage = fields.Boolean(string='Has Material Shortage', compute='_compute_has_shortage', store=True,
                                   help='True when any line has a positive Purchase Required Quantity '
                                        '(SRS section 11 Material Shortage Alert).')

    status = fields.Selection([
        ('draft', 'Draft'), ('department_approval', 'Department Manager Approval'),
        ('purchase_review', 'Purchase Manager Review'), ('finance_approval', 'Finance Approval'),
        ('rfq_generated', 'RFQ Generated'), ('closed', 'Closed'), ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('rfq_ids', 'line_ids')
    def _compute_counts(self):
        for rec in self:
            rec.rfq_count = len(rec.rfq_ids)
            rec.line_count = len(rec.line_ids)

    @api.depends('line_ids.shortage_qty')
    def _compute_has_shortage(self):
        for rec in self:
            rec.has_shortage = any(line.shortage_qty > 0 for line in rec.line_ids)

    def _expand_states(self, states, domain):
        return [key for key, _val in self._fields['status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('pr_number', _('New')) == _('New'):
                vals['pr_number'] = self.env['ir.sequence'].next_by_code('garment.purchase.requisition') or _('New')
        return super().create(vals_list)

    def action_import_from_bom(self):
        """Material Requirement Planning (SRS section 10):
        Purchase Required = Required Material - Available Stock - Incoming Stock."""
        Line = self.env['garment.purchase.request.line']
        for rec in self:
            if not rec.bom_id:
                continue
            for fabric in rec.bom_id.fabric_bom_ids:
                Line.create({
                    'requisition_id': rec.id, 'material_category': 'fabric',
                    'material_name': dict(fabric._fields['fabric_role'].selection).get(fabric.fabric_role, ''),
                    'composition': fabric.composition, 'gsm': fabric.gsm, 'width': fabric.width,
                    'uom': fabric.uom, 'required_qty': fabric.required_qty, 'supplier_id': fabric.supplier_id.id,
                })
            for trim in rec.bom_id.trim_bom_ids:
                Line.create({
                    'requisition_id': rec.id, 'material_category': 'trim',
                    'material_name': dict(trim._fields['trim_type'].selection).get(trim.trim_type, ''),
                    'color': trim.color, 'uom': trim.uom, 'required_qty': trim.required_qty,
                    'supplier_id': trim.supplier_id.id,
                })
            for pack in rec.bom_id.packaging_bom_ids:
                Line.create({
                    'requisition_id': rec.id, 'material_category': 'packaging',
                    'material_name': dict(pack._fields['packaging_type'].selection).get(pack.packaging_type, ''),
                    'uom': pack.uom, 'required_qty': pack.required_qty, 'supplier_id': pack.supplier_id.id,
                })
        self.action_check_shortage_alerts()
        return True

    def action_generate_rfq(self):
        """Automatic RFQ Creation from an approved PR (SRS section 14)."""
        Rfq = self.env['garment.purchase.rfq']
        for rec in self:
            for line in rec.line_ids:
                Rfq.create({
                    'requisition_id': rec.id,
                    'requisition_line_id': line.id,
                    'supplier_id': line.supplier_id.id,
                    'material_name': line.material_name,
                    'specification': line.specification,
                    'quantity': line.required_qty,
                    'delivery_date': rec.required_date,
                })
            rec.write({'status': 'rfq_generated'})
        return True

    def action_view_rfqs(self):
        self.ensure_one()
        return {'name': _('RFQs'), 'type': 'ir.actions.act_window', 'res_model': 'garment.purchase.rfq',
                'view_mode': 'tree,form', 'domain': [('requisition_id', '=', self.id)],
                'context': {'default_requisition_id': self.id}}

    def action_check_shortage_alerts(self):
        """Material Shortage Alert (SRS section 11): post a chatter alert
        for every line whose Purchase Required Quantity is positive, in
        the exact Order/Material/Required/Available/Shortage shape the
        SRS example uses."""
        for rec in self:
            shortage_lines = rec.line_ids.filtered(lambda l: l.shortage_qty > 0)
            if not shortage_lines:
                continue
            body_lines = [_('<b>Material Shortage Alert</b>')]
            for line in shortage_lines:
                body_lines.append(_(
                    '%(material)s — Required: %(required).2f %(uom)s | Available: %(available).2f %(uom)s '
                    '| Shortage: %(shortage).2f %(uom)s'
                ) % {
                    'material': line.material_name, 'required': line.required_qty,
                    'available': line.available_stock, 'shortage': line.shortage_qty, 'uom': line.uom or '',
                })
            rec.message_post(body='<br/>'.join(body_lines))
        return True
