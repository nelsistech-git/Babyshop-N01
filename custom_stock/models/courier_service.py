from odoo import models, fields, api,_
from odoo.addons.helper import validator
from datetime import date
from odoo.exceptions import UserError


class CourierService(models.Model):
    _name = "courier.service"
    _description = "Courier Service"
    _rec_name = 'vendor_id'

    picking_id = fields.Many2one('stock.picking', required=True, ondelete='cascade', string='Delivery')
    move_id = fields.Many2one('account.move', readonly=True, ondelete='cascade', string='Invoice/Bill')
    vendor_id = fields.Many2one('res.partner', string='Vendor', domain=[('is_courier', '=', True)])
    product_id = fields.Many2one('product.product', string='Product', domain=[('type', '=', 'service')])
    courier_product_id = fields.Many2one('courier.mapping.line', string='Product')
    slip_serial = fields.Char(string='Slip Serial')
    booking_office = fields.Char(string='Booking Office')
    destination = fields.Char(string='Destination Address')
    scanned_copy = fields.Many2many('ir.attachment', 'scan_copys_ids', string='Scan Copy', help="Attach files here")
    amount = fields.Float(string='Amount', default=0, related='courier_product_id.amount', readonly=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved')
    ], string='Status', readonly=True, copy=False, index=True, default='draft')
    type = fields.Selection([
        ('bill', 'Bill'),
        ('invoice', 'Invoice')
    ], string='Type',copy=False, index=True)

    @api.constrains('picking_id','courier_product_id')
    def _check_unique_constraint_courier(self):
        for rec in self:
            msg = 'Product  "%s"' % rec.courier_product_id.product_id.name
            envobj = self.env['courier.service']
            conditionlist = [('picking_id', '=', rec.picking_id.id), ('courier_product_id', '=', rec.courier_product_id.id)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)


    @api.model
    def create(self, vals):
        res = super(CourierService, self).create(vals)
        if vals['amount'] < 1:
            raise UserError(
                _("Amount can't be less than 1.")
            )
        return res

    def write(self, vals):
        rslt = super(CourierService, self).write(vals)
        if self.amount < 0:
            raise UserError(
                _("Amount can't be less than 1.")
            )
        return rslt

    # state changing actions
    def action_confirm(self):
        self.state = 'confirm'

    def action_approve(self):
        self.create_bill_invoice()
        self.state = 'approve'

    # creating bill
    def create_bill_invoice(self):
        invoice_state = ''
        if self.type == 'bill':
            type = 'in_invoice'
        else:
            type = 'out_invoice'
            move_id = self.env['account.move'].search([('picking_id', '=', self.picking_id.id)],limit=1)
            invoice_state= move_id.state
            # updating existing invoice line with new product. It will not create new invoice
            if move_id.state == 'draft':
                invoice_line = []
                moveLineData = {
                    'name': self.courier_product_id.product_id.name,
                    'parent_state': 'draft',
                    'partner_id': self.vendor_id.id,
                    'product_id': self.courier_product_id.product_id.id,
                    'product_uom_id': self.courier_product_id.product_id.uom_id.id,
                    'quantity': 1,
                    'account_id': self.courier_product_id.product_id.property_account_income_id.id,
                    'price_unit': self.amount,
                    'is_rounding_line': False,
                    #'exclude_from_invoice_tab': False,
                    'is_landed_costs_line': False,
                }
                invoice_line.append((0, 0, moveLineData))
                move_id.update({
                    'invoice_line_ids': invoice_line,
                    'courier_id': self.id,
                })
                self.move_id = move_id.id
        # creating new invoice or bill based on type
        if invoice_state != 'draft':
            invoice_line = []
            moveLineData = {
                'name': self.courier_product_id.product_id.name,
                'parent_state': 'draft',
                'partner_id': self.vendor_id.id,
                'product_id': self.courier_product_id.product_id.id,
                'product_uom_id': self.courier_product_id.product_id.uom_id.id,
                'quantity': 1,
                'account_id': self.courier_product_id.product_id.property_account_income_id.id,
                'price_unit': self.amount,
                'is_rounding_line': False,
                #'exclude_from_invoice_tab': False,
                'is_landed_costs_line': False,
            }

            invoice_line.append((0, 0, moveLineData))
            inv_data = self.env['account.move'].create({
                'state': 'draft',
                'invoice_origin': self.picking_id.name,
                'partner_id': self.vendor_id.id,
                'invoice_date_due': date.today(),
                'type': type,
                'name': '/',
                'invoice_line_ids': invoice_line,
                'courier_id': self.id,
            })
            self.move_id = inv_data['id']

        return True
