from odoo import models, fields, _, api
#import time

class MapEmployeeWizard(models.TransientModel):
    _name = 'map.employee.wizard'
    _description = 'Map Employee Wizard'

    employee_name = fields.Char(string='Employee Name')
    employee_id = fields.Char(string='Employee ID')
    employee_email = fields.Char(string='Email')
    employee_mobile = fields.Char(string='Mobile (Personal)')
    related_user_id = fields.Many2one('res.users', string='Related User')
    address_home_id = fields.Many2one('res.partner', string='Private Address')

    @api.model
    def default_get(self, fields):
        res = super(MapEmployeeWizard, self).default_get(fields)
        emp_id = self.env.context.get('active_id')
        emp_obj = self.env['hr.employee'].search([('id', '=', emp_id)], limit=1)

        user_obj = self.env['res.users'].search([('login', '=', emp_obj.work_email)], limit=1)

        user_id = 0
        address_home_id = 0

        if user_obj:
            user_id = user_obj.id
            address_home_id = user_obj.partner_id.id
        else:
            if emp_obj.user_id:
                user_id = emp_obj.user_id.id
            if emp_obj.address_home_id:
                address_home_id = emp_obj.address_home_id.id

        res.update({
            'employee_name': emp_obj.display_name,
            'employee_email': emp_obj.work_email,
            'employee_mobile': emp_obj.contact_no,
            'employee_id': emp_obj.id_card_no,
            'related_user_id': user_id or None,
            'address_home_id': address_home_id or None
        })
        return res

    def action_confirm(self):
        emp_id = self.env.context.get('active_id')
        emp_obj = self.env['hr.employee'].sudo().search([('id', '=', emp_id)], limit=1)

        user_obj = self.env['res.users'].sudo().search([('login', '=', emp_obj.work_email)], limit=1)

        if user_obj:
            emp_obj.user_id = user_obj.id
            emp_obj.address_home_id = user_obj.partner_id.id
            user_obj.partner_id.is_employee = True
            user_obj.partner_id.employee_id = self.employee_id
        else:
            new_user = self.env['res.users'].create({
                'name': emp_obj.display_name,
                'login': emp_obj.work_email,
                'partner_id': emp_obj.work_contact_id.id or None,
            })
            emp_obj.user_id = new_user.id
            #new_user.partner_id.email = new_user.login
            #new_user.partner_id.mobile = self.employee_mobile
            #new_user.partner_id.is_employee = True
            #new_user.partner_id.employee_id = self.employee_id
            emp_obj.address_home_id = emp_obj.work_contact_id.id or None
            emp_obj.work_contact_id.is_employee = True
            emp_obj.work_contact_id.employee_id = emp_obj.id_card_no
            emp_obj.work_contact_id.mobile = emp_obj.contact_no

    def action_confirm_all(self):
        emp_obj_all = self.env['hr.employee'].search([('address_home_id', '=', None)], limit=100)
        res_user_obj = self.env['res.users'].sudo()
        for emp_obj in emp_obj_all:
            try:
                user_obj = res_user_obj.search([('login', '=', emp_obj.work_email)], limit=1)
            except:
                #print('emp_obj.work_email------',emp_obj.work_email)
                continue

            if user_obj:
                emp_obj.user_id = user_obj.id
                emp_obj.address_home_id = user_obj.partner_id.id
                user_obj.partner_id.is_employee = True
                user_obj.partner_id.employee_id = emp_obj.id_card_no
            else:
                try:
                    new_user = res_user_obj.create({
                        'name': emp_obj.name,
                        'login': emp_obj.work_email,
                        'partner_id': emp_obj.work_contact_id.id or None
                    })
                    emp_obj.user_id = new_user.id
                    # new_user.partner_id.email = new_user.login
                    # new_user.partner_id.mobile = self.employee_mobile
                    # new_user.partner_id.is_employee = True
                    # new_user.partner_id.employee_id = self.employee_id
                    emp_obj.address_home_id = emp_obj.work_contact_id.id or None
                    emp_obj.work_contact_id.is_employee = True
                    emp_obj.work_contact_id.employee_id = emp_obj.id_card_no
                    emp_obj.work_contact_id.mobile = emp_obj.contact_no

                    #self.env.cr.commit()
                    #time.sleep(1)
                except:
                    continue


