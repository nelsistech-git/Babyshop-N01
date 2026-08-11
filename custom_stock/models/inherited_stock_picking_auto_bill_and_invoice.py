from odoo import models, _, fields, api
from datetime import date
from odoo.exceptions import UserError


# Auto bill and invoice creation when validate products
class StockPickingInheritCustomStock(models.Model):
    _inherit = 'stock.picking'
    _description = "Stock Picking Inherit"

    return_reason = fields.Text(string="Return/Cancel Reason")
    sequence_code = fields.Char(related='picking_type_id.sequence_code', store=True)
    date_deadline = fields.Datetime("Deadline", readonly=False, copy=False, help="Date Promise to the customer on the top level document (SO/PO)")
    is_unreserve = fields.Boolean(default=False)
    show_validate = fields.Boolean(default=False)

    @api.model
    def create(self, vals):
        res = super(StockPickingInheritCustomStock, self).create(vals)
        if vals.get('location_id') == vals.get('location_dest_id'):
            raise UserError(
                _("Source And Destination Location can't be same.")
            )
        return res

    # def _compute_courier_count(self):
    #     all_courier = self.env['courier.service'].search([('picking_id', '=', self.id)])
    #     total_count = len(all_courier)
    #     self.courier_count = total_count
    #     if self.sale_id:
    #         self.is_show_courier = True

    # courier_count = fields.Integer(compute='_compute_courier_count', string='Courier Count')
    is_show_courier = fields.Boolean(default=False)
    challan_no = fields.Char(string="Challan No.")
    challan_date = fields.Date(string="Challan Date")
    terms_condition_id = fields.Many2one('stock.terms.condition', string='Terms & Condition Title', default=lambda self: self.__def_terms_condition())
    terms_condtion_details = fields.Html('Terms Condition Details')
    is_transfer_release = fields.Boolean(string='Is Transfer Release?', default=False, copy=False)
    is_validate_button_show = fields.Boolean(default=False, copy=False)

    @api.onchange('picking_type_id', 'partner_id')
    def onchange_picking_type(self):
        if self.picking_type_id:
            if self.picking_type_id.default_location_src_id:
                location_id = self.picking_type_id.default_location_src_id.id
            else:
                location_id = self.partner_id.property_stock_supplier.id

            if self.picking_type_id.default_location_dest_id:
                location_dest_id = self.picking_type_id.default_location_dest_id.id
            else:
                location_dest_id = self.partner_id.property_stock_customer.id
            if self.state == 'draft':
                self.location_id = location_id
                self.location_dest_id = location_dest_id

        # TDE CLEANME move into onchange_partner_id
        if self.partner_id and self.partner_id.picking_warn:
            if self.partner_id.picking_warn == 'no-message' and self.partner_id.parent_id:
                partner = self.partner_id.parent_id
            elif self.partner_id.picking_warn not in ('no-message', 'block') and self.partner_id.parent_id.picking_warn == 'block':
                partner = self.partner_id.parent_id
            else:
                partner = self.partner_id
            if partner.picking_warn != 'no-message':
                if partner.picking_warn == 'block':
                    self.partner_id = False
                return {'warning': {
                    'title': ("Warning for %s") % partner.name,
                    'message': partner.picking_warn_msg
                }}
    
    def action_reset_to_draft(self):
        # super(StockPickingInheritCustomStock, self).do_unreserve()
        data_sql1 = """update stock_picking set state='draft',is_transfer_release=false where id = {0};
                    """.format(self.id)
        self.env.cr.execute(data_sql1)

        data_sql2 = """update stock_move set state='draft' where picking_id = {0};
                    """.format(self.id)
        self.env.cr.execute(data_sql2)

        data_sql3 = """delete from stock_move_line where picking_id = {0};
                    """.format(self.id)
        self.env.cr.execute(data_sql3)

        for rec in self.move_ids_without_package:
            stock_row = self.env['stock.quant'].search([('product_id', '=', rec.product_id.id), ('quantity', '>', 0), ('location_id', '=', self.location_id.id)])
            if stock_row:
                for x in stock_row:
                    current_qty1 = x.reserved_quantity - rec.product_uom_qty
                    current_qty = 0 if current_qty1 < 0 else current_qty1
                    query = """ UPDATE stock_quant SET reserved_quantity = %s WHERE id = %s"""
                    self.env.cr.execute(query, [current_qty, x.id])

    # def do_unreserve(self):
    #     res = super(StockPickingInheritCustomStock, self).do_unreserve()
    #     self.show_check_availability = True
    #     self.is_unreserve = True
    #     self.state = 'confirmed'
    #     return res

    # def _compute_show_check_availability(self):
    #     """ According to `picking.show_check_availability`, the "check availability" button will be
    #     displayed in the form view of a picking.
    #     """
    #     for picking in self:
    #         if picking.immediate_transfer or not picking.is_locked or picking.state not in ('confirmed', 'waiting', 'assigned'):
    #             picking.show_check_availability = False
    #             continue
    #         picking.show_check_availability = any(
    #             move.state in ('waiting', 'confirmed', 'partially_available') and
    #             float_compare(move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding)
    #             for move in picking.move_lines
    #         )
    #
    #         if picking.is_unreserve:
    #             picking.show_check_availability = True

    # def action_assign(self):
    #     res = super(StockPickingInheritCustomStock, self).action_assign()
    #     print(res)
    #     print(self.quantity)
    #     rint(self)
    #     return res
    #

    def action_confirm(self):
        res = super(StockPickingInheritCustomStock, self).action_confirm()
        for rec in self:
            if rec.sequence_code == 'INT':
                rec.show_validate = False
        return res

    @api.depends('state', 'is_locked')
    def _compute_show_validate(self):
        for picking in self:
            if not (picking.immediate_transfer) and picking.state == 'draft':
                picking.show_validate = False
            elif picking.state not in ('draft', 'waiting', 'confirmed', 'assigned') or not picking.is_locked:
                picking.show_validate = False
            else:
                if self.sequence_code == 'INT':
                    if not self.is_transfer_release:
                        self.show_validate = False
                    elif self.env.context.get('is_validate_button_show') == None:
                        picking.show_validate = False
                    else:
                        picking.show_validate = True
                else:
                    picking.show_validate = True
    
    def get_po_receipts(self):
        stock_picking_obj = self.env['stock.picking'].search([('state', '!=', 'cancel'),
                                                            ('purchase_id', '!=', False)]).ids
        #print(stock_picking_obj)
        # outstanding_bill = []
        # for rec in stock_picking_obj:
        #     if rec.invoice_has_outstanding == True:
        #         outstanding_bill.append(rec.id)

        action_vals = {
            'name': _('PO Receipt'),
            'domain': [('id', 'in', stock_picking_obj)],
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {}
        }
        return action_vals

    def action_transfer_release(self):
        self.is_transfer_release = True
        self.show_validate = True

    @api.model
    def __def_terms_condition(self):
        terms_cond = self.env['stock.terms.condition'].search([('id', '!=', False)], order="id asc", limit=1)
        return terms_cond.id

    @api.onchange('terms_condition_id')
    def onchange_terms_condition_id(self):
        if self.terms_condition_id:
            # disc = {
            #     '$total_amount': '<b>' + str(math.floor(self.amount_total_tmp)) + '0</b>',
            #     '$delivery_date': '<b>' + str(self.date_order) + '</b>',
            #     '$supplier_name': '<b>' + str(self.partner_id.name) + '</b>',
            # }
            # final_temrs = re.sub('<[^>]+>', '', self.terms_condition_id.description)
            self.terms_condtion_details = self.terms_condition_id.description
            # '\n' +  'Total Amount: ' ' <b>' + str(math.floor(self.amount_total_tmp)) + '0</b>' '\n' + 'Delivery Date: ' ' <b>' + str(self.date_order) + '</b>' + '\n' +  'Supplier Name: ' ' <b>' + str(self.partner_id.name) + '</b>'
        else:
            self.terms_condtion_details = ''

    def action_account_move_journal(self):
        account_move_obj = self.env['account.move'].search([('picking_id', '=', self.id), ('move_type', '=', 'entry')])
        if not account_move_obj:
            raise UserError(_('No Journal Entry Found.'))
        action_vals = {
            'name': _('Journal'),
            'domain': [('id', 'in', account_move_obj.ids)],
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {
                'default_type': 'entry',
            }
        }
        return action_vals

    def copy(self, default=None):
        res = super(StockPickingInheritCustomStock, self).copy(default)
        if self.purchase_id:
            res.purchase_id = False
            res.group_id = False
            res.origin = ''
            for rec in res.move_ids_without_package:
                rec.purchase_line_id = False
            res.action_confirm()
        return res

    def button_validate(self):
        res = super(StockPickingInheritCustomStock, self).button_validate()
        allow_create_auto_bill = self.env['custom.common.settings'].search([('key', '=', 'allow_create_auto_bill')], limit=1)
        if allow_create_auto_bill.value:
            # update location id in move line
            if self.location_dest_id.usage == 'inventory':
                move_id = self.env['account.move'].search([('picking_id', '=', self.id)], limit=1)
                for rec in move_id.line_ids:
                    if rec.credit > 0:
                        rec.location_id = self.location_id.id
                    else:
                        rec.location_id = self.location_dest_id.id
            if self.purchase_id and self.sequence_code in ('IN', 'OUT'):
                if res == True:
                    self.create_bill()

            elif self.sale_id and self.sequence_code in ('IN', 'OUT'):
                if res == True:
                    if not self.sale_id.is_created_from_invoice:
                        self.create_invoice()
                # sending sms to customer
                # self.send_sms_notification()
        # else:
        #     # Backdate Transfer validate
        #     key_val = self.env['custom.common.settings'].search([('key', '=', 'transfer_backdate_allowed')], limit=1)
        #     if key_val.value:
        #         if self.scheduled_date:
        #             for rec in self.move_lines:
        #                 scheduled_date = self.scheduled_date
        #                 rec.date = scheduled_date
        #                 for m in rec.move_line_ids:
        #                     m.date = scheduled_date
        #                 raw_move_obj = self.env['account.move'].search([('picking_id', '=', self.id)])
        #                 raw_move_obj.date = scheduled_date

        return res

    # creating invoice
    def create_invoice(self, backorder=None):
        # checking if project.project is installed and project_id in sale_order
        cus_project_obj = self.env['ir.module.module'].sudo().search([('name', '=', 'custom_project'), ('state', '=', 'installed')], limit=1)
        project_obj = self.env['ir.model'].sudo().search([('model', '=', 'project.project')], limit=1)
        project_id_field_obj = self.env['ir.model.fields'].sudo().search([('model', '=', 'account.move'), ('name', '=', 'project_id')], limit=1)

        # previous date change in stock move by sale date
        date_order = self._context.get('force_period_date', fields.Date.context_today(self))
        key_val = self.env['custom.common.settings'].sudo().search([('key', '=', 'sale_backdate_allowed')], limit=1)
        if key_val.value:
            for rec in self.move_ids_without_package:
                date_order = self.sale_id.date_order
                rec.date = date_order
                for m in rec.move_line_ids:
                    m.date = date_order

        # if sale return
        if self.picking_type_id.code == 'incoming':
            type = 'out_refund'
        else:
            type = 'out_invoice'
        if self.sale_id:
            order_id = self.sale_id.id
        else:
            order_id = None
        inv_list = []
        for rec in self.sale_id.invoice_ids:
            inv_list.append(rec.id)
        invoice_line = []
        for data in self.move_ids_without_package:
            qty_delivered = float("{0:.2f}".format(data.sale_line_id.qty_delivered))
            if qty_delivered > data.sale_line_id.product_uom_qty:
                raise UserError(_('Done Qty can not be greater than Reserved Quantity.'))
            if data.quantity != 0:
                moveLineData = {
                    'name': data.product_id.name,
                    'parent_state': 'draft',
                    'sale_line_ids': [(6, 0, [data.sale_line_id.id])],
                    'partner_id': self.partner_id.id if self.partner_id else None,
                    'product_id': data.product_id.id,
                    'product_uom_id': data.product_id.uom_id.id,
                    'quantity': data.quantity,
                    'price_unit': data.sale_line_id.price_unit,
                    'discount': data.sale_line_id.discount,
                }
                invoice_line.append((0, 0, moveLineData))
        if self.sale_id:
            # rint(self.sale_id.is_service_invoice)
            if self.sale_id.is_service_invoice == False:
                for data in self.sale_id.order_line:
                    if data.product_id.type == 'service':
                        moveLineDataService = {
                            'name': data.product_id.name,
                            'parent_state': 'draft',
                            'sale_line_ids': [(6, 0, [data.id])],
                            'partner_id': self.partner_id.id if self.partner_id else None,
                            'customer_reference_id': self.sale_id.customer_reference_id.id,
                            'product_id': data.product_id.id,
                            'product_uom_id': data.product_id.uom_id.id,
                            'quantity': data.product_uom_qty,
                            'price_unit': data.price_unit,
                            'discount': data.discount,
                            # 'is_rounding_line': False,
                            # 'exclude_from_invoice_tab': False,
                            # 'is_landed_costs_line': False,
                        }
                        invoice_line.append((0, 0, moveLineDataService))
                self.sale_id.is_service_invoice = True
        move_vals = {
            'state': 'draft',
            'order_id': order_id,
            'picking_id': self.id,
            'invoice_origin': self.name,
            'partner_id': self.partner_id.id if self.partner_id else None,
            'invoice_date_due': date.today(),
            'move_type': type,
            'date': date_order,
            'name': '/',
            'invoice_line_ids': invoice_line
        }
        if cus_project_obj:
            move_vals['project_id'] = self.sale_id.project_id.id or None
        inv_data = self.env['account.move'].create(move_vals)
        inv_list.append(inv_data['id'])

        auto_invoice_rows = self.env['custom.common.settings'].search([('key', '=', 'auto_invoice_post')], limit=1)
        if auto_invoice_rows.value == True:
            inv_data.post()
        self.sale_id.invoice_ids = [(6, 0, inv_list)]
        self.sale_id.invoice_status = 'invoiced'
        self.sale_id.invoice_count = len(inv_list)

        # ----------------
        # if backorder != 'no_backorder':
        #     for rec in self.move_ids_without_package:
        #         if self.picking_type_id.code != 'incoming':
        #             # reserve_stock = rec.sale_line_id.order_reserve_stock
        #             rec.sale_line_id.order_reserve_stock = reserve_stock - rec.quantity
        # else:
        #     for rec in self.move_ids_without_package:
        #         if self.picking_type_id.code != 'incoming':
        #             rec.sale_line_id.order_reserve_stock = 0
        return True

    # creating bill
    def create_bill(self):
        # previous date change in stock move by po date
        date_order = self._context.get('force_period_date', fields.Date.context_today(self))
        allow_create_auto_bill = self.env['custom.common.settings'].search([('key', '=', 'allow_create_auto_bill')], limit=1)
        if allow_create_auto_bill.value:
            key_val = self.env['custom.common.settings'].search([('key', '=', 'po_backdate_allowed')], limit=1)
            if key_val.value:
                for rec in self.move_lines:
                    date_order = self.purchase_id.date_order
                    rec.date = date_order
                    for m in rec.move_line_ids:
                        m.date = date_order
            type = ''
            # if purchase return
            if self.picking_type_id.code == 'outgoing':
                type = 'in_refund'
            else:
                type = 'in_invoice'
            inv_list = []
            for rec in self.purchase_id.invoice_ids:
                inv_list.append(rec.id)
            invoice_line = []
            for data in self.move_ids_without_package:
                if data.quantity != 0:
                    moveLineData = {
                        'name': data.product_id.name,
                        'parent_state': 'draft',
                        'purchase_line_id': data.purchase_line_id.id,
                        'partner_id': self.partner_id.id,
                        'product_id': data.product_id.id,
                        'product_uom_id': data.product_id.uom_id.id,
                        'quantity': data.quantity,
                        # 'discount_amount': data.purchase_line_id.fixed_discount,
                        'discount': data.purchase_line_id.discount,
                        'price_unit': data.purchase_line_id.price_unit,
                    }
                    invoice_line.append((0, 0, moveLineData))

            if self.purchase_id.is_service_invoice == False:
                for data in self.purchase_id.order_line:
                    if data.product_id.type == 'service':
                        if not data.product_id.property_account_income_id:
                            raise UserError(_('You Have To Add Account For This Product \'%s\'.') % (data.product_id.name))
                        moveLineDataService = {
                            'account_id': data.product_id.property_account_income_id.id,
                            'name': data.product_id.name,
                            'parent_state': 'draft',
                            'purchase_line_id': data.id,
                            'partner_id': self.partner_id,
                            'product_id': data.product_id.id,
                            'product_uom_id': data.product_id.uom_id.id,
                            'quantity': data.product_uom_qty,
                            'price_unit': data.price_unit,
                            # 'is_rounding_line': False,
                            # 'exclude_from_invoice_tab': False,
                            # 'is_landed_costs_line': False,
                        }
                        invoice_line.append((0, 0, moveLineDataService))
                self.purchase_id.is_service_invoice = True
            inv_data = self.env['account.move'].create({
                'state': 'draft',
                'po_id': self.purchase_id.id,
                'currency_id': self.purchase_id.currency_id.id,
                'ref': self.purchase_id.name,
                'invoice_origin': self.name,
                'partner_id': self.partner_id.id,
                'invoice_date_due': date.today(),
                'move_type': type,
                'date': date_order,
                'name': '/',
                'invoice_line_ids': invoice_line
            })
            # for x, y in zip(inv_data.invoice_line_ids, self.purchase_id.order_line):
            #     x.discount_amount = y.fixed_discount
            #     x._onchange_discount_amount_line()

            inv_list.append(inv_data['id'])
            auto_bill_rows = self.env['custom.common.settings'].search([('key', '=', 'auto_bill_post')], limit=1)
            if auto_bill_rows.value:
                inv_data.post()
            self.purchase_id.invoice_ids = [(6, 0, inv_list)]
            self.purchase_id.invoice_count = len(inv_list)

        return True

    def action_cancel(self):
        for rec in self:
            res = super(StockPickingInheritCustomStock, rec).action_cancel()
            # if not rec.note:
            #     raise UserError(_('Note is Mandatory while Canceling.'))
            if rec.sale_id:
                for rec2 in rec.move_lines:
                    rec2.sale_line_id.order_reserve_stock = 0
            #return res

    def send_sms_notification(self):
        template_obj = self.env['sms.template.custom'].sudo().search([('type', '=', 'delivery'), ('is_active', '=', True)],
                                                              limit=1)
        if template_obj:
            courier_rows = self.env['courier.service'].search([('picking_id', '=', self.id)])
            courier_str = ''
            courier_str = ", ".join([x.vendor_id.name for x in courier_rows])

            sms_obj = self.env['sms.outbox.details']

            sms_text = template_obj.sms_format
            cus_name = self.partner_id.name
            final_sms = sms_text.replace('$order_no', str(self.sale_id.name)).replace('$delivery_no',
                                                                                      str(self.name)).replace(
                '$courier_ref', courier_str)
            mobile = ''
            if self.partner_id.mobile:
                mobile = self.partner_id.mobile
            else:
                raise UserError(_('Required Customer Mobile No.'))

            sms_data = {'module_name': '4',
                        'source_ref': 'Delivery:' + self.name,
                        'mobile_no': self.partner_id.mobile,
                        'msg_body': final_sms,
                        'is_header_sent': template_obj.is_header_sent,
                        'is_footer_sent': template_obj.is_footer_sent,
                        'header_text': template_obj.header_text,
                        'footer_text': template_obj.footer_text
                        }
            sms_obj.sudo().create(sms_data)
        return True


