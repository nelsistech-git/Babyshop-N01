from odoo import fields, models, api, _
from datetime import datetime
from odoo.addons.helper import validator


class InheritedHrLeaveTypeInheritCustomHrLeave(models.Model):
    _inherit = "hr.leave.type"
    _description = "HR Leave Type"

    def get_years(self):
        """ Get company start year and display_year from res_company """
        year_list = []
        company = self.env.company
        if company.start_date:
            # start_year = int(str(company.start_date).split("-")[0])
            start_year = company.start_date.year
            if company.display_year:
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, i
                    year_list.append(list_format)
        else:
            if company.display_year:
                start_year = datetime.today().year
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, i
                    year_list.append(list_format)
            else:
                list_format = '%s' % datetime.today().year, datetime.today().year
                year_list.append(list_format)
        return year_list

    # sequence = fields.Integer(string='Sequence', default=1)
    type_code = fields.Char(string='Code', default='')
    year = fields.Selection(get_years, string='Year', default=str(datetime.today().year))
    is_allow_probation = fields.Boolean(string="Is Allow Probation?")
    is_allow_leave_encashment = fields.Boolean(string="Is Allow Leave Encashment?")
    is_auto_allocate = fields.Boolean(string="Is Auto Allocate?")

    auto_allocate_days = fields.Float('Auto Allocate Days', default=1.00)
    auto_allocate_based_on = fields.Selection([
        ('join_date', 'Joining Date'),
        ('confirm_date', 'Confirmation Date'),
    ], 'Auto Allocate Based on', default='join_date')
    # is_dept_approval = fields.Boolean(
    #     string='Department/Responsible/Reporting Manager Approval',
    #     default=True,
    #     help="Responsible of leave approval or Reporting manager of the employee"
    # )
    is_female_only = fields.Boolean(string="Only Female Used?")

    exclude_weekends = fields.Boolean(
        string='Exclude Weekends', default=True,
        help=('If enabled, weekends are skipped in leave days calculation.')
    )
    exclude_ph = fields.Boolean(
        string='Exclude Public Holiday', default=False,
        help=('If enabled, Public Holiday are skipped in leave days calculation.')
    )

    # @api.constrains('year', 'validity_start', 'validity_stop')
    # def date_constrains(self):
    #     start_date_year = datetime.strptime(str(self.validity_start), '%Y-%m-%d').strftime('%Y')
    #     end_date_year = datetime.strptime(str(self.validity_stop), '%Y-%m-%d').strftime('%Y')
    #
    #     if start_date_year == end_date_year:
    #         if start_date_year != self.year:
    #             raise ValidationError(_('Validity from date and to date must be of the year %s.') % self.year)
    #     else:
    #         raise ValidationError(_('Validity from date and to date must be of the same year.'))

    # @api.constrains('sequence')
    # def _check_unique_constraint_name(self):
    #     msg = 'Sequence of "%s"' % self.name
    #     envobj = self.env['hr.leave.type']
    #     year = self.year
    #     conditionlist = [('sequence', '=', self.sequence), ('active', '=', True)]
    #     validator.check_duplicate_value(self, envobj, conditionlist, msg)

    # ('year', '=', year),
    @api.constrains('type_code')
    def _check_unique_constraint_type_code(self):
        msg = 'Code of "%s"' % self.name
        envobj = self.env['hr.leave.type']
        year = self.year
        conditionlist = [('company_id', '=', self.env.user.company_id.id),
                         ('type_code', '=', self.type_code),
                         ('active', '=', True)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)

    # ('year', '=', year),
    # def name_get(self):
    #     result = []
    #
    #     for lt in self:
    #         leave_type_display_name = lt.name
    #         if lt.year:
    #             leave_type_display_name = lt.name + ' (' + lt.year + ')'
    #
    #         result.append((lt.id, leave_type_display_name))
    #
    #     if not self._context.get('employee_id'):
    #         return result
    #
    #     for record in self:
    #         name = record.name
    #         if record.year:
    #             name = name + ' (' + record.year + ')'
    #         if record.allocation_type != 'no':
    #             name = "%(name)s (%(count)s)" % {
    #                 'name': name,
    #                 'count': _('%g remaining out of %g') % (
    #                     float_round(record.virtual_remaining_leaves, precision_digits=2) or 0.0,
    #                     float_round(record.max_leaves, precision_digits=2) or 0.0,
    #                 ) + (_(' hours') if record.request_unit == 'hour' else _(' days'))
    #             }
    #             result.append((record.id, name))
    #     return result
