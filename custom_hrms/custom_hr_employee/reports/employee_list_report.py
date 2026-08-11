from odoo import fields, models, api, tools


class EmployeeList(models.Model):
    """ List View of Employee """
    _name = 'hr.employee.list'
    _description = 'Employee List'
    _auto = False
    
    employee_id = fields.Many2one('hr.employee', string="Employee Name", required=True)
    user_work_location_id = fields.Many2one('stock.location', string="Work/Job Location", related='employee_id.user_work_location_id', domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id')
    designation_id = fields.Many2one('hr.job', string="Designation", related='employee_id.job_id')
    master_id = fields.Char(string="Master ID", related='employee_id.identification_id')
    old_emp_id = fields.Char(string="Employee ID", related='employee_id.id_card_no')
    device_user_id = fields.Char(string="Biometric Device ID", related='employee_id.device_user_id')
    mobile_phone = fields.Char(string="Cell No. (Official)", related='employee_id.mobile_phone')
    contact_no = fields.Char(string="Mobile (Personal)", related='employee_id.contact_no')
    email = fields.Char(string='Email', related='employee_id.work_email')
    email_personal = fields.Char(string='Email (Personal)', related='employee_id.email_personal')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_employee_list')
        self._cr.execute("""
            CREATE OR REPLACE VIEW hr_employee_list AS (
                SELECT
                    row_number() OVER () as id,
                    emp.id AS employee_id
                FROM
                    hr_employee AS emp WHERE active=true                 
                ORDER BY
                    emp.name
            )
        """)

    @api.model
    def action_generate_employee_list_report(self):
        """ Action Method """
        tools.drop_view_if_exists(self._cr, 'hr_employee_list')
        self._cr.execute("""
            CREATE OR REPLACE VIEW hr_employee_list AS (
                SELECT
                    row_number() OVER () as id,
                    emp.id AS employee_id
                FROM
                    hr_employee AS emp WHERE active=true                   
                ORDER BY
                    emp.name
            )
        """)
        
        IrModelData = self.env['ir.model.data']
        tree_view_id = IrModelData._xmlid_to_res_id('custom_hr_employee.employee_list_report_view_tree')
        actionObject = self.env.ref('custom_hr_employee.employee_list_report_action')
        
        action = actionObject.sudo().read(
            ['name', 'help', 'res_model', 'target', 'domain', 'context', 'search_view_id'])
        if not action:
            action = {}
        else:
            action = action[0]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee List',
            # 'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'hr.employee.list',
            'views': [(tree_view_id, 'tree')],
            'target': 'current'
        }
