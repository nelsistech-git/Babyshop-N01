from odoo import models, fields, _
from odoo.exceptions import UserError

class InterCompanyTransferHistory(models.Model):
    _name = 'inter.company.transfer.history'
    #_inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Inter Company Employee Transfer History"
    _order = "id desc"
    _rec_name = 'employee_name'
    
    transfer_type = fields.Selection([
        ('in', 'IN'),
        ('out', 'OUT')
    ], string="Type", default='in', copy=False)
    transfer_reference = fields.Many2one('hr.transfer', string='OUT-Reference')
    in_reference = fields.Char(string='IN-Reference')
    
    employee_name = fields.Char(string='Employee Name')
    from_company = fields.Char(string='From Company')
    from_department = fields.Char(string='From Department')
    from_designation = fields.Char(string='From Designation')
    from_job_location = fields.Char(string='From Job Location')
    # from_job_location = fields.Char(string='From Job Location')
    device_user_id = fields.Char(string='Biometric Device ID', help='The ID Number of the user/employee in the device storage')
    identification_id = fields.Char(string='Master ID')
    id_card_no = fields.Char(string="Employee ID")
    door_card_no = fields.Char(string="Door Card No")
    
    work_email = fields.Char(string='Work Email')
    contact_no = fields.Char(string="Mobile (Personal)")
    initial_employment_date = fields.Date(string='Date of Joining')
    
    to_company = fields.Many2one('company.api.settings', string='To Company')
    #------------
    to_job_location = fields.Char(string='To Work/Job Location')
    to_department = fields.Char(string='To Department')
    to_designation = fields.Char(string='To Designation')
    to_resource_calendar = fields.Char(string='To Working Schedule')
    to_att_policy = fields.Char(string='To Attendance Policy')
    
    #used IN type creation in API
    to_job_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    to_department_id = fields.Many2one('hr.department', string='Department')
    to_designation_id = fields.Many2one('hr.job', string='Designation')
    to_resource_calendar_id = fields.Many2one('resource.calendar', string='Working Schedule')
    to_att_policy_id = fields.Many2one('hr.attendance.policy', string='Attendance Policy')
    
    requested_date = fields.Datetime(string='Requested Date')
    effected_date = fields.Date(string='Effected Date')
    note = fields.Char(string='Note')
    
    gross_salary = fields.Float(string='Gross Salary', default=0)
    total_residual_loan = fields.Float(string='Loan Amount', default=0) #not used
    advance_salary = fields.Float(string='Salary Advance', default=0) #not used
    residual_Salary = fields.Float(string='Salary Payables', default=0) #not used
    
    #--------------------
    #loan_summary
    def _get_loan_dr_acc(self):
        loan_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'loan'),('is_receive_dr', '=', True)])
        loan_dr_acc = loan_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', loan_dr_acc.ids)]
    def _get_loan_cr_acc(self):
        loan_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'loan'),('is_receive_cr', '=', True)])
        loan_cr_acc = loan_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', loan_cr_acc.ids)]    
    loan_dr_acc = fields.Many2one('account.account', string='Debit Account', domain=_get_loan_dr_acc)
    loan_cr_acc = fields.Many2one('account.account', string='Credit Account', domain=_get_loan_cr_acc)
    
    # loan_interest_summary
    def _get_loan_inst_dr_acc(self):
        loan_inst_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'loan_interest'),('is_receive_dr', '=', True)])
        loan_interest_dr_acc = loan_inst_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', loan_interest_dr_acc.ids)]
    def _get_loan_inst_cr_acc(self):
        loan_inst_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'loan_interest'),('is_receive_cr', '=', True)])
        loan_interest_cr_acc = loan_inst_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', loan_interest_cr_acc.ids)]    
    loan_interest_dr_acc = fields.Many2one('account.account', string='Debit Account(Interest)', domain=_get_loan_inst_dr_acc)
    loan_interest_cr_acc = fields.Many2one('account.account', string='Credit Account(Interest)', domain=_get_loan_inst_cr_acc)
    
    # salary_advance_summary
    def _get_sal_adv_dr_acc(self):
        salary_adb_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'salary_advance'),('is_receive_dr', '=', True)])
        salary_adv_dr_acc = salary_adb_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', salary_adv_dr_acc.ids)]
    def _get_sal_adv_cr_acc(self):
        salary_adb_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'salary_advance'),('is_receive_cr', '=', True)])
        salary_adv_cr_acc = salary_adb_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', salary_adv_cr_acc.ids)]    
    salary_adv_dr_acc = fields.Many2one('account.account', string='Debit Account(ADV)', domain=_get_sal_adv_dr_acc)
    salary_adv_cr_acc = fields.Many2one('account.account', string='Credit Account(ADV)', domain=_get_sal_adv_cr_acc)
    
    # tds_summary
    def _get_tds_dr_acc(self):
        tds_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'tds'),('is_receive_dr', '=', True)])
        tds_dr_acc = tds_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', tds_dr_acc.ids)]
    def _get_tds_cr_acc(self):
        tds_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'tds'),('is_receive_cr', '=', True)])
        tds_cr_acc = tds_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', tds_cr_acc.ids)]
    tds_dr_acc = fields.Many2one('account.account', string='Debit Account(TDS)', domain=_get_tds_dr_acc)
    tds_cr_acc = fields.Many2one('account.account', string='Credit Account(TDS)', domain=_get_tds_cr_acc)
    
    # pf_summary
    def _get_pf_dr_acc(self):
        pf_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'pf'),('is_receive_dr', '=', True)])
        pf_dr_acc = pf_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', pf_dr_acc.ids)]
    def _get_pf_cr_acc(self):
        pf_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'pf'),('is_receive_cr', '=', True)])
        pf_cr_acc = pf_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', pf_cr_acc.ids)]
    pf_dr_acc = fields.Many2one('account.account', string='Debit Account(PF)', domain=_get_pf_dr_acc)
    pf_cr_acc = fields.Many2one('account.account', string='Credit Account(PF)', domain=_get_pf_cr_acc)
    
    # salary_payable_summary
    def _get_sal_pay_dr_acc(self):
        salary_pay_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'salary_payable'),('is_receive_dr', '=', True)])
        salary_payable_dr_acc = salary_pay_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', salary_payable_dr_acc.ids)]
    def _get_sal_pay_cr_acc(self):
        salary_pay_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'salary_payable'),('is_receive_cr', '=', True)])
        salary_payable_cr_acc = salary_pay_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', salary_payable_cr_acc.ids)]
    salary_payable_dr_acc = fields.Many2one('account.account', string='Debit Account(Payable)', domain=_get_sal_pay_dr_acc)
    salary_payable_cr_acc = fields.Many2one('account.account', string='Credit Account(Payable)', domain=_get_sal_pay_cr_acc)
    
    #-----------------
    loan_balance = fields.Float(string='Loan Balance', default=0)
    loan_interest_balance = fields.Float(string='Loan Interest Balance', default=0)
    salary_adv_balance = fields.Float(string='Salary Advance Balance', default=0)
    tds_balance = fields.Float(string='TDS Balance', default=0)
    pf_balance = fields.Float(string='PF Balance', default=0)
    salary_payable_balance = fields.Float(string='Salary Payable Balance', default=0)
    
    leave_casual_balance = fields.Integer(string='Casual Leave Balance', default=0)
    leave_sick_balance = fields.Integer(string='Sick Leave Balance', default=0)
    leave_marriage_balance = fields.Integer(string='Marriage Leave Balance', default=0)
    
    is_receive_emp = fields.Boolean(string='Employee Received?', readonly=True, copy=False)
    receive_emp_id = fields.Many2one('hr.employee', string='Receive Employee Ref.')
    emp_private_address_id = fields.Many2one(related='receive_emp_id.address_home_id', string='Private Address')    
    is_create_contract = fields.Boolean(string='Contract Created?', readonly=True, copy=False)
    is_leave_create = fields.Boolean(string='Leave Created?', readonly=True, copy=False)
    is_create_journal = fields.Boolean(string='Accounts Updated?', readonly=True, copy=False)
    
    def action_receive_emp(self):
        emp_obj = self.env['hr.employee']
        for rec in self:
            rcv_emp_id = ''
            emp_row = emp_obj.search([('device_user_id', '=', self.device_user_id),'|',('active', '=', True),('active', '=', False)], limit=1)
            if emp_row:
                rcv_emp_id = emp_row[0].id
                vals = {'active': True}
                
                if rec.to_job_location_id:
                    vals['user_work_location_id'] = rec.to_job_location_id.id
                if rec.to_department_id:
                    vals['department_id'] = rec.to_department_id.id
                if rec.to_designation_id:
                    vals['job_id'] = rec.to_designation_id.id
                if rec.id_card_no:
                    vals['id_card_no'] = rec.id_card_no
                if rec.door_card_no:
                    vals['door_card_no'] = rec.door_card_no
                if rec.identification_id:
                    vals['identification_id'] = rec.identification_id
                if rec.work_email:
                    vals['work_email'] = rec.work_email
                if rec.contact_no:
                    vals['contact_no'] = rec.contact_no
                if rec.initial_employment_date:
                    vals['initial_employment_date'] = rec.initial_employment_date
                    
                emp_row[0].write(vals)
                
            else:
                vals = {'name': rec.employee_name,
                        'device_user_id': rec.device_user_id,
                        'identification_id': rec.identification_id,
                        'id_card_no': rec.id_card_no,
                        'door_card_no': rec.door_card_no,
                        'work_email': rec.work_email,
                        'contact_no': rec.contact_no,
                        'initial_employment_date': rec.initial_employment_date,
                        'active': True}
                        
                if rec.to_job_location_id:
                    vals['user_work_location_id'] = rec.to_job_location_id.id
                if rec.to_department_id:
                    vals['department_id'] = rec.to_department_id.id
                if rec.to_designation_id:
                    vals['job_id'] = rec.to_designation_id.id
                    
                emp_row = emp_obj.create(vals)
                if emp_row:
                    rcv_emp_id = emp_row[0].id
            #-----------            
            rec.write({'is_receive_emp': True, 'receive_emp_id': rcv_emp_id})
            rec.action_create_contract()
            
            
    def action_create_contract(self):        
        #-----------
        basic_value = 0
        hra_value = 0
        da_value = 0
        travel_value = 0
        meal_value = 0
        medical_value = 0
        pf_value = 0
        company_pf_value = 0
        festival_bonus_value = 0
        
        basic_row = self.env['hr.contract.particular.settings'].search([])
        for rec in basic_row:
            if rec.name == 'basic' and (rec.value > 0 and rec.value <= 100):
                basic_value = rec.value
            elif rec.name == 'hra' and (rec.value > 0 and rec.value <= 100):
                hra_value = rec.value
            elif rec.name == 'da' and (rec.value > 0 and rec.value <= 100):
                da_value = rec.value
            elif rec.name == 'travel' and (rec.value > 0 and rec.value <= 100):
                travel_value = rec.value
            elif rec.name == 'meal' and (rec.value > 0 and rec.value <= 100):
                meal_value = rec.value
            elif rec.name == 'medical' and (rec.value > 0 and rec.value <= 100):
                medical_value = rec.value
            elif rec.name == 'pf' and (rec.value > 0 and rec.value <= 100):
                pf_value = rec.value
            elif rec.name == 'company_pf' and (rec.value > 0 and rec.value <= 100):
                company_pf_value = rec.value
            elif rec.name == 'festival_bonus' and (rec.value > 0 and rec.value <= 100):
                festival_bonus_value = rec.value
        #-----------
        emp_contact_obj = self.env['hr.contract']
        # ('draft', 'New'),
        # ('open', 'Running'),
        # ('close', 'Expired'),
        # ('cancel', 'Cancelled')
        for rec in self:            
            contract_rows = emp_contact_obj.search([('employee_id', '=', self.receive_emp_id.id),('state', '!=', 'cancel')])
            if contract_rows:
                for cont in contract_rows:
                    cont.write({'state':'cancel'})
            
            #-----------
            vals = {'employee_id': rec.receive_emp_id.id,
                    'name': rec.receive_emp_id.name,
                    'department_id': rec.receive_emp_id.department_id.id if rec.receive_emp_id.department_id else None,
                    'resource_calendar_id': rec.to_resource_calendar_id.id if rec.to_resource_calendar_id else None,
                    'att_policy_id': rec.to_att_policy_id.id if rec.to_att_policy_id else None,
                    'gross_salary': rec.gross_salary,
                    'date_start': rec.effected_date,
                    'trial_date_end':None,
                    'state':'draft',
                    'wage':0,
                    'hra':0,
                    'da':0,
                    'travel_allowance':0,
                    'meal_allowance':0,
                    'medical_allowance':0,
                    'pf_deduction':0,
                    'company_pf_contribution':0,
                    'festival_bonus':0,
                    'structure_type_id':None
                    }
            #---------------
            if basic_value:
                vals['wage'] = round(rec.gross_salary * (basic_value / 100))
            if hra_value:
                vals['hra'] = round(rec.gross_salary * (hra_value / 100))
            if da_value:
                vals['da'] = round(rec.gross_salary * (da_value / 100))
            if travel_value:
                vals['travel_allowance'] = round(rec.gross_salary * (travel_value / 100))
            if meal_value:
                vals['meal_allowance'] = round(rec.gross_salary * (meal_value / 100))
            if medical_value:
                vals['medical_allowance'] = round(rec.gross_salary * (medical_value / 100))
            if pf_value:
                vals['pf_deduction'] = round(rec.gross_salary * (pf_value / 100))
            if company_pf_value:
                vals['company_pf_contribution'] = round(vals['pf_deduction'] * (company_pf_value / 100))
            if festival_bonus_value:
                vals['festival_bonus'] = round(rec.gross_salary * (festival_bonus_value / 100))
    
            vals['other_allowance'] = rec.gross_salary - (vals['wage'] + vals['hra'] + vals['da'] + vals['travel_allowance'] + vals['meal_allowance'] + vals['medical_allowance'])  #
            
            #-----------
            if rec.receive_emp_id.company_id:
                structure_types = self.env['hr.payroll.structure.type'].search(['|',('country_id', '=', rec.receive_emp_id.company_id.id),('country_id', '=', False)])
                if structure_types:
                    vals['structure_type_id'] = structure_types[0].id
            #-----------
            
            emp_contact_obj.create(vals)
            rec.write({'is_create_contract': True})
    
    def action_create_leave_allocation(self):
        #-----------
        leave_allocation_obj = self.env['hr.leave.allocation']
        for rec in self:
            casual_balance = rec.leave_casual_balance
            sick_balance = rec.leave_sick_balance
            marriage_balance = rec.leave_marriage_balance
            is_leave_create = False
            #------------
            if casual_balance > 0:
                leave_type = self.env['hr.leave.type'].search([('type_code', '=', 'CL')], limit = 1)
                if leave_type:
                    holiday_status_id = leave_type[0].id                    
                    #-----------
                    vals = {'holiday_type': 'employee',
                            'employee_id': rec.receive_emp_id.id,
                            'holiday_status_id': holiday_status_id,
                            'name': 'Casual Leave',
                            'allocation_type': 'regular',
                            'number_of_days': casual_balance
                            }                    
                    leave_allocation_obj.create(vals)
                    is_leave_create = True
            #------------ rec.receive_emp_id.company_id
            if sick_balance > 0:
                leave_type = self.env['hr.leave.type'].search([('type_code', '=', 'SL')], limit = 1)
                if leave_type:
                    holiday_status_id = leave_type[0].id                    
                    #-----------
                    vals = {'holiday_type': 'employee',
                            'employee_id': rec.receive_emp_id.id,
                            'holiday_status_id': holiday_status_id,
                            'name': 'Sick Leave',
                            'allocation_type': 'regular',
                            'number_of_days': sick_balance
                            }                    
                    leave_allocation_obj.create(vals)
                    is_leave_create = True
            #------------
            if marriage_balance > 0:
                leave_type = self.env['hr.leave.type'].search([('type_code', '=', 'ML')], limit = 1)
                if leave_type:
                    holiday_status_id = leave_type[0].id                    
                    #-----------
                    vals = {'holiday_type': 'employee',
                            'employee_id': rec.receive_emp_id.id,
                            'holiday_status_id': holiday_status_id,
                            'name': 'Marriage Leave',
                            'allocation_type': 'regular',
                            'number_of_days': marriage_balance
                            }                    
                    leave_allocation_obj.create(vals)
                    is_leave_create = True
            if is_leave_create == True:
                rec.write({'is_leave_create': True})
            else:
                raise UserError(_('Leave Balance not available or configuration needed!'))
                
                
    def create_journal_transfer_receive(self):        
        #-----------
        for rec in self:
            move_line = []
            
            if rec.emp_private_address_id:
                partner_id = rec.emp_private_address_id.id
            else:
                raise UserError(_('Private Address not mapped for employee: %s') % rec.receive_emp_id.name)
            
            journal_id = self.env['account.journal'].search([('code', '=', 'JRV')], limit=1)
            
            if not journal_id:
                journal_id = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
            
            # loan debit & credit account and balance
            if rec.loan_balance != 0:

                loan_debit_val = {
                    'account_id': rec.loan_dr_acc.id,
                    'debit': rec.loan_balance,
                    'credit': 0.0,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, loan_debit_val))

                loan_credit_val = {
                    'account_id': rec.loan_cr_acc.id,
                    'debit': 0.0,
                    'credit': rec.loan_balance,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, loan_credit_val))

            # loan interest debit & credit account and balance
            if rec.loan_interest_balance != 0:
                loan_inst_debit_val = {
                    'account_id': rec.loan_interest_dr_acc.id,
                    'debit': rec.loan_interest_balance,
                    'credit': 0.0,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, loan_inst_debit_val))

                loan_inst_credit_val = {
                    'account_id': rec.loan_interest_cr_acc.id,
                    'debit': 0.0,
                    'credit': rec.loan_interest_balance,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, loan_inst_credit_val))

            # salary advance debit & credit account and balance
            if rec.salary_adv_balance != 0:
                sal_adv_debit_val = {
                    'account_id': rec.salary_adv_dr_acc.id,
                    'debit': rec.salary_adv_balance,
                    'credit': 0.0,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, sal_adv_debit_val))

                sal_adv_credit_val = {
                    'account_id': rec.salary_adv_cr_acc.id,
                    'debit': 0.0,
                    'credit': rec.salary_adv_balance,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, sal_adv_credit_val))

            # tds debit & credit account and balance
            if rec.tds_balance != 0:
                tds_debit_val = {
                    'account_id': rec.tds_dr_acc.id,
                    'debit': rec.tds_balance,
                    'credit': 0.0,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, tds_debit_val))

                tds_credit_val = {
                    'account_id': rec.tds_cr_acc.id,
                    'debit': 0.0,
                    'credit': rec.tds_balance,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, tds_credit_val))

            # pf debit & credit account and balance
            if rec.pf_balance != 0:
                pf_debit_val = {
                    'account_id': rec.pf_dr_acc.id,
                    'debit': rec.pf_balance,
                    'credit': 0.0,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, pf_debit_val))

                pf_credit_val = {
                    'account_id': rec.pf_cr_acc.id,
                    'debit': 0.0,
                    'credit': rec.pf_balance,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, pf_credit_val))

            # salary payable debit & credit account and balance
            if rec.salary_payable_balance != 0:
                sal_pay_debit_val = {
                    'account_id': rec.salary_payable_dr_acc.id,
                    'debit': rec.salary_payable_balance,
                    'credit': 0.0,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, sal_pay_debit_val))

                sal_pay_credit_val = {
                    'account_id': rec.salary_payable_cr_acc.id,
                    'debit': 0.0,
                    'credit': rec.salary_payable_balance,
                    'partner_id': partner_id,
                    'name': rec.employee_name,
                    #'exclude_from_invoice_tab': False,
                }
                move_line.append((0, 0, sal_pay_credit_val))
            if rec.loan_balance != 0 or rec.loan_interest_balance != 0 or rec.salary_adv_balance != 0 or rec.tds_balance != 0 or rec.pf_balance != 0 or rec.salary_payable_balance != 0:
                # journal creation
                self.env['account.move'].create({
                    'ref': rec.employee_name,
                    'name': '/',
                    'partner_id': partner_id,
                    'journal_id': journal_id.id,
                    'line_ids': move_line,
                })
            
            rec.write({'is_create_journal': True})
            
    
    def action_create_journal_entry(self):
        return False
            