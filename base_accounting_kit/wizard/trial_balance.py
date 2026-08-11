from odoo import fields, models, api ,_


class AccountBalanceReport(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = 'account.balance.report'
    _description = 'Trial Balance Report'

    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_balance_report_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_balance_report_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    name = fields.Char(string="Trial Balance", default="Trial Balance", required=True, translate=True)
    journal_ids = fields.Many2many('account.journal',
                                   'account_balance_report_journal_rel',
                                   'account_id', 'journal_id',
                                   string='List of Journals', required=True,
                                   default=[])


    def _print_report(self, data):
        data = self.pre_print_report(data)
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref(
            'base_accounting_kit.action_report_trial_balance').report_action(
            records, data=data)
