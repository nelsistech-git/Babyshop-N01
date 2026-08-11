from odoo import exceptions, fields, models, _
from odoo.exceptions import UserError
import base64
import time


class CustomerUploadWizard(models.TransientModel):
    _name = "customer.upload.wizard"
    _description = "Customer Upload Wizard"

    upload_csv_file = fields.Binary(string="Upload File")
    upload_des = fields.Text(string="Description")

    def action_customer_upload(self):
        if not self.upload_csv_file:
            raise exceptions.ValidationError("Failed! Required CSV file!")
        else:
            # lines = []
            file_data = base64.decodestring(self.upload_csv_file)
            csv_data = str(file_data.decode("utf-8"))
            row_list = csv_data.split('\n')
            line_count = len(row_list)

            customer_tmpl_obj = self.env['res.partner']
            country_id = self.env.ref('base.bd').id

            customer_count = 0
            loop_count = 0
            error_str = ""
            row_no = 1

            # row_list.pop(0)

            if len(row_list) > 0:
                for i in range(len(row_list)):
                    if i == 0:
                        continue  # it's for 1st row heading

                    row_no = row_no + i
                    rowdata = row_list[i]
                    col_list = rowdata.split(',')
                    if rowdata == '':
                        continue

                    if len(col_list) != 4:
                        error_str += "Row-%s: Error: Required All Columns: Customer ID, Customer Name, Phone Number, Email" % row_no + '\n'
                        continue
                    else:
                        cust_ref = col_list[0]
                        cust_name = col_list[1]
                        mobile_no = col_list[2]
                        cust_email = col_list[3]
                        if not mobile_no.startswith("0"):
                            mobile_no = '0' + mobile_no

                        if not (len(mobile_no) == 11):
                            error_str += "Row-%s: 'Mobile number '%s' is not valid! E.g. 01842647664" % (
                                row_no, mobile_no) + '\n'
                            continue
                        else:
                            # if '' in rowdata:
                            #     error_str += "Row-%s: Missing some values!" % (row_no) + '\n'
                            #     continue
                            # else:
                            customer_row = customer_tmpl_obj.search([('mobile', '=', mobile_no)], limit=1)
                            if customer_row:
                                error_str += "Row-%s: %s already exists!" % (row_no, mobile_no) + '\n'
                                continue
                            else:
                                vals = {
                                    'company_type': 'person',
                                    'country_id': country_id,
                                    'ref': cust_ref,
                                    'name': cust_name,
                                    'mobile': mobile_no,
                                    'email': cust_email,
                                    'customer_rank': 1,
                                    'supplier_rank': 0
                                }
                                customer_tmpl_obj.create(vals)
                                customer_count += 1
                                loop_count += 1
                                if loop_count == 100:
                                    # print('----start----', datetime.datetime.now())
                                    time.sleep(5)
                                    loop_count = 0
                                    # print('----end----', datetime.datetime.now())
            else:
                raise UserError('No Customer to Upload!')

            upload_des = 'Total Rows: ' + str(line_count) + '\nImport Rows: ' + str(
                customer_count) + '\nError:\n' + str(
                error_str)

            self.upload_des = upload_des

            return {
                'name': _('Customer Upload'),
                'context': self.env.context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'customer.upload.wizard',
                'res_id': self.id,
                'view_id': False,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
