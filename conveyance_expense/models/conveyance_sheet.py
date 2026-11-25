from odoo import models, fields, api, _
from odoo.exceptions import UserError

from .conveyance_sheet_line import _amount_to_words_bdt


DEBIT_ACCOUNT_CODE = '493'    # Travel National (Dr.)
CREDIT_ACCOUNT_CODE = '701'   # Cash in Hand (Cr.)
PAYMENT_REQUEST_THRESHOLD = 5000.0


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
            ('vice_president', 'Line Manager'),
            ('ceo', 'HoF'),
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
    payment_request_required = fields.Boolean(
        string='Payment Request Required',
        compute='_compute_payment_request_required',
    )
    due_item_ids = fields.One2many('payment.due.item', 'conveyance_sheet_id', string='Due Items')
    payment_request_id = fields.Many2one(
        'payment.request', string='Payment Request',
        compute='_compute_payment_request_id')
    refuse_reason = fields.Char(string='Refuse Reason', tracking=True)

    amount_in_words = fields.Char(
        string='Amount in Word',
        compute='_compute_amount_in_words',
    )

    @api.depends('total_amount')
    def _compute_amount_in_words(self):
        for rec in self:
            rec.amount_in_words = _amount_to_words_bdt(rec.total_amount)

    @api.depends('line_ids.total_amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('total_amount'))

    def _payment_threshold(self):
        icp = self.env['ir.config_parameter'].sudo()
        value = icp.get_param('payment_request_due_sync.expense_min_amount')
        try:
            return float(value) if value else PAYMENT_REQUEST_THRESHOLD
        except ValueError:
            return PAYMENT_REQUEST_THRESHOLD

    @api.depends('total_amount')
    def _compute_payment_request_required(self):
        threshold = self._payment_threshold()
        for rec in self:
            rec.payment_request_required = rec.total_amount > threshold

    @api.depends('due_item_ids.request_id')
    def _compute_payment_request_id(self):
        for rec in self:
            rec.payment_request_id = rec.sudo().due_item_ids.request_id[:1]

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

    def write(self, vals):
        res = super().write(vals)
        if 'line_ids' in vals:
            self.mapped('expense_id')._sync_total_from_conveyance()
        return res

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
                raise UserError(_('Only Line Manager can approve this stage.'))
            rec.state = 'ceo'

    def action_approve_ceo(self):
        for rec in self:
            if not self.env.user.has_group('conveyance_expense.group_conveyance_ceo'):
                raise UserError(_('Only HoF can approve this stage.'))
            rec.state = 'approved'
        self.action_post_journal_entries()

    def action_post_journal_entries(self):
        """On final (HoF) approval post the journal entry automatically:
            Dr. 493 - Travel National                         (always)
            Cr. 701 - Cash in Hand                            when the total is 5,000 or less
            Cr. Account Payable (employee) -> Payment Request when the total is above 5,000
        """
        for rec in self:
            if rec.state not in ('approved', 'ceo'):
                raise UserError(_('Only approved sheets can be posted.'))
            if not rec.line_ids:
                raise UserError(_('No line items found.'))
            amount = rec.total_amount
            if not amount:
                raise UserError(_('No amount found in lines.'))

            Account = rec.env['account.account'].sudo()
            debit_account = Account.search([
                ('code', '=', DEBIT_ACCOUNT_CODE),
                ('company_id', '=', rec.company_id.id),
            ], limit=1)
            credit_account = Account.search([
                ('code', '=', CREDIT_ACCOUNT_CODE),
                ('company_id', '=', rec.company_id.id),
            ], limit=1)
            if not debit_account:
                raise UserError(_('Account %s (Travel National) was not found. Please create it in the chart of accounts.') % DEBIT_ACCOUNT_CODE)
            if not credit_account:
                raise UserError(_('Account %s (Cash in Hand) was not found. Please create it in the chart of accounts.') % CREDIT_ACCOUNT_CODE)

            journal = rec.env['account.journal'].sudo().search([
                ('type', '=', 'general'),
                ('company_id', '=', rec.company_id.id),
            ], limit=1)
            if not journal:
                raise UserError(_('No Miscellaneous (general) journal found.'))

            employee = rec.employee_id.sudo()
            partner = (
                employee.work_contact_id
                or (employee._fields.get('address_home_id') and employee.address_home_id)
                or (employee.user_id and employee.user_id.partner_id)
            )
            use_payable = amount > rec._payment_threshold()
            credit_label = _('Cash in Hand')
            if use_payable:
                if not partner:
                    raise UserError(_('Employee %s has no contact (partner) - it is needed for Account Payable.')
                                    % employee.name)
                credit_account = partner.with_company(rec.company_id).property_account_payable_id
                if not credit_account:
                    raise UserError(_('No Account Payable found for %s.') % partner.display_name)
                credit_label = _('Account Payable')

            label = _('Conveyance - %s') % rec.name
            move = rec.env['account.move'].sudo().create({
                'move_type': 'entry',
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'ref': rec.name,
                'line_ids': [
                    (0, 0, {
                        'name': label,
                        'account_id': debit_account.id,
                        'partner_id': partner.id if partner else False,
                        'debit': amount,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': label,
                        'account_id': credit_account.id,
                        'partner_id': partner.id if partner else False,
                        'debit': 0.0,
                        'credit': amount,
                    }),
                ],
            })
            move.action_post()
            rec.journal_entry_ids = [(4, move.id)]
            rec.state = 'posted'
            rec.message_post(body=_('Journal Entry posted: %s (Dr. %s Travel National / Cr. %s)') % (
                move.name, DEBIT_ACCOUNT_CODE, credit_label))

    def action_create_payment_request(self):
        """Above the threshold (default BDT 5,000) the payment is made from the Payment Request
        module: create a Draft Payment Request from this sheet's 'Due for Payment' row."""
        self.ensure_one()
        if not self.payment_request_required:
            raise UserError(_('Payment request is only needed for amounts above %s BDT.')
                            % '{:,.0f}'.format(self._payment_threshold()))
        if self.state != 'posted':
            raise UserError(_('Only posted sheets can be sent to a Payment Request.'))
        Item = self.env['payment.due.item'].sudo()
        Item._sync()
        item = Item.search([('conveyance_sheet_id', '=', self.id)], limit=1)
        if not item:
            raise UserError(_('This sheet is not listed in "Due for Payment".'))
        if item.state != 'pending':
            raise UserError(_('This sheet is already in Payment Request %s.') % item.request_id.display_name)
        action = item.action_create_payment_request()
        self.message_post(body=_('Payment Request created. Payment will be made from the Payment Request module.'))
        return action

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