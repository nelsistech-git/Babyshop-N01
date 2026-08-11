from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError
import base64
from datetime import datetime


class MiniInventoryAdjustmentWizard(models.TransientModel):
    _name = 'mini.inventory.adjustment.wizard'
    _description = "MINI Inventory Adjustment Report"

    upload_csv_file = fields.Binary(string="Upload File")
    upload_des = fields.Text(string="Description")
    location_id = fields.Many2one('stock.location', string='Location',
                                  domain=[('state', '=', 'done')])
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', copy=False, index=True, default='done')
    type = fields.Selection([
        ('01', 'Scan'),
        ('02', 'Upload'),
    ], string='Type', copy=False, index=True, default='01')
    scrap_scan_barcode = fields.Text(string='Barcode & Qty')
    product_line_ids = fields.One2many('mini.inventory.adjustment.wizard.line', 'head_id', string='Product Line')

    def check_barcode_validity(self):
        total_count = 0
        loop_count = 0
        article_count = 0
        error_str = ''
        non_vals = []
        if self.scrap_scan_barcode:
            product_tmpl_obj = self.env['product.product'].sudo()
            if self.scrap_scan_barcode:
                nonfoot_barcode_list = self.scrap_scan_barcode.split('\n')
                if len(nonfoot_barcode_list) > 0:
                    for line in nonfoot_barcode_list:
                        if line:
                            loop_count += 1
                            barcode_splt = line.split()
                            if not barcode_splt[0]:
                                error_str += "Error: Required All Columns:  Barcode, QTY!" + '\n'
                                continue
                            else:
                                prod_barcode = barcode_splt[0]
                                prod_qty = 0
                                try:
                                    prod_qty = barcode_splt[1]
                                except Exception as e:
                                    error_str += "Error: " + str(e) +'\n'
                                if not prod_qty and prod_barcode == '':
                                    error_str += "Error: Barcode and QTY required!" + '\n'
                                    continue
                                else:
                                    try:
                                        if float(prod_qty) < .1 or float(prod_qty) > .99:
                                            error_str += "Error: Barcode:%s (Qty: %s) Qty Shouldn't Less than .1 or More than .99!" % (prod_barcode, prod_qty) + '\n'
                                            continue
                                        if prod_barcode:
                                            product_row = product_tmpl_obj.search([('barcode', '=', prod_barcode)],
                                                                                  limit=1)
                                            if product_row:
                                                non_vals.append((0, 0, {'pro_id': product_row.id,
                                                                        'qty': float(prod_qty),
                                                                        'approved_by_id': self.approved_by_id.id,
                                                                        'location_id': self.location_id.id,
                                                                        }))
                                                article_count += 1
                                            else:
                                                error_str += "Error: Barcode %s not Found!" % (
                                                     prod_barcode) + '\n'
                                                continue
                                    except:
                                        error_str += "Error: Possibly it doesn't exists!" + '\n'
                                        continue
                            total_count = total_count + 1
                    if non_vals:
                        self.write({
                            'product_line_ids': non_vals,
                        })

        upload_des = 'Total Rows: ' + str(loop_count) + '\nImport Rows: ' + str(article_count) + '\nError:\n' + str(error_str)
        self.upload_des = upload_des
        self.scrap_scan_barcode = ''
        return {
            'name': _('Inventory Adjustment (Qty .1 - Qty .99)'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mini.inventory.adjustment.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_adjustment_file_upload(self):
        loc_obj = self.env['stock.location'].search([('usage', '=', 'inventory')], limit=1)
        stock_move_obj = self.env['stock.move'].sudo()
        if self.type == '01':
            if not self.product_line_ids:
                raise exceptions.ValidationError("Failed! Required Product!")
            for rec in self.product_line_ids:
                if rec.pro_id and self.state == 'done':
                    move_vals = {
                        'name': 'Inventory Adjustment',
                        'product_id': rec.pro_id.id,
                        'product_uom': rec.pro_id.uom_id.id,
                        'product_uom_qty': rec.qty,
                        'location_id': loc_obj.id,
                        'location_dest_id': self.location_id.id,
                        'quantity_done': rec.qty,
                        'date': datetime.today().date(),
                        'date_expected': datetime.today().date()
                    }
                    mo_move_obj = stock_move_obj.create(move_vals)
                    mo_move_obj.sudo()._action_done()

                if rec.pro_id:
                    self.env['mini.product.inventory.adjustment'].create({
                        'product_id': rec.pro_id.id,
                        'qty': rec.qty,
                        'approved_by_id': self.approved_by_id.id,
                        'location_id': self.location_id.id,
                        'state': self.state,
                    })
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

        else:
            if not self.upload_csv_file:
                raise exceptions.ValidationError("Failed! Required CSV file!")
            else:

                file_data = base64.decodestring(self.upload_csv_file)
                csv_data = str(file_data.decode("utf-8"))
                row_list = csv_data.split('\n')
                line_count = len(row_list)
                product_tmpl_obj = self.env['product.product'].sudo()

                article_count = 0
                loop_count = 0
                error_str = ""
                row_no = 1
                if len(row_list) > 0:
                    for i in range(len(row_list)):
                        if i == 0:
                            continue  # it's for 1st row heading

                        row_no = i + 1
                        rowdata = row_list[i]
                        col_list = rowdata.split(',')
                        if rowdata == '':
                            continue
                        loop_count += 1
                        if len(col_list) != 2:
                            error_str += "Row-%s: Error: Required All Columns:  Barcode,  Sales Price!" % row_no + '\n'
                            continue
                        else:
                            prod_barcode = col_list[0]
                            prod_qty = col_list[1]
                            if not prod_qty and prod_barcode == '':
                                error_str += "Row-%s: Error: Barcode and QTY required!" % row_no + '\n'
                                continue
                            else:
                                try:
                                    if float(prod_qty) < .1 or float(prod_qty) > .99:
                                        error_str += "Row-%s: Error: Barcode:%s (Qty: %s) Qty Shouldn't Less than .1 or More than .99!" % (
                                        row_no, prod_barcode, prod_qty) + '\n'
                                        continue
                                    if prod_barcode:
                                        product_row = product_tmpl_obj.search([('barcode', '=', prod_barcode)], limit=1)
                                        if product_row and self.state == 'done':
                                            move_vals = {
                                                'name': 'Inventory Adjustment',
                                                'product_id': product_row.id,
                                                'product_uom': product_row.uom_id.id,
                                                'product_uom_qty': prod_qty,
                                                'location_id': loc_obj.id,
                                                'location_dest_id': self.location_id.id,
                                                'quantity_done': prod_qty,
                                                'date': datetime.today().date(),
                                                'date_expected': datetime.today().date()
                                            }
                                            mo_move_obj = stock_move_obj.create(move_vals)
                                            mo_move_obj.sudo()._action_done()

                                        if product_row:
                                            self.env['mini.product.inventory.adjustment'].create({
                                                'product_id': product_row.id,
                                                'qty': prod_qty,
                                                'approved_by_id': self.approved_by_id.id,
                                                'location_id': self.location_id.id,
                                                'state': self.state,
                                            })

                                            article_count += 1
                                        else:
                                            error_str += "Row-%s: Error: Barcode %s not Found!" % (
                                            row_no, prod_barcode) + '\n'
                                            continue
                                except:
                                    error_str += "Row-%s: Error: Possibly it doesn't exists!" % row_no + '\n'
                                    continue
                else:
                    raise UserError('No Products to Upload!')

                upload_des = 'Total Rows: ' + str(loop_count) + '\nImport Rows: ' + str(article_count) + '\nError:\n' + str(
                    error_str)

                self.upload_des = upload_des

            return {
                'name': _('Inventory Adjustment (Qty .1 - Qty .99)'),
                'context': self.env.context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'mini.inventory.adjustment.wizard',
                'res_id': self.id,
                'view_id': False,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    def action_sample_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/custom_stock/static/src/sample_inventory_adjustment_upload_file.csv',
            'target': 'self',
        }


class MiniInventoryAdjustmentWizardLine(models.TransientModel):
    _name = 'mini.inventory.adjustment.wizard.line'
    _description = "MINI Inventory Adjustment Wizard Line"

    head_id = fields.Many2one('mini.inventory.adjustment.wizard')
    location_id = fields.Many2one('stock.location', string='Location',
                                  domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    pro_id = fields.Many2one('product.product', string='Product/Barcode')
    qty = fields.Float()
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', copy=False, index=True, default='done')