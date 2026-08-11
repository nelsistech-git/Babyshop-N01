from odoo import fields, models, api, tools, _
from odoo.modules.module import get_module_resource
from dateutil.relativedelta import relativedelta


class InheritedHrApplicantOG(models.Model):
    """ Add employee & recruitment related fields in hr.employee & hr.recruitment model """
    _inherit = 'hr.applicant'

    def _get_employee_create_vals(self):
        vals = super()._get_employee_create_vals()
        vals['work_phone'] =self.partner_mobile
        vals['contact_no'] = self.partner_mobile
        vals['mobile_phone'] =self.partner_phone
        vals['work_email'] =self.email_from
        return vals

