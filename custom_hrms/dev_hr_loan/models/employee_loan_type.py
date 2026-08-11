from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EmployeeLoanType(models.Model):
    _name = 'employee.loan.type'
    _description = 'Employee Loan Type'

    def _compute_loan_done(self):
        for record in self:
            emp_loan = self.env['employee.loan'].search([('state', '=', 'done'), ('loan_type_id', '=', record.id)])
            record.count_loan_done = len(emp_loan)

    def _compute_loan_paid(self):
        for record in self:
            emp_loan = self.env['employee.loan'].search([('state', '=', 'paid'), ('loan_type_id', '=', record.id)])
            record.count_loan_paid = len(emp_loan)

    def _compute_loan_draft(self):
        for record in self:
            emp_loan = self.env['employee.loan'].search([('state', '=', 'draft'), ('loan_type_id', '=', record.id)])
            record.count_loan_draft = len(emp_loan)

    name = fields.Char('Name', required=True)

    is_apply_interest = fields.Boolean('Apply Interest')
    interest_rate = fields.Float('Interest Rate', default=10)
    interest_type = fields.Selection([('liner', 'Liner'), ('reduce', 'Reduce')], string='Interest Type',
                                     default='liner')
    loan_account = fields.Many2one('account.account', string='Loan Emp/Debit Account', required=True)
    loan_payment_account = fields.Many2one('account.account', string='Default Payment Disb./Credit Account')
    loan_payment_account_rcv = fields.Many2one('account.account', string='Default Payment Rcv./Debit Account')
    interest_account = fields.Many2one('account.account', string='Interest Debit Account')
    debit_process_fee_account = fields.Many2one('account.account', string='Loan Process Fee Credit Account')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    color = fields.Integer(string='Color')
    count_loan_draft = fields.Integer(compute='_compute_loan_draft')
    count_loan_done = fields.Integer(compute='_compute_loan_done')
    count_loan_paid = fields.Integer(compute='_compute_loan_paid')
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal')], default='0')

    type = fields.Selection([('pf_loan', 'PF Loan'), ('general', 'General')], string='Type', default='general')
    pf_policy_id = fields.Many2one('pf.configuration', string='PF Policy')

    loan_limit = fields.Float('Max Loan Amount', default=50000)
    minimum_loan_amount = fields.Float(string="Min Loan Amount", default=0.0)
    loan_term = fields.Integer(string="Max No. of Installment", default=1)
    minimum_installment_amount = fields.Float(string="Min Installment Amount", default=0.0)
    is_apply_top_up = fields.Boolean('Is Top-Up Apply?', default=False)
    top_up_paid_chk_amt = fields.Float(string="Top-Up Validation Paid (%)", default=50.0,
                                       help="Second loan applicable if Previous paid amount (%)")
    top_up_paid_chk_month = fields.Integer(string="Top-Up Validation Paid (Months)", default=0,
                                           help="Second loan applicable if Previous paid months (%)")
    is_default = fields.Boolean('Is Default?', default=False)

    @api.onchange('pf_policy_id')
    def _onchange_pf_policy_id(self):
        if self.pf_policy_id:
            self.minimum_loan_amount = self.pf_policy_id.minimum_loan_amount
            self.loan_term = self.pf_policy_id.max_no_installment
            self.minimum_installment_amount = self.pf_policy_id.minimum_installment_amount
            self.is_apply_top_up = True
        else:
            self.minimum_loan_amount = 0
            self.loan_term = 0
            self.minimum_installment_amount = 0
            self.is_apply_top_up = False

    def _get_action(self, action_xmlid):
        # TDE TODO check to have one view + custo in methods
        action = self.env.ref(action_xmlid).read()[0]
        if self:
            action['display_name'] = self.display_name
        return action

    def get_action_loan_tree_done(self):
        return self._get_action('dev_hr_loan.action_loan_tree_done')

    def get_action_loan_tree_draft(self):
        return self._get_action('dev_hr_loan.action_loan_tree_draft')

    def action_get_hr_loan_type(self):
        return self._get_action('dev_hr_loan.get_hr_loan_type')

    def get_action_loan_paid(self):
        return self._get_action('dev_hr_loan.action_loan_paid')

    def get_action_hr_approval(self):
        return self._get_action('dev_hr_loan.action_hr_approval')

    def get_loan_create(self):
        return self._get_action('dev_hr_loan.action_loan_create')

    def get_all_loan(self):
        return self._get_action('dev_hr_loan.action_view_all_loan')

    def get_setting(self):
        return self._get_action('dev_hr_loan.action_setting')

    @api.constrains('is_apply_interest', 'interest_rate', 'interest_type')
    def _check_interest_rate(self):
        for loan in self:
            if loan.is_apply_interest:
                if loan.interest_rate <= 0:
                    raise ValidationError("Interest Rate must be greater 0.00")
                if not loan.interest_type:
                    raise ValidationError("Please Select Interest Type")
