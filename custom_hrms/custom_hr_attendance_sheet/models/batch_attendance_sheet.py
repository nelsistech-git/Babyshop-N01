from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.tools.misc import format_date

from odoo import fields, models, api, _


class BatchAttendanceSheet(models.Model):
    _name = 'batch.attendance.sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Batch Attendance Sheet'
    _order = 'date_to desc'

    name = fields.Char()
    att_sheet_ids = fields.One2many('attendance.sheet', 'batch_att_sheet_id', string='Attendance Sheets', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft', tracking=True)
    date_from = fields.Date(string='Date From', required=True, readonly=True,
                            # states={'draft': [('readonly', False)]},
                            default=lambda self: fields.Date.to_string(
                                date.today().replace(day=1) - relativedelta(months=1)))
    date_to = fields.Date(string='Date To', required=True, readonly=True,
                          # states={'draft': [('readonly', False)]},
                          default=lambda self: fields.Date.to_string(
                              ((date.today().replace(day=1) - relativedelta(months=1)) + relativedelta(months=+1, day=1,
                                                                                                       days=-1))))
    att_sheet_count = fields.Integer(compute='_compute_att_sheet_count')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True,
                                 default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', string='Department')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    is_payslip_done = fields.Boolean(string='Payslip Done')
    is_generate = fields.Boolean(string='Is Generate', default=False)

    @api.onchange('user_work_location_id', 'date_from', 'date_to')
    def onchange_name(self):
        self.name = 'Batch Attendance Sheet: %s - %s' % (
        self.user_work_location_id.display_name or '', format_date(self.env, self.date_to,
                                                              date_format="MMMM y"))
    def unlink(self):
        for rec in self:
            if any(rec.filtered(lambda rec: rec.state not in ('draft'))):
                raise UserError(_('%s can be deleted in draft state.') % rec.name)
        return super(BatchAttendanceSheet, self).unlink()

    def _compute_att_sheet_count(self):
        for sheet_id in self:
            sheet_id.att_sheet_count = len(self.att_sheet_ids)

    def action_draft(self):
        return self.write({'state': 'draft'})

    def action_done(self):
        if self._are_payslips_ready():
            self.write({'state': 'done'})

    def action_payslip_done(self):
        for rec in self.att_sheet_ids.payslip_id:
            # net_sal_line = rec.line_ids.filtered(lambda x: x.code == 'NET')
            # if rec.state != 'done':
            #     if net_sal_line.amount > 0:
            #         rec.action_payslip_done()
            #     else:
            #         continue
            if rec.state != 'done':
                #try:
                rec.action_payslip_done()
                # except:
                #     continue
        self.is_payslip_done = True

    def action_validate(self):
        for rec in self.att_sheet_ids:
            if rec.state not in ('draft', 'approve', 'cancel'):
                rec.action_approve()
        self.action_done()

    def action_open_att_sheets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "attendance.sheet",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [['id', 'in', self.att_sheet_ids.ids]],
            "name": "Attendance Sheets",
        }

    def action_open_payslips(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [['id', 'in', self.att_sheet_ids.mapped('payslip_id').ids]],
            "name": "Employee Payslips",
        }

    def _are_payslips_ready(self):
        return all(sheet.state == 'done' for sheet in self.mapped('att_sheet_ids'))
