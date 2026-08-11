from odoo import api, fields, models
from odoo.addons.helper import validator


class HrDocumentType(models.Model):
    _name = 'hr.document.type'
    _description = 'Document Type'
    _order = 'name'

    name = fields.Char(string="Name", required=True, trim=True)

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = 'Name "%s"' % self.name
        envobj = self.env['hr.document.type']
        conditionlist = [('name', '=', self.name)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)


class HrEmployeeDocumentLine(models.Model):
    _name = "hr.employee.document.line"
    _description = "Employee Document Line"
    _rec_name = 'document_name'
    _order = 'doc_type, document_name'

    master_id = fields.Many2one('hr.employee', string='Employee', ondelete='restrict')
    doc_type = fields.Many2one('hr.document.type', string='Type', ondelete='restrict')
    document_name = fields.Char('Document Name')
    attachement_file_ids = fields.Many2many('ir.attachment', 'hr_employee_document_line_ir_attachments_rel',
                                            'emp_doc_line_id',
                                            'attachment_id', string='Attachments', help="Attach files here")

    def save(self):
        return {'type': 'ir.actions.act_window_close'}
