from odoo import models, fields, api
from odoo.addons.helper import validator

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.helper import xlsxwriter

import base64
from io import BytesIO


class RegionList(models.Model):
    _name = "region.list"
    _description = "Region List"

    file_data = fields.Binary('Region List')
    name = fields.Char(string='Name', required=True, copy=False)
    type = fields.Selection([
        ('national', 'National'),
        ('wings', 'Wings'),
        ('division', 'Division'),
        ('region', 'Region'),
        ('territory', 'Territory'),
        ('base', 'Base'),
    ], string='Type', required=True, copy=False)
    code = fields.Char(string='Code', copy=False)
    region_employee_lines = fields.One2many('region.list.employee', 'region_list_id', string='Regional Employees')
    parent_id = fields.Many2one('region.list', string='Parent', ondelete="restrict")
    division_id = fields.Many2one("division", string="Division")
    district_id = fields.Many2one("district", string="District")
    thana_id = fields.Many2one("district.thana", string="Thana")
    postcode_id = fields.Many2one("postcode", string="Postcode")

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.type:
                name = "%s [%s]" % (name, str(record.type).capitalize())
            result.append((record.id, name))
        return result

    @api.constrains('code')
    def _check_unique_constraint_code(self):
        for rec in self:
            msg = 'Code "%s" for this type' % rec.code
            envobj = self.env['region.list']
            conditionlist = [('code', '=', rec.code)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.constrains('parent_id', 'name')
    def _check_unique_constraint_name(self):
        for rec in self:
            msg = 'Name "%s" of this parent' % rec.name
            envobj = self.env['region.list']
            conditionlist = [('parent_id', '=', rec.parent_id.id), ('name', '=', rec.name)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.onchange('type', 'parent_id')
    def _onchange_parent_id(self):
        if self.type:
            if self.type == 'wings':
                domain = [('type', '=', 'national')]
            elif self.type == 'division':
                domain = [('type', '=', 'wings')]
            elif self.type == 'region':
                domain = [('type', '=', 'division')]
            elif self.type == 'territory':
                domain = [('type', '=', 'region')]
            elif self.type == 'base':
                domain = [('type', '=', 'territory')]
            else:
                domain = []

            return {'domain': {
                'parent_id': domain
            }}

    @api.onchange('type')
    def _onchange_type(self):
        if self.type:
            code = ''
            if self.type == 'national':
                code_row = self.env['region.list'].search([('type', '=', 'national')], order='code desc', limit=1)
                if code_row:
                    try:
                        code = 'N' + str(int((code_row[0].code)[1:]) + 1).zfill(1)
                    except:
                        code = 'N' + '1'
                else:
                    code = 'N' + '1'

            elif self.type == 'wings':
                code_row = self.env['region.list'].search([('type', '=', 'wings')], order='code desc', limit=1)
                if code_row:
                    try:
                        code = 'W' + str(int((code_row[0].code)[1:]) + 1).zfill(2)
                    except:
                        code = 'W' + '01'
                else:
                    code = 'W' + '01'

            elif self.type == 'division':
                code_row = self.env['region.list'].search([('type', '=', 'division')], order='code desc', limit=1)
                if code_row:
                    try:
                        code = 'D' + str(int((code_row[0].code)[1:]) + 1).zfill(2)
                    except:
                        code = 'D' + '01'
                else:
                    code = 'D' + '01'

            elif self.type == 'region':
                code_row = self.env['region.list'].search([('type', '=', 'region')], order='code desc', limit=1)
                if code_row:
                    try:
                        code = 'R' + str(int((code_row[0].code)[1:]) + 1).zfill(3)
                    except:
                        code = 'R' + '001'
                else:
                    code = 'R' + '001'

            elif self.type == 'territory':
                code_row = self.env['region.list'].search([('type', '=', 'territory')], order='code desc', limit=1)
                if code_row:
                    try:
                        code = 'T' + str(int((code_row[0].code)[1:]) + 1).zfill(4)
                    except:
                        code = 'T' + '0001'
                else:
                    code = 'T' + '0001'

            elif self.type == 'base':
                code_row = self.env['region.list'].search([('type', '=', 'base')], order='code desc', limit=1)
                if code_row:
                    try:
                        code = 'B' + str(int((code_row[0].code)[1:]) + 1).zfill(5)
                    except:
                        code = 'B' + '00001'
                else:
                    code = 'B' + '00001'

            else:
                pass

            self.code = code

            # ------------------
            if self.type == 'wings':
                domain = [('type', '=', 'national')]
            elif self.type == 'division':
                domain = [('type', '=', 'wings')]
            elif self.type == 'region':
                domain = [('type', '=', 'division')]
            elif self.type == 'territory':
                domain = [('type', '=', 'region')]
            elif self.type == 'base':
                domain = [('type', '=', 'territory')]
            else:
                domain = []

            return {'domain': {
                'parent_id': domain
            }}

    def action_download_data(self):
        data_list = self.get_region_data()
        file_name = "Region List- Hierarchy.xlsx"
        file_pointer = BytesIO()

        workbook = xlsxwriter.Workbook(file_pointer)

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

        sheet = workbook.add_worksheet('Region List')

        sheet.merge_range(0, 0, 2, 12, "Region List", format0)

        sheet.write(3, 0, 'SL No.', format2)
        sheet.write(3, 1, 'National', format2)
        sheet.write(3, 2, 'National (EMP)', format2)
        sheet.write(3, 3, 'Wing', format2)
        sheet.write(3, 4, 'Wing (EMP)', format2)
        sheet.write(3, 5, 'Division', format2)
        sheet.write(3, 6, 'Division (EMP)', format2)
        sheet.write(3, 7, 'Region', format2)
        sheet.write(3, 8, 'Region (EMP)', format2)
        sheet.write(3, 9, 'Territory', format2)
        sheet.write(3, 10, 'Territory (EMP)', format2)
        sheet.write(3, 11, 'Base', format2)
        sheet.write(3, 12, 'Base (EMP)', format2)
        # national_emp,win_emp,div_emp,reg_emp,ter_emp,bas_emp

        row = 4
        col = 0
        sl_no = 1

        for line in data_list:
            sheet.write(row, col, sl_no, format5)
            col = col + 1
            sheet.write(row, col, line['national'], format5)
            col = col + 1
            sheet.write(row, col, line['national_emp'], format5)
            col = col + 1
            sheet.write(row, col, line['wing'], format5)
            col = col + 1
            sheet.write(row, col, line['win_emp'], format5)
            col = col + 1
            sheet.write(row, col, line['division'], format5)
            col = col + 1
            sheet.write(row, col, line['div_emp'], format5)
            col = col + 1
            sheet.write(row, col, line['region'], format5)
            col = col + 1
            sheet.write(row, col, line['reg_emp'], format5)
            col = col + 1
            sheet.write(row, col, line['territory'], format5)
            col = col + 1
            sheet.write(row, col, line['ter_emp'], format5)
            col = col + 1
            sheet.write(row, col, line['route'], format5)
            col = col + 1
            sheet.write(row, col, line['bas_emp'], format5)

            row = row + 1
            col = 0
            sl_no = sl_no + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.encodestring(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Region List- Hierarchy',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=region.list&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def action_download_data_base(self):
        data_list = self.get_region_data_base()
        file_name = "Region List- Base.xlsx"
        file_pointer = BytesIO()

        workbook = xlsxwriter.Workbook(file_pointer)

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

        sheet = workbook.add_worksheet('Region List')

        sheet.merge_range(0, 0, 2, 12, "Region List", format0)

        sheet.write(3, 0, 'SL No.', format2)
        sheet.write(3, 1, 'National', format2)
        sheet.write(3, 2, 'National (Code)', format2)
        sheet.write(3, 3, 'Wing', format2)
        sheet.write(3, 4, 'Wing (Code)', format2)
        sheet.write(3, 5, 'Division', format2)
        sheet.write(3, 6, 'Division (Code)', format2)
        sheet.write(3, 7, 'Region', format2)
        sheet.write(3, 8, 'Region (Code)', format2)
        sheet.write(3, 9, 'Territory', format2)
        sheet.write(3, 10, 'Territory (Code)', format2)
        sheet.write(3, 11, 'Base', format2)
        sheet.write(3, 12, 'Base (Code)', format2)

        row = 4
        col = 0
        sl_no = 1

        for line in data_list:
            sheet.write(row, col, sl_no, format5)
            col = col + 1
            sheet.write(row, col, line['national'], format5)
            col = col + 1
            sheet.write(row, col, line['national_code'], format5)
            col = col + 1
            sheet.write(row, col, line['wing'], format5)
            col = col + 1
            sheet.write(row, col, line['wing_code'], format5)
            col = col + 1
            sheet.write(row, col, line['division'], format5)
            col = col + 1
            sheet.write(row, col, line['division_code'], format5)
            col = col + 1
            sheet.write(row, col, line['region'], format5)
            col = col + 1
            sheet.write(row, col, line['region_code'], format5)
            col = col + 1
            sheet.write(row, col, line['territory'], format5)
            col = col + 1
            sheet.write(row, col, line['territory_code'], format5)
            col = col + 1
            sheet.write(row, col, line['route'], format5)
            col = col + 1
            sheet.write(row, col, line['route_code'], format5)

            row = row + 1
            col = 0
            sl_no = sl_no + 1

        workbook.close()
        file_pointer.seek(0)
        file_data = base64.encodestring(file_pointer.read())
        self.write({'file_data': file_data})
        file_pointer.close()

        return {
            'name': 'Region List- Base',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=region.list&field=file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def get_region_data(self):
        data_list = []
        first_rows = self.env['region.list'].search([('type', '=', 'national')], order='name')
        for nat in first_rows:
            nat_id = nat.id
            nat_name = nat.name
            nat_code = nat.code
            national = str(nat_name) + ' (' + nat_code + ')'

            national_emp = ""
            emp_ids = self.env['region.list.employee'].search([('region_list_id', '=', nat_id)])
            for rec in emp_ids:
                if not national_emp:
                    national_emp = rec.employee_id.name
                else:
                    national_emp += ', ' + rec.employee_id.name

            data_dict = {'national': national, 'national_emp': national_emp, 'wing': '', 'win_emp': '', 'division': '',
                         'div_emp': '', 'region': '', 'reg_emp': '', 'territory': '', 'ter_emp': '', 'route': '',
                         'bas_emp': ''}
            data_list.append(data_dict)

            second_rows = self.env['region.list'].search([('parent_id', '=', nat_id)], order='name')
            for win in second_rows:
                win_id = win.id
                win_name = win.name
                win_code = win.code
                wings = str(win_name) + ' (' + win_code + ')'
                # data_dict = {'national': national, 'wing': wings, 'division': '', 'region': '', 'territory': '',
                #              'route': ''}

                win_emp = ""
                emp_ids = self.env['region.list.employee'].search([('region_list_id', '=', win_id)])
                for rec in emp_ids:
                    if not win_emp:
                        win_emp = rec.employee_id.name
                    else:
                        win_emp += ', ' + rec.employee_id.name

                data_dict = {'national': '', 'national_emp': '', 'wing': wings, 'win_emp': win_emp, 'division': '',
                             'div_emp': '', 'region': '', 'reg_emp': '', 'territory': '', 'ter_emp': '',
                             'route': '', 'bas_emp': ''}
                data_list.append(data_dict)

                third_rows = self.env['region.list'].search([('parent_id', '=', win_id)], order='name')
                for div in third_rows:
                    div_id = div.id
                    div_name = div.name
                    div_code = div.code
                    division = str(div_name) + ' (' + div_code + ')'
                    # data_dict = {'national': national, 'wing': wings, 'division': division, 'region': '',
                    #              'territory': '', 'route': ''}
                    div_emp = ""
                    emp_ids = self.env['region.list.employee'].search([('region_list_id', '=', div_id)])
                    for rec in emp_ids:
                        if not div_emp:
                            div_emp = rec.employee_id.name
                        else:
                            div_emp += ', ' + rec.employee_id.name

                    data_dict = {'national': '', 'national_emp': '', 'wing': '', 'win_emp': '', 'division': division,
                                 'div_emp': div_emp, 'region': '', 'reg_emp': '',
                                 'territory': '', 'ter_emp': '', 'route': '', 'bas_emp': ''}
                    data_list.append(data_dict)

                    fourth_rows = self.env['region.list'].search([('parent_id', '=', div_id)], order='name')
                    for reg in fourth_rows:
                        reg_id = reg.id
                        reg_name = reg.name
                        reg_code = reg.code
                        region = str(reg_name) + ' (' + reg_code + ')'
                        # data_dict = {'national': national, 'wing': wings, 'division': division, 'region': region,
                        #              'territory': '', 'route': ''}
                        reg_emp = ""
                        emp_ids = self.env['region.list.employee'].search([('region_list_id', '=', reg_id)])
                        for rec in emp_ids:
                            if not reg_emp:
                                reg_emp = rec.employee_id.name
                            else:
                                reg_emp += ', ' + rec.employee_id.name

                        data_dict = {'national': '', 'national_emp': '', 'wing': '', 'win_emp': '', 'division': '',
                                     'div_emp': '', 'region': region, 'reg_emp': reg_emp,
                                     'territory': '', 'ter_emp': '', 'route': '', 'bas_emp': ''}
                        data_list.append(data_dict)

                        fifth_rows = self.env['region.list'].search([('parent_id', '=', reg_id)], order='name')
                        for ter in fifth_rows:
                            ter_id = ter.id
                            ter_name = ter.name
                            ter_code = ter.code
                            territory = str(ter_name) + ' (' + ter_code + ')'
                            # data_dict = {'national': national, 'wing': wings, 'division': division, 'region': region,
                            #              'territory': territory, 'route': ''}
                            ter_emp = ""
                            emp_ids = self.env['region.list.employee'].search([('region_list_id', '=', ter_id)])
                            for rec in emp_ids:
                                if not ter_emp:
                                    ter_emp = rec.employee_id.name
                                else:
                                    ter_emp += ', ' + rec.employee_id.name

                            data_dict = {'national': '', 'national_emp': '', 'wing': '', 'win_emp': '', 'division': '',
                                         'div_emp': '', 'region': '', 'reg_emp': '',
                                         'territory': territory, 'ter_emp': ter_emp, 'route': '', 'bas_emp': ''}
                            data_list.append(data_dict)

                            sixth_rows = self.env['region.list'].search([('parent_id', '=', ter_id)], order='name')
                            for bas in sixth_rows:
                                bas_id = bas.id
                                bas_name = bas.name
                                bas_code = bas.code
                                route = str(bas_name) + ' (' + bas_code + ')'
                                # data_dict = {'national': national, 'wing': wings, 'division': division,
                                #              'region': region, 'territory': territory, 'route': route}
                                bas_emp = ""
                                emp_ids = self.env['region.list.employee'].search([('region_list_id', '=', bas_id)])
                                for rec in emp_ids:
                                    if not bas_emp:
                                        bas_emp = rec.employee_id.name
                                    else:
                                        bas_emp += ', ' + rec.employee_id.name

                                data_dict = {'national': '', 'national_emp': '', 'wing': '', 'win_emp': '',
                                             'division': '', 'div_emp': '',
                                             'region': '', 'reg_emp': '', 'territory': '', 'ter_emp': '',
                                             'route': route, 'bas_emp': bas_emp}
                                data_list.append(data_dict)

        return data_list

    def get_region_data_base(self):
        data_list = []
        self._cr.execute(('''select tbl_n.name as national_name, tbl_n.code as national_code,
                            tbl_w.name as wings_name, tbl_w.code as wings_code,
                            tbl_d.name as division_name, tbl_d.code as division_code,
                            tbl_r.name as region_name, tbl_r.code as region_code,
                            tbl_t.name as territory_name, tbl_t.code as territory_code,
                            tbl_b.name as base_name, tbl_b.code as base_code
                            FROM (
                            select id, name, code, parent_id from region_list where type='base') tbl_b
                            JOIN (select id, name, code, parent_id from region_list where type='territory') tbl_t ON tbl_t.id=tbl_b.parent_id
                            JOIN (select id, name, code, parent_id from region_list where type='region') tbl_r ON tbl_r.id=tbl_t.parent_id
                            JOIN (select id, name, code, parent_id from region_list where type='division') tbl_d ON tbl_d.id=tbl_r.parent_id
                            JOIN (select id, name, code, parent_id from region_list where type='wings') tbl_w ON tbl_w.id=tbl_d.parent_id
                            JOIN (select id, name, code, parent_id from region_list where type='national') tbl_n ON tbl_n.id=tbl_w.parent_id
                            ORDER BY tbl_n.name, tbl_w.name, tbl_d.name, tbl_r.name, tbl_t.name, tbl_b.name          
                                        '''))
        sql_result = self.env.cr.dictfetchall()
        for data in sql_result:
            data_dict = {
                'national': data['national_name'],
                'national_code': data['national_code'],
                'wing': data['wings_name'],
                'wing_code': data['wings_code'],
                'division': data['division_name'],
                'division_code': data['division_code'],
                'region': data['region_name'],
                'region_code': data['region_code'],
                'territory': data['territory_name'],
                'territory_code': data['territory_code'],
                'route': data['base_name'],
                'route_code': data['base_code'],
            }
            data_list.append(data_dict)

        return data_list


class RegionListEmployee(models.Model):
    _name = "region.list.employee"
    _description = "Region List Employee"

    region_list_id = fields.Many2one('region.list', string='Region List', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', domain="[('user_id','!=',False)]")
    employee_user_id = fields.Many2one('res.users', string='Employee User')
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id')
    designation_id = fields.Many2one('hr.job', string='Designation', related='employee_id.job_id')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.employee_user_id = self.employee_id.user_id.id

    @api.constrains('employee_id')
    def _check_unique_constraint_employee_id(self):
        for rec in self:
            msg = 'Employee "%s"' % rec.employee_id.name
            envobj = self.env['region.list.employee']
            conditionlist = [('region_list_id', '=', rec.region_list_id.id), ('employee_id', '=', rec.employee_id.id)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)
