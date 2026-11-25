from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
from datetime import datetime


try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.helper import xlsxwriter

import base64
from io import BytesIO


class ProjectCostingReportWizard(models.TransientModel):
    _name = "project.costing.report.wizard"
    _description = "Project Costing Report"

    file_data = fields.Binary('Project Costing Report')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date', default=fields.Date.context_today)
    src_location_id = fields.Many2one('stock.location', string='Source Location',
                                      domain="[('usage', '=', 'internal')]")
    dest_location_id = fields.Many2one('stock.location', string='Project Location')

    # comment-for-upgrade
    # src_location_id = fields.Many2one('stock.location', string='Source Location',
    #                                   domain="[('usage', '=', 'internal'), ('state', '=', 'done')]")
    # dest_location_id = fields.Many2one('stock.location', string='Project Location',
    #                                    domain="[('type', '=', 'project'), ('state', '=', 'done')]")

    rpt_type = fields.Selection([
        ('details', 'Details'),
        ('summary', 'Summary')
    ], string="Report Type", default='summary', copy=False)

    # category_id = fields.Many2one('product.category', string='Product Category')
    # product_id = fields.Many2one('product.product', string='Product', help="Main Product",
    #                              domain="[('state', '=', 'approve'), ('product_tmpl_id.categ_id', 'child_of', category_id)]")


    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        for rec in self:
            if rec.end_date < rec.start_date:
                raise ValidationError(_('Start date cannot be greater than the end date.'))

    def project_costing_report_pdf(self):
        start_date = self.start_date
        end_date = self.end_date
        # category_id = self.category_id
        # product_id = self.product_id
        src_location_id = self.src_location_id
        dest_location_id = self.dest_location_id

        # get data from sql
        data = self.project_costing_report_sql(start_date, end_date, src_location_id, dest_location_id)

        return self.env.ref('custom_account_day_book.project_costing_report_tmpl').with_context(
            landscape=False).report_action(self, data=data)

    def project_costing_report_excel(self):
        start_date = self.start_date
        end_date = self.end_date
        # category_id = self.category_id
        # product_id = self.product_id
        src_location_id = self.src_location_id
        dest_location_id = self.dest_location_id

        # get data from sql
        data = self.project_costing_report_sql(start_date, end_date, src_location_id, dest_location_id)

        start_date = datetime.strptime(str(start_date), '%Y-%m-%d').strftime('%d-%b-%Y')
        end_date = datetime.strptime(str(end_date), '%Y-%m-%d').strftime('%d-%b-%Y')

        file_name = "Project Costing Report.xlsx"
        file_pointer = BytesIO()

        workbook = xlsxwriter.Workbook(file_pointer)

        # main header formatting
        format0 = workbook.add_format({'font_size': 14, 'align': 'vcenter', 'bold': True})
        format0.set_align('center')
        format0.set_border()

        # column header formatting
        format1 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format1.set_align('left')
        format1.set_border()
        format2 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format2.set_align('center')
        format2.set_border()
        format3 = workbook.add_format({'font_size': 10, 'align': 'vcenter', 'bold': True})
        format3.set_align('right')
        format3.set_border()

        # body formatting
        format4 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format4.set_align('left')
        format4.set_border()
        format5 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format5.set_align('center')
        format5.set_border()
        format6 = workbook.add_format({'font_size': 10, 'align': 'vcenter'})
        format6.set_align('right')
        format6.set_border()

        # grand total formatting
        format7 = workbook.add_format({'font_size': 10, 'align': 'right', 'bold': True})
        format7.set_border()
        format8 = workbook.add_format({'font_size': 10, 'align': 'left', 'bold': True})
        format8.set_border()
        format9 = workbook.add_format({'font_size': 10, 'align': 'center', 'bold': True})
        format9.set_border()

        sheet = workbook.add_worksheet('Inventory Transfer Report')

        # table heading
        head_row = 5
        head_col = 0

        sheet.write(head_row, head_col, 'Sl. No.', format2)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Cost Head', format1)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Item Name', format1)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'UOM', format1)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Date', format3)
        # head_col = head_col + 1
        # sheet.write(head_row, head_col, 'Source Location', format1)
        # head_col = head_col + 1
        # sheet.write(head_row, head_col, 'Destination Location', format1)
        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Qty.', format3)

        head_col = head_col + 1
        sheet.write(head_row, head_col, 'Total Cost Price', format3)

        # main heading
        sheet.merge_range(0, 0, 1, head_col, 'Project Costing Report (%s)'% (data['report_type'] or '-'), format0)

        sheet.merge_range(2, 0, 2, int(head_col/2), 'Start Date: {0}'.format(start_date), format1)
        sheet.merge_range(3, 0, 3, int(head_col/2), 'End Date: {0}'.format(end_date), format1)
        sheet.merge_range(2, int(head_col/2) + 1, 2, head_col, 'Source Location: {0}'.format(data['src_loc_name']), format3)
        sheet.merge_range(3, int(head_col/2) + 1, 3, head_col, 'Destination Location: {0}'.format(data['dest_loc_name']), format3)

        sl_no = 1
        t_quantity = 0
        t_sales_price = 0
        total_price = 0

        # table body
        row = head_row + 1
        col = 0

        for rec in data['csr']:
            sheet.write(row, col, sl_no, format5)
            col = col + 1
            sheet.write(row, col, rec['cost_head'], format4)
            col = col + 1
            sheet.write(row, col, rec['product'], format4)
            col = col + 1
            sheet.write(row, col, rec['uom'], format4)
            col = col + 1

            try:
                tr_date = datetime.strptime(str(rec['date']),'%Y-%m-%d').strftime('%Y-%m-%d')
            except:
                tr_date = rec['date']

            sheet.write(row, col, tr_date, format4)
            # col = col + 1
            # sheet.write(row, col, rec['dest_location'], format4)
            col = col + 1
            sheet.write(row, col, round(rec['qty'], 3), format6)
            t_quantity = t_quantity + rec['qty']
            # col = col + 1
            # sheet.write(row, col, round(rec['cost_price'], 2), format6)
            # t_sales_price = t_sales_price + rec['cost_price']
            col = col + 1
            sheet.write(row, col, round(rec['total_cost'], 2), format6)
            total_price = total_price + rec['total_cost']

            sl_no = sl_no + 1
            row = row + 1
            col = 0

        # total section
        final_row = row
        final_col = 4
        sheet.merge_range(final_row, 0, final_row, final_col, 'Total', format7)
        final_col = final_col + 1
        sheet.write(final_row, final_col, round(t_quantity, 3), format7)
        # final_col = final_col + 1
        # sheet.write(final_row, final_col, round(t_sales_price, 2), format7)
        final_col = final_col + 1
        sheet.write(final_row, final_col, round(total_price, 2), format7)

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.encodestring(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Project Costing Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=project.costing.report.wizard&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def project_costing_report_sql(self, start_date, end_date, src_location_id, dest_location_id):

        domain = [('picking_id.state', '=', 'done'), ('picking_id.picking_type_id.code', '=', 'internal'), ('date', '>=', start_date), ('date', '<=', end_date)]

        if src_location_id:
            domain = domain + [('location_id', '=', src_location_id.id)]
            src_loc_name = src_location_id.name
        else:
            src_loc_name = "All"

        if dest_location_id:
            domain = domain + [('location_dest_id', '=', dest_location_id.id)]
            dest_loc_name = dest_location_id.name
        else:
            domain = domain + [('location_dest_id.type', '=', 'project'),('location_dest_id.state', '=', 'done')]
            dest_loc_name = "All"


        data_list = []

        stock_obj = self.env['stock.move'].search(domain)

        #--------------------
        startDateFilter = ""
        src_location = ""
        dest_location = ""
        dest_location2 = ""

        #----------- Source
        if src_location_id:
            loc_ids = tuple(self.env['stock.location'].search([('id', '=', src_location_id.id)]).ids)
            src_loc_name = src_location_id.name
        else:
            loc_ids = tuple(self.env['stock.location'].search([('usage', '=', 'internal'), ('state', '=', 'done')]).ids)
            src_loc_name = "All"
        if len(loc_ids) > 1:
            src_location = "AND sm.location_id IN {0}".format(loc_ids)
        elif len(loc_ids) == 1:
            src_location = "AND sm.location_id = %s" % loc_ids[0]

        #-------------Destination
        if dest_location_id:
            dest_loc_ids = tuple(self.env['stock.location'].search([('id', '=', dest_location_id.id)]).ids)
            dest_loc_name = dest_location_id.name
        else:
            dest_loc_ids = tuple(self.env['stock.location'].search([('type', '=', 'project'),('state', '=', 'done')]).ids)
            dest_loc_name = "All"
        if len(dest_loc_ids) > 1:
            dest_location = "AND sm.location_dest_id IN {0}".format(dest_loc_ids)
            dest_location2 = "AND amvl.location_id IN {0}".format(dest_loc_ids)
        elif len(dest_loc_ids) == 1:
            dest_location = "AND sm.location_dest_id = %s" % dest_loc_ids[0]
            dest_location2 = "AND amvl.location_id = %s" % dest_loc_ids[0]

        if self.rpt_type == 'details':
            data_sql1 = """     	                    
                    SELECT product_id, product_name,uom_name, date, cost_price, SUM(qty) AS qty, SUM(qty*cost_price) AS total_cost
                    FROM(
                    SELECT sm.product_id as product_id,pt.name as product_name,um.name as uom_name, DATE(sm.date) as date, COALESCE(sm.product_uom_qty, 0) AS qty, (COALESCE(sm.cost_price, 0) + COALESCE(sm.other_cost, 0)) as cost_price
                    FROM stock_move sm
                    JOIN product_product pp ON pp.id = sm.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN uom_uom um ON um.id = pt.uom_id
                    WHERE sm.state = 'done' AND DATE(date) BETWEEN '{0}' AND '{1}'
                    {2} {3}
                    ) tbl1
                    GROUP BY product_id, product_name,uom_name, date, cost_price
                    """.format(start_date, end_date, src_location, dest_location)
        else:
            data_sql1 = """
               SELECT product_id, product_name,uom_name, '-' as date, SUM(qty) AS qty, SUM(total_cost) AS total_cost
                   FROM (
                    SELECT product_id, product_name,uom_name, date, cost_price, SUM(qty) AS qty, SUM(qty*cost_price) AS total_cost
                    FROM(
                    SELECT sm.product_id as product_id,pt.name as product_name,um.name as uom_name, DATE(sm.date) as date, COALESCE(sm.product_uom_qty, 0) AS qty, (COALESCE(sm.cost_price, 0) + COALESCE(sm.other_cost, 0)) as cost_price
                    FROM stock_move sm
                    JOIN product_product pp ON pp.id = sm.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    JOIN uom_uom um ON um.id = pt.uom_id
                    WHERE sm.state = 'done' AND DATE(date) BETWEEN '{0}' AND '{1}'
                    {2} {3}
                    ) tbl1
                    GROUP BY product_id, product_name,uom_name, date, cost_price
                ) tbl3
                GROUP BY product_id, product_name,uom_name
                
                """.format(start_date, end_date, src_location, dest_location)

        self.env.cr.execute(data_sql1)
        data_res1 = self.env.cr.dictfetchall()
        #print('data_sql1-----------',data_sql1)
        #-------------
        for sm in data_res1:
            vals = {
                'cost_head': 'Material Cost',
                'product': sm['product_name'],
                'uom': sm['uom_name'],
                'date': sm['date'],
                'qty': sm['qty'],
                'total_cost': sm['total_cost']
            }
            data_list.append(vals)

        #-------------------
        # # ------------------ extra cost
        if self.rpt_type == 'details':
            data_sql2 = """
                    SELECT type, account_id, acc_name, date, sum(balance) as balance
                    FROM (
                    SELECT acc.project_extra_cost_category as type, amvl.account_id as account_id, acc.name as acc_name, DATE(amv.date) as date, (debit-credit) as balance
                        FROM account_move amv
                        JOIN account_move_line amvl ON (amvl.move_id=amv.id)
                        JOIN account_account acc ON (acc.id=amvl.account_id)
                        WHERE amv.state='posted'
                        AND DATE(amv.date) >= '{0}'
                        AND DATE(amv.date) <= '{1}'                    
                        AND acc.project_extra_cost_category in ('overhead','labour','vat','tax','other')
                        {2}
                    ) tbl2
                    GROUP BY type, account_id, acc_name, date
                               """.format(start_date, end_date, dest_location2)
        else:
            data_sql2 = """
                      SELECT type, '-' as account_id, '-' as acc_name, '-' as date, sum(balance) as balance
                        FROM (
                                SELECT type, account_id, acc_name, date, sum(balance) as balance
                                FROM (
                                SELECT acc.project_extra_cost_category as type, amvl.account_id as account_id, acc.name as acc_name, DATE(amv.date) as date, (debit-credit) as balance
                                    FROM account_move amv
                                    JOIN account_move_line amvl ON (amvl.move_id=amv.id)
                                    JOIN account_account acc ON (acc.id=amvl.account_id)
                                    WHERE amv.state='posted'
                                    AND DATE(amv.date) >= '{0}'
                                    AND DATE(amv.date) <= '{1}'                    
                                    AND acc.project_extra_cost_category in ('overhead','labour','vat','tax','other')
                                    {2}
                                ) tbl2
                                GROUP BY type, account_id, acc_name, date
                            ) tbl3
                            GROUP BY type
                                           """.format(start_date, end_date, dest_location2)

        self.env.cr.execute(data_sql2)
        data_res2 = self.env.cr.dictfetchall()
        #print('data_res2-----------', data_res2)
        for accmv in data_res2:
            vals = {
                'cost_head': dict(self.env['account.account']._fields['project_extra_cost_category'].selection).get(accmv['type']),
                'product': accmv['acc_name'],
                'uom': '',
                'date': accmv['date'],
                'qty': 0,
                'total_cost': accmv['balance']
            }
            data_list.append(vals)

        #-----------------
        data = {
            'model': "project.costing.report.wizard",
            'form': self.read()[0],
            'csr': data_list,
            'src_loc_name': src_loc_name,
            'dest_loc_name': dest_loc_name,
            'report_type': str(self.rpt_type).capitalize() or '-'
        }
        return data




