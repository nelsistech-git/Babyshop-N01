# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Stock Movement (SRS section 20 DB design) — garment.stock.move. The
single ledger every quantity figure in this module is derived from.
Material Reservation (SRS section 17) and Production Material Issue /
Return (SRS sections 18-19) are implemented as move_type values here
rather than as separate models, since the official 8-model DB design
table does not list them separately.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Move types that represent a stock correction rather than a routine
# receipt/issue and therefore require Warehouse Manager approval before they
# count towards on-hand quantity (SRS "Inventory Approval Rules": Stock
# Adjustment, Material Return, Stock Transfer all require approval).
APPROVAL_REQUIRED_MOVE_TYPES = ('adjustment_in', 'adjustment_out', 'return', 'transfer_in', 'transfer_out')


class GarmentStockMove(models.Model):
    _name = 'garment.stock.move'
    _description = 'Garment Stock Movement'
    _inherit = ['mail.thread']
    _order = 'move_date desc, id desc'

    move_number = fields.Char(string='Move Number', copy=False, readonly=True, default=lambda s: _('New'))
    material_id = fields.Many2one('garment.material', string='Material', required=True, tracking=True)
    warehouse_id = fields.Many2one('garment.warehouse', string='Warehouse', required=True)
    location_id = fields.Many2one('garment.location', string='Location', domain="[('warehouse_id', '=', warehouse_id)]",
                                   tracking=True)
    move_type = fields.Selection([
        ('receipt', 'Receipt (GRN)'), ('issue', 'Production Issue'), ('return', 'Production Return'),
        ('transfer_in', 'Transfer In'), ('transfer_out', 'Transfer Out'),
        ('adjustment_in', 'Adjustment In'), ('adjustment_out', 'Adjustment Out'),
        ('reservation', 'Reservation'),
    ], string='Move Type', required=True, tracking=True)
    quantity = fields.Float(string='Quantity', required=True, tracking=True)
    move_date = fields.Date(string='Move Date', default=fields.Date.context_today, required=True)

    # Production Issue context (SRS section 18)
    issue_department = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('finishing', 'Finishing'),
    ], string='Issue Department')
    order_reference = fields.Char(string='Order Reference',
                                   help='Free-text reference until the Production Order module is installed.')
    bom_id = fields.Many2one('garment.bom', string='BOM Reference')

    # Return context (SRS section 19)
    return_condition = fields.Selection([
        ('good', 'Good'), ('damaged', 'Damaged'),
    ], string='Return Condition')

    # Transfer context (SRS section 31 "Stock Transfer Management" / section
    # 29 "Internal Stock Transfer" — Source Location, Destination Location).
    destination_warehouse_id = fields.Many2one('garment.warehouse', string='Destination Warehouse')
    destination_location_id = fields.Many2one(
        'garment.location', string='Destination Location',
        domain="[('warehouse_id', '=', destination_warehouse_id)]",
        help='Informational for a transfer_out move — the paired transfer_in move at the '
             'destination is what actually posts the quantity there. Use the "New Stock '
             'Transfer" wizard to create both moves together.')

    # Adjustment context (SRS section 32-33 "Inventory Adjustment").
    adjustment_reason = fields.Selection([
        ('damage', 'Damage'), ('loss', 'Loss / Missing Stock'), ('counting_error', 'Counting Error'),
        ('wrong_entry', 'Wrong Entry'), ('system_correction', 'System Correction'), ('other', 'Other'),
    ], string='Adjustment/Return Reason')

    fabric_roll_id = fields.Many2one('garment.fabric.roll', string='Fabric Roll')
    reference = fields.Char(string='Reference')
    remarks = fields.Char(string='Remarks')
    created_by_id = fields.Many2one('res.users', string='Created By', default=lambda s: s.env.user)

    state = fields.Selection([
        ('draft', 'Draft'), ('done', 'Done'), ('cancelled', 'Cancelled'),
    ], string='Status', default='done', tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False, tracking=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('move_number', _('New')) == _('New'):
                vals['move_number'] = self.env['ir.sequence'].next_by_code('garment.stock.move') or _('New')
            # Adjustment / Return / Transfer moves require Warehouse Manager
            # approval before they affect on-hand quantity, unless created
            # by an already-approved workflow (e.g. Stock Count approval).
            if vals.get('move_type') in APPROVAL_REQUIRED_MOVE_TYPES and \
                    not self.env.context.get('skip_adjustment_approval'):
                vals['state'] = 'draft'
                vals.pop('approved_by_id', None)
        return super().create(vals_list)

    def action_approve_movement(self):
        """Warehouse Manager approval for Adjustment/Return/Transfer moves
        (SRS section 42 "Inventory Approval Rules")."""
        if not self.env.user.has_group('garment_warehouse.group_warehouse_manager'):
            raise UserError(_('Only a Warehouse Manager can approve this stock movement.'))
        for rec in self:
            if rec.move_type not in APPROVAL_REQUIRED_MOVE_TYPES:
                raise UserError(_('This movement type does not require approval.'))
            if rec.state != 'draft':
                continue
            rec.write({'state': 'done', 'approved_by_id': self.env.user.id})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