# stock immediate transfer (create auto invoice and bill)
# class StockImmediateTransferInherit(models.TransientModel):
#     _inherit = 'stock.immediate.transfer'
#
#     def process(self):
#         res = super(StockImmediateTransferInherit, self).process()
#         if res == False:
#             # update location id in move line
#             if self.pick_ids.location_dest_id.usage == 'inventory':
#                 move_id = self.env['account.move'].search([('picking_id', '=', self.pick_ids.id)], limit=1)
#                 for rec in move_id.line_ids:
#                     if rec.credit > 0:
#                         rec.location_id = self.pick_ids.location_id.id
#                     else:
#                         rec.location_id = self.pick_ids.location_dest_id.id
#
#             for rec in self.pick_ids:
#                 if rec.purchase_id:
#                     StockPickingInheritCustomStock.create_bill(self.pick_ids)
#                 elif rec.sale_id:
#                     StockPickingInheritCustomStock.create_invoice(self.pick_ids)
#         return res
#
#
# # partially done quantity -- Create Backorder button (create auto invoice and bill)
# class StockBackorderConfirmationInherit(models.TransientModel):
#     _inherit = 'stock.backorder.confirmation'
#
#     # backorder
#     def process(self):
#         self._process()
#         # update location id in move line
#         if self.pick_ids.location_dest_id.usage == 'inventory':
#             move_id = self.env['account.move'].search([('picking_id', '=', self.pick_ids.id)], limit=1)
#             for rec in move_id.line_ids:
#                 if rec.credit > 0:
#                     rec.location_id = self.pick_ids.location_id.id
#                 else:
#                     rec.location_id = self.pick_ids.location_dest_id.id
#
#         for rec in self.pick_ids:
#             if rec.purchase_id:
#                 StockPickingInheritCustomStock.create_bill(self.pick_ids)
#             elif rec.sale_id:
#                 StockPickingInheritCustomStock.create_invoice(self.pick_ids)
#
#     # no backorder
#     def process_cancel_backorder(self):
#         self._process(cancel_backorder=True)
#         # update location id in move line
#         if self.pick_ids.location_dest_id.usage == 'inventory':
#             move_id = self.env['account.move'].search([('picking_id', '=', self.pick_ids.id)], limit=1)
#             for rec in move_id.line_ids:
#                 if rec.credit > 0:
#                     rec.location_id = self.pick_ids.location_id.id
#                 else:
#                     rec.location_id = self.pick_ids.location_dest_id.id
#
#         for rec in self.pick_ids:
#             if rec.purchase_id:
#                 StockPickingInheritCustomStock.create_bill(self.pick_ids)
#             elif rec.sale_id:
#                 StockPickingInheritCustomStock.create_invoice(self.pick_ids, 'no_backorder')


# product return from warehouse to vendor -- Return button (create auto invoice and bill)
# class ReturnPickingInherit(models.TransientModel):
#     _inherit = 'stock.return.picking'
#
#     def create_returns(self):
#         res = super(ReturnPickingInherit, self)._create_returns()
#         pickings = self.env['stock.picking'].browse(res[0])
#         if pickings:
#             print(pickings.purchase_id)
#             if pickings.purchase_id:
#                 StockPickingInheritCustomPoLc.create_bill(pickings)
#             elif pickings.sale_id:
#                 StockPickingInheritCustomPoLc.create_invoice(self.picking_id)
#         return res

class STJournalPrintReport(models.AbstractModel):
    _name = 'report.custom_stock.stock_journal_template_id'
    _description = 'Employee Settlement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        account_move_obj = self.env['account.move'].search([('picking_id', '=', docids[0]), ('type', '=', 'entry')],
                                                           limit=1)
        if not account_move_obj:
            raise UserError(_('No Journal Entry Found.'))
        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': account_move_obj,
            'data': data,
        }

