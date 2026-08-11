# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, date, time
import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    _name = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    def _get_available_contracts_domain(self):
        return [('contract_ids.state', '=', 'open'), ('company_id', '=', self.env.company.id)]

    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    department_id = fields.Many2one('hr.department', string='Department')
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees', required=True)
    structure_id = fields.Many2one('hr.payroll.structure', string='Salary Structure')

    @api.model
    def default_get(self, fields):
        res = super(HrPayslipEmployees, self).default_get(fields)
        batch_payslip_obj = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
        res['user_work_location_id'] = batch_payslip_obj.user_work_location_id.id
        res['department_id'] = batch_payslip_obj.department_id.id
        return res

    @api.onchange('user_work_location_id', 'department_id')
    def _onchange_employees(self):
        domains = self._get_available_contracts_domain()

        batch_payslip_obj = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        if batch_payslip_obj.user_work_location_id:
            domains += [('user_work_location_id', '=', batch_payslip_obj.user_work_location_id.id)]

        if batch_payslip_obj.department_id:
            domains += [('department_id', '=', batch_payslip_obj.department_id.id)]

        emp_ids = self.env['hr.employee'].search(domains)

        payslip_emp_ids = set(self.env['hr.payslip'].search([('date_to', '>=', batch_payslip_obj.date_start), ('date_to', '<=', batch_payslip_obj.date_end), ('state', '!=', 'cancel'), ('employee_id', 'in', emp_ids.ids)]).mapped('employee_id').ids)

        emp_list = list(set(emp_ids.ids).difference(payslip_emp_ids))

        domains += [('id', 'in', emp_list)]

        return {'value': {'employee_ids': [(6, 0, emp_list)]}, 'domain': {
            'employee_ids': domains,
        }}

    def _check_undefined_slots(self, work_entries, payslip_run):
        """
        Check if a time slot in the contract's calendar is not covered by a work entry
        """
        work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in work_entries:
            work_entries_by_contract[work_entry.contract_id] |= work_entry

        for contract, work_entries in work_entries_by_contract.items():
            calendar_start = pytz.utc.localize(datetime.combine(max(contract.date_start, payslip_run.date_start), time.min))
            calendar_end = pytz.utc.localize(datetime.combine(min(contract.date_end or date.max, payslip_run.date_end), time.max))
            outside = contract.resource_calendar_id._attendance_intervals(calendar_start, calendar_end) - work_entries._to_intervals()
            if outside:
                raise UserError(_("Some part of %s's calendar is not covered by any work entry. Please complete the schedule.") % contract.employee_id.name)

    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': from_date.strftime('%B %Y'),
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        if not self.employee_ids:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']

        contracts = self.employee_ids._get_contracts(payslip_run.date_start, payslip_run.date_end, states=['open', 'close'])
        contracts._generate_work_entries(payslip_run.date_start, payslip_run.date_end)
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '<=', payslip_run.date_end),
            ('date_stop', '>=', payslip_run.date_start),
            ('employee_id', 'in', self.employee_ids.ids),
        ])
        self._check_undefined_slots(work_entries, payslip_run)

        validated = work_entries.action_validate()
        # if not validated:
        #     raise UserError(_("Some work entries could not be validated."))

        default_values = Payslip.default_get(Payslip.fields_get())
        for contract in contracts:
            values = dict(default_values, **{
                'employee_id': contract.employee_id.id,
                'credit_note': payslip_run.credit_note,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
                'contract_id': contract.id,
                'struct_id': self.structure_id.id or contract.structure_type_id.default_struct_id.id,
            })
            payslip = self.env['hr.payslip'].new(values)
            payslip._onchange_employee()
            values = payslip._convert_to_write(payslip._cache)
            payslips += Payslip.create(values)
        payslips.compute_sheet()
        payslip_run.state = 'verify'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }
