from io import BytesIO
from odoo import models, fields
import xlwt
import base64

# This is global variable to indicate default Start from the first cell.
row = 0
parent_list = []
account_depth = {}
tree_depth = 0
max_depth = 10


class CoaXlsx(models.TransientModel):
    """
    For Chart of Accounts
    """
    _name = "account.open.chart.export.wizard"
    _description = "Account Export"

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    excel_file = fields.Binary('Download Report Excel')
    file_name = fields.Char('Excel File', size=64)

    def generate_xlsx_report(self, context=None):
        """ base of generating Excel file """
        # Reset row every call
        global row
        row = 0

        filename = 'Chart of Accounts' + '.xls'

        # Create a workbook and add a worksheet.
        workbook = xlwt.Workbook(encoding="UTF-8")
        worksheet = workbook.add_sheet('my sheet')

        # must have id column and make sure id column in first position. others will be free
        sql_query_for_root = """select aa.id, CONCAT(aa.code,'-', jsonb_extract_path_text(aa.name,'en_US')) as code from account_account as aa \
        where aa.parent_id IS NULL ORDER by aa.code"""
        self.env.cr.execute(sql_query_for_root)

        # Get data as a list of tuples
        root_accounts = self.env.cr.fetchall()
        self._write_worksheet(worksheet, root_accounts)


        fp = BytesIO()
        workbook.save(fp)
        export_id = self.create({'excel_file': base64.encodebytes(fp.getvalue()), 'file_name': filename})
        fp.close()


        return {
            'name': 'COA Export',
            'view_mode': 'form',
            'res_id': export_id.id,
            'res_model': 'account.open.chart.export.wizard',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def _write_worksheet(self, worksheet, datas):
        """ write in worksheet """
        global row, account_depth, max_depth
        for single_record in datas:
            self._get_account_depth(single_record[0])
            single_account_id = single_record[0]
            if single_account_id in account_depth:
                if account_depth[single_account_id] == 0:
                    for co in range(len(single_record) + max_depth):
                        if co < len(single_record) - 1:
                            worksheet.write(row, co, single_record[co+1])
                        else:
                            worksheet.write(row, co, "")
                else:
                    for co in range(len(single_record) + max_depth):
                        if co < account_depth[single_account_id]:
                            worksheet.write(row, co, "")
                        elif co < len(single_record) + account_depth[single_account_id] - 1:
                            worksheet.write(row, co, single_record[co - account_depth[single_account_id] + 1])
                        else:
                            worksheet.write(row, co, "")
            row += 1
            self._get_account(single_record[0], worksheet)

    def _get_account(self, parent_ids, worksheet):
        """ get data depending on specific parent_id """

        # must have id column and make sure id column in first position. others will be free
        que = """ select aa.id, CONCAT(aa.code,'-', jsonb_extract_path_text(aa.name,'en_US')) as code from account_account as aa \
        where aa.parent_id={con} ORDER BY aa.code""".format(con=str(parent_ids))
        self.env.cr.execute(que)
        datas = self.env.cr.fetchall()
        self._write_worksheet(worksheet, datas)

    def _get_account_depth(self, account):
        """ assign depth for each account """
        global parent_list, tree_depth
        parent_query = """ select aa.parent_id from account_account as aa where aa.id={con} """.format(con=str(account))
        self.env.cr.execute(parent_query)
        parent_account = self.env.cr.fetchall()
        for s_parent_account in parent_account:
            if s_parent_account[0]:
                if s_parent_account[0] not in parent_list:
                    tree_depth += 1
                    parent_list.append(s_parent_account[0])
                    t_query = """ select aa.id from account_account as aa where aa.parent_id={con} """.format(
                        con=str(s_parent_account[0]))
                    self.env.cr.execute(t_query)
                    t_datas = self.env.cr.fetchall()
                    if t_datas:
                        for a in t_datas:
                            if a[0] not in account_depth.keys():
                                account_depth[a[0]] = account_depth[s_parent_account[0]] + 1
            else:
                account_depth[account] = 0
