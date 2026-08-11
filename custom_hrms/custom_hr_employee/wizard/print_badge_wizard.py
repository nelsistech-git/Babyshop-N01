from odoo import api, fields, models, _

class PrintBadgeWizard(models.TransientModel):
    _name = 'print.badge.wizard'
    _description = 'Print Employee Badges'

    employee_ids = fields.Many2many('hr.employee', string='Employees')

    # @api.multi
    # def print_badges(self):
    #     data = {
    #         'model': 'hr.employee',
    #         'ids': self.employee_ids.ids,
    #         'form': {'dummy': True},
    #         'context': {'active_test': False},
    #     }
    #     return self.env.ref('custom_hr_employee.report_employee_badges').report_action(self, data=data)
    #
    # def print_badges(self, data={}):
    #     pt_id = self.pt_id.id
    #     product_id = self.product_id.id
    #     barcode_format = self.barcode_format
    #     print_qty = self.print_qty
    #
    #     request_url = str(request.httprequest.url_root)
    #
    #     if not (pt_id):
    #         raise exceptions.ValidationError("Required PO")
    #     else:
    #         product_list = []
    #         # print(product_list)
    #         # ----------
    #         domain = []
    #         if pt_id:
    #             domain.append(('product_id.product_tmpl_id', '=', pt_id))
    #         if product_id:
    #             domain.append(('product_id', '=', product_id))
    #
    #         line_rows = self.env['single.barcode.print.wizard'].search(domain, order="product_id asc")
    #         for line in line_rows:
    #             product_id = line.product_id.id
    #             product_name = str(line.product_id.name).upper()
    #             # product_size = line.product_id.product_template_attribute_value_ids.name
    #             product_size = ", ".join(attr.name for attr in line.product_id.product_template_attribute_value_ids)
    #             pt_code = line.product_id.product_tmpl_id.product_code
    #             currency_symbol = line.product_id.product_tmpl_id.company_id.currency_id.symbol
    #             list_price = line.product_id.list_price
    #             product_uom = line.product_id.uom_id.name
    #             product_barcode = line.product_id.barcode
    #             # product_qty = line.quantity_done or line.product_uom_qty
    #             product_qty = self.print_qty
    #             # -----------
    #
    #             try:
    #                 # po_no = str(line.stock_id.origin)
    #                 po_no = self.origin
    #             except:
    #                 po_no = '0'
    #             cat_name = str(line.product_id.product_tmpl_id.categ_id.name).upper()
    #             # -----------
    #             i = 1
    #             while (i <= product_qty):
    #                 dict_data = {'id': i,
    #                              'product_id': product_id,
    #                              'product_name': product_name,
    #                              'product_size': product_size,
    #                              'pt_code': pt_code,
    #                              'currency_symbol': currency_symbol,
    #                              'list_price': list_price,
    #                              'product_uom': product_uom,
    #                              'product_barcode': product_barcode,
    #                              'barcode': product_barcode,
    #                              'cat_name': cat_name,
    #                              'po_no': str(po_no)[2:],
    #                              }
    #                 product_list.append(dict_data)
    #                 i += 1
    #
    #             if len(product_list) == 0:
    #                 raise exceptions.ValidationError("Product not available!")
    #             else:
    #                 # ---------------------
    #                 page_list = []
    #                 if barcode_format == '1':
    #                     page_column = 5
    #                     page_row = 16
    #                 elif barcode_format == '2':
    #                     page_column = 4
    #                     page_row = 12
    #                 elif barcode_format == '3':
    #                     page_column = 2
    #                     page_row = 6
    #                 elif barcode_format == '4':
    #                     page_column = 2
    #                     page_row = 1
    #                 elif barcode_format == '5':
    #                     page_column = 2
    #                     page_row = 1
    #                 elif barcode_format == '6':
    #                     page_column = 2
    #                     page_row = 1
    #                 else:
    #                     page_column = 1
    #                     page_row = 1
    #
    #                 row_list = []
    #                 col_list = []
    #                 row_count = 0
    #                 col_count = 0
    #
    #                 for m in range(len(product_list)):
    #                     rec_data = product_list[m]
    #
    #                     col_list.append(rec_data)
    #                     col_count += 1
    #
    #                     if col_count == page_column:
    #                         row_list.append(col_list)
    #                         col_list = []
    #                         col_count = 0
    #                         row_count += 1
    #
    #                         if row_count == page_row:
    #                             page_list.append(row_list)
    #                             row_list = []
    #                             row_count = 0
    #
    #                 # ------ partial column add in row
    #                 if col_count > 0:
    #                     row_list.append(col_list)
    #                     col_list = []
    #                     col_count = 0
    #                     row_count += 1
    #                     if row_count == page_row:
    #                         page_list.append(row_list)
    #                         row_list = []
    #                         row_count = 0
    #
    #                 # ------ partial row add in page
    #                 if row_count > 0:
    #                     page_list.append(row_list)
    #                     row_list = []
    #                     row_count = 0
    #
    #                 data = {
    #                     'model': "single.barcode.print.wizard",
    #                     'form': self.read()[0],
    #                     'page_list': page_list,
    #                     'request_url': request_url
    #                 }
    #                 # print(data)
    #                 if barcode_format == '1':
    #                     return self.env.ref(
    #                         'custom_barcode.single_barcode_print_format_1_label').with_context().report_action(
    #                         self, data=data)
    #
    #                 elif barcode_format == '2':
    #                     return self.env.ref(
    #                         'custom_barcode.single_barcode_print_format_2_label').with_context().report_action(
    #                         self, data=data)

# import pytz
# import math
# from datetime import datetime, date, timedelta, time
# from dateutil.relativedelta import relativedelta
# from odoo import models, fields, tools, api, exceptions, _
# from odoo.exceptions import UserError, ValidationError
# from odoo.tools.misc import format_date
# from odoo.addons.resource.models.resource import float_to_time, HOURS_PER_DAY, \
#     make_aware, datetime_to_string, string_to_datetime
# from calendar import monthrange
#
#
#
# class AttendanceSheet(models.Model):
#     _name = 'print.badge.wizard'
#
#     _description = 'Print Badge Wizard'
#     _order = "id desc"
#
#
#     employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', index=True,
#                                   required=True)
#     id_card_no = fields.Char(string="Employee ID", groups="hr.group_hr_user",
#                              related='employee_id.id_card_no')
#
#     department_id = fields.Many2one(related='employee_id.department_id',
#                                     string='Department')
#     initial_employment_date = fields.Date(related='employee_id.initial_employment_date', string='Date of Joining')
#     job_id = fields.Many2one('hr.job', string="Designation", related="employee_id.job_id")
#     company_id = fields.Many2one('res.company', string='Company', readonly=True,
#                                  copy=False, required=True,
#                                  default=lambda self: self.env.company,
#                                  states={'draft': [('readonly', False)]})
#
#     user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
#                                        domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
#
#
