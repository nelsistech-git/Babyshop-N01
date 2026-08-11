from odoo import fields, models, api, _
from odoo.exceptions import UserError


class BatchEmployeeBonusWizard(models.TransientModel):
    _name = 'batch.employee.bonus.wizard'
    _description = 'Batch Employee Bonus Wizard'

    def _get_available_contracts_domain(self):
        return [('contract_ids.state', 'in', ('open', 'close')), ('company_id', '=', self.env.company.id)]

    bonus_batch_id = fields.Many2one('batch.hr.employee.bonus', string='Batch Bonus')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    department_id = fields.Many2one('hr.department', string='Department')
    bonus_type_id = fields.Many2one('hr.employee.bonus.type', 'Bonus Type')
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_batch_emp_bonus_rel', 'batch_emp_bonus_id',
                                    'employee_id', 'Employee(s)', required=True)
    bonus_date = fields.Date(string='Bonus Date')

    calculation_type = fields.Selection(related='bonus_type_id.calculation_type', string='Calculation Type')
    percentage_from_settings = fields.Boolean('Percentage from settings?',
                                              related='bonus_type_id.percentage_from_settings')
    settings_type = fields.Selection(string='Settings Type', related='bonus_type_id.settings_type')
    allowed_employee_type_ids = fields.Many2many('hr.employee.type', related='bonus_type_id.allowed_employee_type_ids',
                                                 string='Allowed Employee Type/Category')

    based_on_type = fields.Selection(string='Based On', related='bonus_batch_id.based_on_type')
    amount_percentage = fields.Float(related='bonus_batch_id.amount_percentage')

    @api.model
    def default_get(self, fields):
        res = super(BatchEmployeeBonusWizard, self).default_get(fields)
        batch_obj = self.env['batch.hr.employee.bonus'].browse(self.env.context.get('active_id'))
        res['bonus_batch_id'] = batch_obj.id
        res['user_work_location_id'] = batch_obj.user_work_location_id.id
        res['department_id'] = batch_obj.department_id.id
        res['bonus_type_id'] = batch_obj.bonus_type_id.id
        res['bonus_date'] = batch_obj.bonus_date
        return res

    @api.onchange('user_work_location_id', 'department_id')
    def _onchange_employees(self):
        domains = self._get_available_contracts_domain()

        batch_hr_emp_bonus_obj = self.env['batch.hr.employee.bonus'].browse(self.env.context.get('active_id'))
        if batch_hr_emp_bonus_obj.user_work_location_id:
            domains += [('user_work_location_id', '=', batch_hr_emp_bonus_obj.user_work_location_id.id)]
        if batch_hr_emp_bonus_obj.department_id:
            domains += [('department_id', '=', batch_hr_emp_bonus_obj.department_id.id)]
        if batch_hr_emp_bonus_obj.bonus_type_id:
            domains += [('employee_type_id', 'in', batch_hr_emp_bonus_obj.allowed_employee_type_ids.ids)]

        emp_ids = self.env['hr.employee'].search(domains)

        #  skip already exist
        emp_bonus_ids = set(self.env['hr.employee.bonus'].search(
            [('date', '=', batch_hr_emp_bonus_obj.bonus_date), ('state', '!=', 'cancelled'),
             ('employee_id', 'in', emp_ids.ids)]).mapped('employee_id').ids)

        emp_list = list(set(emp_ids.ids).difference(emp_bonus_ids))

        domains += [('id', 'in', emp_list)]

        return {'value': {'employee_ids': [(6, 0, emp_list)]}, 'domain': {'employee_ids': domains}}

    def generate_emp_bonus(self):
        self.ensure_one()
        batch_hr_emp_bonus_obj = self.env['batch.hr.employee.bonus'].browse(self.env.context.get('active_id'))
        if not batch_hr_emp_bonus_obj:
            raise UserError(_("Batch ID not found!"))
        else:
            batch_emp_bonus_id = batch_hr_emp_bonus_obj.id

        if not self.employee_ids:
            raise UserError(_("Employee not available in this Batch bonus!"))
        else:
            pass

        emp_bonus_obj = self.env['hr.employee.bonus']
        bonus_sett_obj = self.env['hr.bonus.settings']

        bonus_type_id = batch_hr_emp_bonus_obj.bonus_type_id.id
        based_on_type = None
        settings_type = batch_hr_emp_bonus_obj.bonus_type_id.settings_type
        calculation_type = batch_hr_emp_bonus_obj.calculation_type
        bonus_date = batch_hr_emp_bonus_obj.bonus_date
        percentage_from_settings = batch_hr_emp_bonus_obj.percentage_from_settings
        uid = self.env.uid

        for em in self.employee_ids:
            joining_date = em.initial_employment_date

            if not em.contract_id:
                raise UserError(_("Contract is not available of the Employee '%s'!" % (em.name)))
            else:
                employee_type_id = em.employee_type_id.id
                contract_id = em.contract_id.id
                gross_salary = em.contract_id.gross_salary
                basic_salary = em.contract_id.wage

                reference = ''
                if calculation_type == 'percentage':  # percentage calculation
                    if not percentage_from_settings:  # percentage but not from settings
                        amount_percentage = batch_hr_emp_bonus_obj.amount_percentage
                        based_on_type = batch_hr_emp_bonus_obj.bonus_type_id.based_on_type
                        if based_on_type == 'gross':
                            amount = gross_salary
                        else:
                            amount = basic_salary

                        bonus_amount = amount * (amount_percentage / 100)  # * self.quantity

                    else:  # percentage but value from settings
                        try:
                            service_length_day = (bonus_date - joining_date).days
                        except:
                            service_length_day = 0

                        settings_domain = [('head_id', '=', bonus_type_id)]
                        if settings_type == 'emp_type':
                            settings_domain.append(('employee_type_id', '=', employee_type_id))
                        elif settings_type == 'serv_len':
                            settings_domain.append(('days_from', '<=', service_length_day))
                            settings_domain.append(('days_to', '>=', service_length_day))
                        elif settings_type == 'serv_len_emp_type':
                            settings_domain.append(('employee_type_id', '=', employee_type_id))
                            settings_domain.append(('days_from', '<=', service_length_day))
                            settings_domain.append(('days_to', '>=', service_length_day))
                        else:
                            raise UserError(
                                _("Settings type is not available of the Bonus type for Employee '%s'!" % (em.name)))

                        bonus_sett_row = bonus_sett_obj.sudo().search(settings_domain, limit=1)
                        if not bonus_sett_row:
                            raise UserError(
                                _("Bonus settings is not available of the Bonus type for Employee '%s'!" % (em.name)))
                        else:
                            amount_percentage = bonus_sett_row[0].amount_percentage
                            based_on_type = bonus_sett_row[0].based_on_type
                            reference = '{0}'.format(bonus_sett_row[0].reference or '')

                            if based_on_type == 'gross':
                                amount = gross_salary
                            else:
                                amount = basic_salary

                            bonus_amount = amount * (amount_percentage / 100)  # * self.quantity

                else:  # fixed calculation
                    amount_percentage = batch_hr_emp_bonus_obj.amount_percentage
                    bonus_amount = amount_percentage  # * batch_hr_emp_bonus_obj.quantity

                emp_bonus_obj.create(
                    {
                        'batch_emp_bonus_id': batch_emp_bonus_id,
                        'bonus_type_id': bonus_type_id,
                        'employee_id': em.id,
                        'employee_type_id': employee_type_id,
                        'initial_employment_date': joining_date,
                        'contract_id': contract_id,
                        'date': bonus_date,
                        'based_on_type': based_on_type,
                        'amount_percentage': amount_percentage,
                        'quantity': 1.0,
                        'bonus_amount': round(bonus_amount, 0),
                        'gross_salary': gross_salary,
                        'basic_salary': basic_salary,
                        'reference': reference,
                        'user_id': uid
                    }
                )

        #batch_hr_emp_bonus_obj.is_generate = True
