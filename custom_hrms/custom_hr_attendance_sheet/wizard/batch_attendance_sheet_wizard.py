from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date


class BatchAttendanceSheetWizard(models.TransientModel):
    _name = 'batch.attendance.sheet.wizard'
    _description = 'Generate Batch Attendance Sheet Wizard'

    def _get_available_contracts_domain(self, date_from, date_to):
        return [('contract_ids.state', '=', 'open'), ('company_id', '=', self.env.company.id), ('contract_ids.date_start', '<=', date_to),
                '|', ('contract_ids.date_end', '=', False), ('contract_ids.date_end', '>=', date_from)]

    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    department_id = fields.Many2one('hr.department', string='Department')
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_batch_att_rel', 'batch_att_sheet_id', 'employee_id', 'Employees', required=True)
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    @api.model
    def default_get(self, fields):
        res = super(BatchAttendanceSheetWizard, self).default_get(fields)
        batch_sheet_obj = self.env['batch.attendance.sheet'].browse(self.env.context.get('active_id'))
        res['user_work_location_id'] = batch_sheet_obj.user_work_location_id.id
        res['department_id'] = batch_sheet_obj.department_id.id
        res['date_from'] = batch_sheet_obj.date_from
        res['date_to'] = batch_sheet_obj.date_to
        return res

    @api.onchange('user_work_location_id', 'department_id', 'date_from', 'date_to')
    def _onchange_employees(self):
        domains = self._get_available_contracts_domain(self.date_from, self.date_to)

        batch_sheet_obj = self.env['batch.attendance.sheet'].browse(self.env.context.get('active_id'))

        if batch_sheet_obj.user_work_location_id:
            domains += [('user_work_location_id', '=', batch_sheet_obj.user_work_location_id.id)]

        if batch_sheet_obj.department_id:
            domains += [('department_id', '=', batch_sheet_obj.department_id.id)]

        # skip confirmed resignation employees
        resig_obj = self.env['hr.resignation'].search([('state', '=', 'confirm'), ('submit_date', '>=', self.date_from), ('submit_date', '<=', self.date_to)])
        if resig_obj:
            domains += [('id', 'not in', resig_obj.employee_id.ids)]
        # ----- end
        domains += [('is_separated', '=', False)]

        emp_ids = self.env['hr.employee'].search(domains)

        payslip_emp_ids = set(self.env['hr.payslip'].search([('date_to', '>=', batch_sheet_obj.date_from), ('date_to', '<=', batch_sheet_obj.date_to), ('state', '!=', 'cancel'), ('employee_id', 'in', emp_ids.ids)]).mapped('employee_id').ids)

        emp_list = list(set(emp_ids.ids).difference(payslip_emp_ids))

        domains += [('id', 'in', emp_list)]

        return {'value': {'employee_ids': [(6, 0, emp_list)]}, 'domain': {
            'employee_ids': domains,
        }}

    def generate_att_sheet(self):
        self.ensure_one()
        batch_sheet_obj = self.env['batch.attendance.sheet'].browse(self.env.context.get('active_id'))

        if not self.employee_ids:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        sheet_obj = self.env['attendance.sheet']

        for em in self.employee_ids:
            contracts = em._get_contracts(batch_sheet_obj.date_from, batch_sheet_obj.date_to)
            if not em.contract_id.att_policy_id:
                raise UserError(_("Attendance policy not available in contract of '%s'." %(em.name)))

            sheet_obj.create(
                {
                    'employee_id': em.id,
                    'user_work_location_id': em.user_work_location_id.id,
                    'department_id': em.department_id.id,
                    'company_id': batch_sheet_obj.company_id.id,
                    'contract_id': em.contract_id.id,
                    'date_from': batch_sheet_obj.date_from,
                    'date_to': batch_sheet_obj.date_to,
                    'name': 'Attendance Sheet - %s - %s' % (em.name or '', format_date(self.env, batch_sheet_obj.date_from, date_format="MMMM y")),
                    'att_policy_id': em.contract_id.att_policy_id.id,
                    'gross_salary': contracts.gross_salary,
                    'basic_salary': contracts.wage,
                    'ot_day_count': contracts.ot_day_count,
                    'ot_daily_allowance': contracts.ot_daily_allowance,
                    'ot_daily_salary': contracts.ot_daily_salary,
                }
            )
            sheet_id = sheet_obj.search(
            [('employee_id', '=', em.id), ('state', '=', 'draft'),
             ('date_from', '=', batch_sheet_obj.date_from), ('date_to', '=', batch_sheet_obj.date_to)], limit=1)
            sheet_id.get_attendances()
            sheet_id.action_confirm()

        sheet_ids = sheet_obj.search(
            [('employee_id', 'in', self.employee_ids.ids), ('state', '=', 'confirm'),
             ('date_from', '=', batch_sheet_obj.date_from), ('date_to', '=', batch_sheet_obj.date_to)])

        batch_sheet_obj.att_sheet_ids = [(6, 0, sheet_ids.ids)]
        batch_sheet_obj.is_generate = True
