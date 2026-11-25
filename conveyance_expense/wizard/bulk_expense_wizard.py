from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrExpenseBulkWizard(models.TransientModel):
    _name = 'hr.expense.bulk.wizard'
    _description = 'Bulk Expense Creation'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Category',
        domain=[('can_be_expensed', '=', True)],
        required=True,
    )
    date = fields.Date(string='Expense Date', default=fields.Date.context_today, required=True)
    payment_mode = fields.Selection(
        selection=[
            ('own_account', 'Employee (to reimburse)'),
            ('company_account', 'Company'),
        ],
        string='Paid By',
        default='own_account',
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    name = fields.Char(string='Description', default='Conveyance', required=True)
    line_ids = fields.One2many(
        comodel_name='hr.expense.bulk.wizard.line',
        inverse_name='wizard_id',
        string='Conveyance Lines',
    )

    def action_create_expenses(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Please add at least one line.'))

        # sudo: lets a normal user create expenses for other employees
        # without being given the wider "Team Approver" access rights.
        Expense = self.env['hr.expense'].sudo()
        author = self.env.user.partner_id

        # Group wizard lines by employee -> one expense (+ one conveyance sheet) per employee
        grouped = {}
        for line in self.line_ids:
            grouped.setdefault(line.employee_id, self.env['hr.expense.bulk.wizard.line'])
            grouped[line.employee_id] |= line

        expenses = Expense
        for employee, lines in grouped.items():
            expense = Expense.create({
                'name': self.name,
                'employee_id': employee.id,
                'product_id': self.product_id.id,
                'date': min(lines.mapped('date')),
                'payment_mode': self.payment_mode,
                'company_id': self.company_id.id,
                'total_amount': sum(lines.mapped('total_amount')),
                'conveyance_line_ids': [(0, 0, l._prepare_sheet_line_vals()) for l in lines],
            })
            sheet = expense.conveyance_sheet_id
            if sheet:
                sheet.write({
                    'date_from': min(lines.mapped('date')),
                    'date_to': max(lines.mapped('date')),
                })
            expense.message_post(
                body=_('Created by %s via Bulk Expense.') % self.env.user.name,
                author_id=author.id,
            )
            expenses |= expense

        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Expenses'),
            'res_model': 'hr.expense',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', expenses.ids)],
            'target': 'current',
        }


class HrExpenseBulkWizardLine(models.TransientModel):
    _name = 'hr.expense.bulk.wizard.line'
    _description = 'Bulk Expense Line'

    wizard_id = fields.Many2one('hr.expense.bulk.wizard', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    from_location = fields.Char(string='From', required=True)
    to_location = fields.Char(string='To', required=True)
    purpose = fields.Char(string='Purpose')
    transport = fields.Selection([
        ('rickshaw', 'Rickshaw'),
        ('cng', 'CNG'),
        ('uber', 'Uber'),
        ('bus', 'Bus'),
        ('pathao', 'Pathao'),
        ('metro_rail', 'Metro Rail'),
        ('car', 'Car'),
        ('walked', 'Walked'),
        ('others', 'Others'),
    ], string='Transport', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer')
    conveyance_amount = fields.Float(string='Conveyance Amount', digits=(12, 2))
    food_bill = fields.Float(string='Food Bill', digits=(12, 2))
    others_cost = fields.Char(string='Others Cost')
    amount = fields.Float(string='Amount', digits=(12, 2))
    total_amount = fields.Float(
        string='Total Amount', compute='_compute_total_amount', digits=(12, 2),
    )
    remarks = fields.Char(string='Remarks')

    @api.depends('conveyance_amount', 'food_bill', 'amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.conveyance_amount + rec.food_bill + rec.amount

    def _prepare_sheet_line_vals(self):
        self.ensure_one()
        return {
            'date': self.date,
            'from_location': self.from_location,
            'to_location': self.to_location,
            'purpose': self.purpose,
            'transport': self.transport,
            'customer_id': self.customer_id.id,
            'conveyance_amount': self.conveyance_amount,
            'food_bill': self.food_bill,
            'others_cost': self.others_cost,
            'amount': self.amount,
            'remarks': self.remarks,
        }