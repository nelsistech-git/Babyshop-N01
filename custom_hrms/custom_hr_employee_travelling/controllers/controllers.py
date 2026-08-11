# -*- coding: utf-8 -*-
# from odoo import http


# class HrEmployeeTravelling(http.Controller):
#     @http.route('/custom_hr_employee_travelling/custom_hr_employee_travelling/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_hr_employee_travelling/custom_hr_employee_travelling/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_hr_employee_travelling.listing', {
#             'root': '/custom_hr_employee_travelling/custom_hr_employee_travelling',
#             'objects': http.request.env['custom_hr_employee_travelling.custom_hr_employee_travelling'].search([]),
#         })

#     @http.route('/custom_hr_employee_travelling/custom_hr_employee_travelling/objects/<model("custom_hr_employee_travelling.hr_employee_travelling"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hr_employee_travelling.object', {
#             'object': obj
#         })
