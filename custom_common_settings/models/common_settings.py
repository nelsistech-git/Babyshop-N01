from odoo import models, fields, api
from odoo.addons.helper import validator


class CustomCommonSettings(models.Model):
    _name = "custom.common.settings"
    _description = "Custom Common Settings"
    _order = "sequence"

    sequence = fields.Integer(index=True, help="Give the sequence no.", default=1)
    code = fields.Integer(required=True, string='Code')
    key = fields.Selection([
        ('particular_bill', 'Enable Particular Bill'),
        ('auto_bill_post', 'Enable Auto Bill Post'),
        ('allow_create_auto_bill', 'Enable Auto Create Bill'),
        ('auto_invoice_post', 'Enable Auto Invoice Post'),
        ('hide_check_availability_warning', 'Hide Check Availability Warning'),
        ('coa_reports_config', 'Enable COA Report Config'),
        ('po_backdate_allowed', 'PO Backdate Allow'),
        ('sale_backdate_allowed', 'Sale Backdate Allow'),
        ('transfer_backdate_allowed', 'Transfer Backdate Allow'),
        ('inventory_backdate_allowed', 'Inventory Backdate Allow'),
        ('production_backdate_allowed', 'Production Backdate Allow'),
        ('requisition_backdate_allowed', 'Requisition Backdate Allow'),
        ('pr_from_requisition', 'Allow Purchase Request from Requisition'),
        ('ot_auto_approve', 'Overtime Auto Approve?'),
        ('upcoming_date_attendance_allow', 'Upcoming Date Attendance Allow?'),
        ('is_rostering_attendance_process', 'Rostering Attendance Process?'),
        ('allow_create_po_from_bill', 'Allow Create PO From Bill?'),
        ('allow_create_so_from_invoice', 'Allow Create SO From Invoice?'),
        ('hr_reports_order_by_employee_id', 'HR Reports Order By Employee ID'),
        ('recruitment_auto_update', 'Recruitment Update from Requisition')
    ], string='Key', copy=False, index=True)
    value = fields.Boolean(default=False, string="Value")

    @api.onchange('value')
    def _onchange_value(self):
        if self.key == 'particular_bill' and self.value == True:
            self.env.cr.execute("""UPDATE res_partner SET is_po_cost = False""", )

    @api.constrains('code')
    def _check_unique_code(self):
        for rec in self:
            msg = 'Key "%s"' % rec.key
            envobj = self.env['custom.common.settings']
            conditionlist = [('key', '=', rec.key)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)
