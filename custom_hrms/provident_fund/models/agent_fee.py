from odoo import models, fields, api, _, exceptions


class AgentFee(models.Model):
    _name = "agent.fee"
    _description = "Agent Fee"
    _rec_name = "agent_id"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    """
      - Agent fee can be Stock market or FDR Related person's payment
    """

    agent_id = fields.Many2one('res.partner', ondelete='cascade', string='Agent Name', tracking=True)
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    date = fields.Date(string='Date', tracking=True, default=fields.Date.context_today, required=True)
    agent_details = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approve'),
        ('cancel', 'Cancel'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=24, default='draft')
    acc_move_id = fields.Many2one('account.move', 'Journal Entries')
    total_commission_amount = fields.Float(default=0, string='Net Return on Shares', compute='_compute_net_return',
                                           store=True)
    avg_investment_in_share = fields.Float(default=0, string='Avg Investment in Shares')
    return_share_percentage = fields.Float(default=0, string='Return if Invested in FDR(%)')
    return_share_amount = fields.Float(default=0, string='Return FDR Total Amount')
    credit_by_managing_agent = fields.Float(default=0, string='Credit Made by Managing agent')
    managing_agent_fee_percentage = fields.Float(default=0, string='Managing Agent Fee(%)')
    managing_agent_fee_total_amount = fields.Float(default=0, string='Managing Agent Fee Total Amount')

    def _get_dbt_acc(self):
        if self.env.context.get('default_context_type') == 'general':
            return [('user_type_id.type', '!=', 'view'), ('fs_dept', '=', 'accounts')]
        else:
            return [('user_type_id.type', '!=', 'view'), ('fs_dept', '=', 'pf')]

    debit_aac_id = fields.Many2one('account.account', 'Debit Acc', domain=_get_dbt_acc)
    credit_acc_id = fields.Many2one('account.account', 'Credit Acc', domain=_get_dbt_acc)
    line_ids = fields.One2many('agent.fee.line', 'head_id')

    @api.depends('line_ids')
    def _compute_net_return(self):
        for rec in self:
            rec.total_commission_amount = sum(rec.line_ids.mapped('balance'))

    @api.onchange('return_share_percentage', 'avg_investment_in_share')
    def _onchange_return_share_percentage(self):
        for line in self:
            if line.return_share_percentage != 0:
                fixed_discount = 0.0
                credit_by_managing_agent = 0.0
                if line.avg_investment_in_share:
                    fixed_discount = line.return_share_percentage * (line.avg_investment_in_share / 100.0)
                    credit_by_managing_agent = line.total_commission_amount - fixed_discount
                line.update(
                    {"return_share_amount": fixed_discount, 'credit_by_managing_agent': credit_by_managing_agent})
            if line.return_share_percentage == 0:
                fixed_discount = 0.0
                line.update(
                    {"return_share_amount": fixed_discount, "credit_by_managing_agent": line.total_commission_amount})

    @api.onchange('managing_agent_fee_percentage', 'credit_by_managing_agent')
    def _onchange_managing_agent_fee_percentage(self):
        for line in self:
            if line.managing_agent_fee_percentage != 0:
                fixed_discount = 0.0
                if line.credit_by_managing_agent:
                    fixed_discount = line.managing_agent_fee_percentage * (line.credit_by_managing_agent / 100.0)
                line.update({"managing_agent_fee_total_amount": fixed_discount})
            if line.managing_agent_fee_percentage == 0:
                fixed_discount = 0.0
                line.update({"managing_agent_fee_total_amount": fixed_discount})

    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def action_done(self):
        lst = []
        credit_account_id = self.credit_acc_id.id or False
        debit_account_id = self.debit_aac_id.id or False

        amount = self.managing_agent_fee_total_amount
        ref = 'Agent Fees'

        lst.append((0, 0, {
            'account_id': debit_account_id,
            'name': ref,
            'debit': amount if amount > 0 else (-1 * amount),
        }))
        lst.append((0, 0, {
            'account_id': credit_account_id,
            'name': ref,
            'credit': amount if amount > 0 else (-1 * amount),
        }))
        journal_id = self.env['account.journal'].search([('code', '=', 'STJ')], limit=1)
        if not journal_id:
            raise exceptions.ValidationError(_('NO Journal Found!'))
        inv_data = self.env['account.move'].create({
            'invoice_origin': '',
            'move_type': 'entry',
            'journal_id': journal_id.id,
            'line_ids': lst
        })
        inv_data.post()
        inv_data.date = self.date
        self.acc_move_id = inv_data.id or False
        self.state = 'approve'

    def action_cancel(self):
        self.state = 'cancel'


class AgentFeeLine(models.Model):
    _name = "agent.fee.line"
    _description = "Agent Fee Line"

    head_id = fields.Many2one('agent.fee', ondelete='cascade')
    commission_type_id = fields.Many2one('agent.commission.type', ondelete='cascade')

    type_account_id = fields.Many2one('account.account', string='Type Account', ondelete='restrict', required=True,
                                      domain="[('account_type', '=', 'income')]", change_default=True)

    balance = fields.Float(string='Balance', default=0)
    percentage = fields.Float(string='Percentage', default=0)
    commission_amount = fields.Float(string='Commission Amount', default=0)
    remarks = fields.Char(string='Remarks')

    @api.constrains('percentage')
    def _check_percentage(self):
        for rec in self:
            if rec.percentage < 0:
                raise exceptions.ValidationError(_('Amount can not be negative!'))

    @api.onchange('commission_type_id')
    def _onchange_commission_type_id(self):
        if self.commission_type_id:
            self.type_account_id = self.commission_type_id.type_account_id.id
        else:
            self.type_account_id = None

    @api.onchange("percentage")
    def _onchange_percentage(self):
        for line in self:
            if line.percentage != 0:
                fixed_discount = 0.0
                if line.balance:
                    fixed_discount = line.percentage * (line.balance / 100.0)
                line.update({"commission_amount": fixed_discount})
            if line.percentage == 0:
                fixed_discount = 0.0
                line.update({"commission_amount": fixed_discount})

    @api.onchange('type_account_id')
    def _onchange_type_account_id(self):
        if self.type_account_id:
            if self.type_account_id.total_balance > 0:
                self.balance = (-1 * self.type_account_id.total_balance)
            else:
                self.balance = self.type_account_id.total_balance
        else:
            self.balance = 0
