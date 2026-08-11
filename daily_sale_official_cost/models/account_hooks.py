# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        self._daily_report_touch()
        return res

    def _daily_report_touch(self):
        """Requirement 4 (Real-time Synchronization): as soon as an
        accounting entry is validated, refresh the Daily Sale & Official
        Cost report for the matching date(s) so the figures shown are
        always current. Locked reports are left untouched on purpose.
        """
        Report = self.env['daily.sale.official.cost.report']
        dates = {(m.invoice_date or m.date, m.company_id.id) for m in self
                  if (m.invoice_date or m.date)}
        for report_date, company_id in dates:
            report = Report.search([
                ('report_date', '=', report_date),
                ('company_id', '=', company_id),
                ('state', '=', 'draft'),
            ], limit=1)
            if report:
                report._refresh_lines()


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        res = super().action_post()
        self._daily_report_touch()
        return res

    def _daily_report_touch(self):
        Report = self.env['daily.sale.official.cost.report']
        dates = {(p.date, p.company_id.id) for p in self if p.date}
        for report_date, company_id in dates:
            report = Report.search([
                ('report_date', '=', report_date),
                ('company_id', '=', company_id),
                ('state', '=', 'draft'),
            ], limit=1)
            if report:
                report._refresh_lines()
