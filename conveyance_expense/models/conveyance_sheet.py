from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ConveyanceSheet(models.Model):
    _name = 'conveyance.sheet'
    _description = 'Conveyance Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reference',
        readonly=True,
        default='New',
        copy=False,
    )
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        tracking=True,
    )
    designation = fields.Many2one(
        comodel_name='hr.job',
        string='Designation',
    )
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    expense_id = fields.Many2one(
        comodel_name='hr.expense',
        string='Linked Expense',
        ondelete='set null',
    )
    line_ids = fields.One2many(
        comodel_name='conveyance.sheet.line',
        inverse_name='sheet_id',
        string='Conveyance Lines',
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('supervisor', 'Accounts'),
            ('vice_president', 'Management-Authorized By'),
            ('ceo', 'CFO'),
            ('approved', 'Approved'),
            ('posted', 'Posted'),
            ('done', 'Done'),
            ('refused', 'Refused'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    journal_entry_ids = fields.Many2many(
        comodel_name='account.move',
        string='Journal Entries',
        copy=False,
    )
    vendor_bill_count = fields.Integer(
        string='Vendor Bills',
        compute='_compute_vendor_bill_count',
    )
    refuse_reason = fields.Char(string='Refuse Reason', tracking=True)

    @api.depends('line_ids.total_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('total_amount'))

    def _compute_vendor_bill_count(self):
        for rec in self:
            rec.vendor_bill_count = len(rec.journal_entry_ids)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.job_id:
                rec.designation = rec.employee_id.job_id
            else:
                rec.designation = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('conveyance.sheet') or 'New'
            if vals.get('employee_id') and not vals.get('designation'):
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                if employee.job_id:
                    vals['designation'] = employee.job_id.id
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_('No line items found. Please add at least one line.'))
            rec.state = 'supervisor'

    def action_approve_supervisor(self):
        for rec in self:
            if not self.env.user.has_group('conveyance_expense.group_conveyance_supervisor'):
                raise UserError(_('Only Approved by can approve this stage.'))
            rec.state = 'vice_president'

    def action_approve_vice_president(self):
        for rec in self:
            if not self.env.user.has_group('conveyance_expense.group_conveyance_vice_president'):
                raise UserError(_('Only management-Authorized by can approve this stage.'))
            rec.state = 'ceo'

    def action_approve_ceo(self):
        for rec in self:
            if not self.env.user.has_group('conveyance_expense.group_conveyance_ceo'):
                raise UserError(_('Only CFO can approve this stage.'))
            rec.state = 'approved'
        self.action_post_journal_entries()

    def action_post_journal_entries(self):
        for rec in self:
            if rec.state not in ('approved', 'ceo'):
                raise UserError(_('Only approved sheets can be posted.'))
            if not rec.line_ids:
                raise UserError(_('No line items found.'))

            employee = rec.employee_id
            partner = (
                employee.sudo().address_home_id
                or employee.sudo().work_contact_id
                or (employee.sudo().user_id and employee.sudo().user_id.partner_id)
            )
            if not partner:
                raise UserError(_(
                    'Employee "%s" has no home address, work contact, or linked user. '
                    'Please set a private address on the employee form.'
                ) % employee.name)

            journal = rec.env['account.journal'].sudo().search([
                ('type', 'in', ['purchase', 'general']),
                ('company_id', '=', rec.company_id.id),
            ], limit=1)
            if not journal:
                raise UserError(_('No Purchase or General journal found.'))

            expense_account = rec.env['account.account'].sudo().search([
                ('account_type', '=', 'expense'),
                ('company_id', '=', rec.company_id.id),
            ], limit=1)

            if not expense_account:
                expense_account = rec.env['account.account'].sudo().search([
                    ('account_type', '=', 'expense'),
                ], limit=1)

            if not expense_account:
                raise UserError(_('No expense account found.'))

            move_lines = []
            for line in rec.line_ids:
                if line.total_amount:
                    move_lines.append((0, 0, {
                        'name': '%s - %s to %s' % (
                            line.purpose or 'Conveyance',
                            line.from_location or '',
                            line.to_location or '',
                        ),
                        'account_id': expense_account.id,
                        'quantity': 1,
                        'price_unit': line.total_amount,
                    }))

            if not move_lines:
                raise UserError(_('No amount found in lines.'))

            bill_vals = {
                'move_type': 'in_invoice',
                'partner_id': partner.id,
                'invoice_date': fields.Date.today(),
                'journal_id': journal.id,
                'ref': rec.name,
                'invoice_line_ids': move_lines,
            }

            bill = rec.env['account.move'].sudo().create(bill_vals)
            rec.journal_entry_ids = [(4, bill.id)]
            rec.state = 'posted'
            rec.message_post(
                body=_('Vendor Bill created: %s') % bill.name,
            )

    def action_refuse(self):
        for rec in self:
            rec.state = 'refused'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.refuse_reason = False

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_view_vendor_bills(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Bills',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.journal_entry_ids.ids)],
        }

    def action_print_conveyance(self):
        return self.env.ref(
            'conveyance_expense.action_report_conveyance_sheet'
        ).report_action(self)