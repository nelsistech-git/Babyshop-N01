from odoo import models


class InheritedResUsersCustomHREmployee(models.Model):
    _inherit = 'res.users'
    _description = 'Inherited Res Users Inherit Custom HR Employee'

    def action_create_employee(self):
        emp_obj = self.env['hr.employee'].search([('work_email', '=', self.login)], limit=1)

        if emp_obj:
            emp_obj.user_id = self.id
        else:
            self.ensure_one()
            self.env['hr.employee'].create(dict(
                name=self.name,
                work_email=self.login,
                address_home_id=self.partner_id.id,
                company_id=self.env.company.id,
                **self.env['hr.employee']._sync_user(self)
            ))
