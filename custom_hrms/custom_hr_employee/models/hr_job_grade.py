# coding=utf-8
from odoo import fields, models, api
from odoo.addons.helper import validator


class HRJobGrade(models.Model):
    """ HR job grade fields list """

    _name = "hr.job.grade"
    _description = "HR Job Grade"

    name = fields.Char(string="Job Grade", required=True, trim=True)
    grade_type = fields.Many2one("hr.job.grade.type", string="Grade Type")
    job_level = fields.Many2one("hr.job.level", string="Job Level")
    line_ids = fields.One2many('hr.job.grade.line', 'job_grade', required=True)

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = 'Job Grade "%s"' % self.name
        envobj = self.env['hr.job.grade']
        conditionlist = [('name', '=', self.name)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)
