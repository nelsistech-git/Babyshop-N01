from odoo import _, api, fields, models
from datetime import date, datetime
from odoo.exceptions import UserError
from odoo.tools import format_date


class EmployeeIncrementLetter(models.TransientModel):
    _name = 'employee.increment.letter'
    _description = 'Employee Increment/Decrement Letter'

    type = fields.Selection(
        [('increment', 'Increment'), ('decrement', 'Decrement')],
        string='Type', default='increment')
    ref_id = fields.Many2one('hr.contract.update', string='Ref.')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    department_id = fields.Many2one('hr.department', string='Department')

    @api.onchange('type')
    def _onchange_type(self):
        type = self.type
        if type:
            return {'value': {'ref_id': None}}
        else:
            return {'value': {'ref_id': None},
                    'domain': {'ref_id': None}
                    }

    @api.onchange('ref_id')
    def _set_ref_id(self):
        ref_id = self.ref_id.id
        update_contract_obj = self.env['hr.contract.update.line'].sudo().search(
            [('hr_contract_update_id', '=', ref_id)])
        loc_list = []
        dept_list = []
        emp_list = []
        for rec in update_contract_obj:
            loc_list.append(rec.user_work_location_id.id)
            dept_list.append(rec.department_id.id)
            emp_list.append(rec.employee_id.id)
        loc_list = list(set(loc_list))
        dept_list = list(set(dept_list))
        emp_list = list(set(emp_list))

        if ref_id:
            return {'value': {'user_work_location_id': [('id', 'in', loc_list)],
                           'department_id': [('id', 'in', dept_list)],
                           'employee_id': [('id', 'in', emp_list)]
                           }}
        else:
            return {'value': {'user_work_location_id': None, 'department_id': None, 'employee_id': None},
                    'domain': {'user_work_location_id': None, 'department_id': None, 'employee_id': None}}

        # return {'domain': {'user_work_location_id': [('id', 'in', loc_list)],
        #                    'department_id': [('id', 'in', dept_list)],
        #                    'employee_id': [('id', 'in', emp_list)]
        #                    }}

    # @api.onchange('ref_id')

    def replace_all(self, descriptions, dic):
        for i, j in dic.items():
            if j == False:
                j = str(j)
            descriptions = descriptions.replace(i, str(j))
        return descriptions

    def action_print(self):
        letter_text1 = ''
        if self.type == 'increment':
            letter_type_obj = self.env['employee.letter.template'].sudo().search(
                [('template_type', '=', 'increment_letter'), ('active', '=', True)], limit=1)
        else:
            letter_type_obj = self.env['employee.letter.template'].sudo().search(
                [('template_type', '=', 'decrement_letter'), ('active', '=', True)], limit=1)
        if letter_type_obj:
            letter_text1 = letter_type_obj.description
        else:
            pass

        domain = [('hr_contract_update_id.type', '=', self.type),('hr_contract_update_id', '=', self.ref_id.id)]
        if self.user_work_location_id:
            domain += [('user_work_location_id', '=', self.user_work_location_id.id)]
        if self.department_id:
            domain += [('department_id', '=', self.department_id.id)]
        if self.employee_id:
            domain += [('employee_id', '=', self.employee_id.id)]

        increment_lines = self.env['hr.contract.update.line'].sudo().search(domain)
        all_letter = []
        for rec in increment_lines:
            emp_id = rec.employee_id.id
            emp_name = rec.employee_id.name
            increment_amt = rec.amount
            department_id = rec.department_id.name
            old_sal = rec.gross_salary
            new_sal = rec.new_gross_salary
            emp_designation = rec.job_id.name
            id_card_no = rec.id_card_no
            effective_date = rec.hr_contract_update_id.effective_date

            dict_data = {
                '$emp_name': str(emp_name),
                '$emp_department': str(department_id),
                '$emp_designation': str(emp_designation),
                '$emp_id': id_card_no,
                '$present_sal': '{0:,.2f}'.format(old_sal),
                '$inc_amt': '{0:,.2f}'.format(increment_amt),
                '$new_sal': '{0:,.2f}'.format(new_sal),
                '$ref_no': self.ref_id.name,
                '$print_date': datetime.strptime(str(date.today()), '%Y-%m-%d').strftime('%d-%b-%Y'),
                '$effective_date': datetime.strptime(str(effective_date), '%Y-%m-%d').strftime('%d-%b-%Y'),
            }
            letter_text_2 = self.replace_all(letter_text1, dict_data)

            letter_data = {
                'emp_id': emp_id,
                'letter_text': letter_text_2
            }
            all_letter.append(letter_data)

        data = {
            'model': "employee.increment.letter",
            'form': self.read()[0],
            'csr': all_letter,
        }

        return self.env.ref(
            'hr_payroll.employee_increment_letter_tmpl').with_context(landscape=False).report_action(self, data=data)
