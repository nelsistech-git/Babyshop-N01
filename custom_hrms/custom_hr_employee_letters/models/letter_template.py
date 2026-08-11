# coding=utf-8
from odoo import models, fields, api
from odoo.addons.helper import validator


class LetterTemplate(models.Model):
    """ Template for Employee letters """
    _name = 'employee.letter.template'
    _description = 'Employee Letter Template'
    _rec_name = 'name'

    template_type = fields.Selection([
        ('confirmation_service', 'Confirmation of Service'),
        ('dismissal_letter', 'Dismissal Letter'),
        ('introduction_letter', 'Introduction Letter (LOI)'),
        ('demotion_letter', 'Letter of Demotion'),
        ('release_letter', 'Letter of Release & Certificate'),
        ('salary_refixation', 'Letter of Salary Re-Fixation'),
        ('offer_letter', 'Offer Letter'),
        ('termination_letter', 'Termination Letter'),
        ('transfer_letter', 'Transfer Letter'),
        ('visa_request_letter', 'Visa Request Letter'),
        ('warning_letter', 'Warning Letter'),
        ('resignation_acceptance', 'Acceptance of Resignation and Charge Handover'),
        ('charge_handover', 'Charge Handover And Transfer'),
        ('contract_letter', 'Contract Letter'),
        ('promotion_transfer', 'Promotion And Transfer'),
        ('increment_letter', 'Letter of Salary Increment'),
        ('decrement_letter', 'Letter of Salary Decrement'),
        ('default', 'Select Type')
    ], string='Letter Type', default="default", required=True, copy=False)
    type = fields.Selection([
        ('head_office', 'Head Office'),
        ('shop', 'Branch/Shop')
    ], required=True, string="Type")

    name = fields.Char(string="Letter Name", copy=False, default="_", required=True, help="Title can be maximum 120 characters")

    description = fields.Html(string="Description")
    active = fields.Boolean(default=True)

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()

    @api.constrains('template_type', 'type')
    def _check_unique_constraint_template_type(self):
        msg = "This 'Letter Type' of the 'Type'"
        envobj = self.env['employee.letter.template']
        conditionlist = [('template_type', '=', self.template_type), ('type', '=', self.type), '|',
                         ('active', '=', True), ('active', '=', False)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = "Letter Name '%s'" % (self.name)
        envobj = self.env['employee.letter.template']
        conditionlist = [('name', '=ilike', self.name), '|', ('active', '=', True), ('active', '=', False)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)

    @api.constrains('description')
    def _check_template_description_length(self):
        limit = 10000
        record = self.description
        field_name = "Description"
        validator._check_length_with_clean_htmltag(self, record, limit, field_name)
