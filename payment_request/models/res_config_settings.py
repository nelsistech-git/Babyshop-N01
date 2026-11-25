# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pr_own_bank_id = fields.Many2one(
        'res.partner.bank', related='company_id.pr_own_bank_id', readonly=False,
        string='Own Bank Account (RTGS/BEFTN)')
    pr_own_bank_branch = fields.Char(
        related='company_id.pr_own_bank_branch', readonly=False, string='Own Bank Branch')
    pr_journal_id = fields.Many2one(
        'account.journal', related='company_id.pr_journal_id', readonly=False,
        string='Payment Request Journal')
    pr_bank_account_id = fields.Many2one(
        'account.account', related='company_id.pr_bank_account_id', readonly=False,
        string='Bank Account (Credited on Payment)')
    pr_tds_payable_account_id = fields.Many2one(
        'account.account', related='company_id.pr_tds_payable_account_id', readonly=False,
        string='TDS (WHT) Payable Account')
    pr_vds_payable_account_id = fields.Many2one(
        'account.account', related='company_id.pr_vds_payable_account_id', readonly=False,
        string='VDS (WHVAT) Payable Account')
    pr_signatory_name = fields.Char(
        related='company_id.pr_signatory_name', readonly=False, string='Signatory Name')
    pr_signatory_designation = fields.Char(
        related='company_id.pr_signatory_designation', readonly=False, string='Signatory Designation')
    pr_signatory_name_2 = fields.Char(
        related='company_id.pr_signatory_name_2', readonly=False, string='BEFTN 2nd Signatory Name')
    pr_signatory_designation_2 = fields.Char(
        related='company_id.pr_signatory_designation_2', readonly=False, string='BEFTN 2nd Signatory Designation')
    pr_vds_company_bin = fields.Char(
        related='company_id.pr_vds_company_bin', readonly=False, string='Company BIN (VAT Registration)')

    def action_pr_setup_chart_of_accounts(self):
        self.ensure_one()
        return self.company_id.action_pr_setup_chart_of_accounts()
