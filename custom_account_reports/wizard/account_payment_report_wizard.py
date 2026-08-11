from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64
import xlsxwriter


class AccountPaymentReceiveReportWizard(models.TransientModel):
    _name = "account.payment.receive.report.wizard"
    _description = "Payment/Receive Report Wizard"

    date_from = fields.Date(string="From Date", required=True)
    date_to = fields.Date(string="To Date", required=True)
    partner_id = fields.Many2one("res.partner", string="Partner")
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
    )
    state = fields.Selection(
        [
            ("all", "All"),
            ("posted", "Posted"),
            ("draft", "Draft"),
        ],
        string="Status",
        default="all",
    )
    payment_type = fields.Selection(
        [
            ("all", "All"),
            ("receive", "Receive (Dr)"),
            ("payment", "Payment (Cr)"),
        ],
        string="Type",
        default="all",
    )

    # ─────────────────────────────────────────────
    #  Account type helpers
    # ─────────────────────────────────────────────

    @staticmethod
    def _acct_type(account):
        return (
            getattr(account, 'account_type', None)
            or getattr(account, 'internal_type', None)
            or ''
        )

    def _is_liquidity(self, account):
        return self._acct_type(account) in ('asset_cash', 'liquidity')

    def _is_receivable(self, account):
        return self._acct_type(account) in ('asset_receivable', 'receivable')

    def _is_payable(self, account):
        return self._acct_type(account) in ('liability_payable', 'payable')

    def _is_income(self, account):
        return self._acct_type(account) in ('income', 'income_other')

    def _is_expense(self, account):
        return self._acct_type(account) in ('expense', 'expense_depreciation', 'expense_direct_cost')

    # ─────────────────────────────────────────────
    #  Direction + Amount determination
    # ─────────────────────────────────────────────

    def _get_direction_and_amount(self, move):
        """
        Returns (net_dr, net_cr) for a journal entry.
        net_dr > 0  → Receive (money in)
        net_cr > 0  → Payment (money out)
        Uses only standard account.move / account.move.line fields.
        """

        # Method 1: from account.payment
        payment = getattr(move, 'payment_id', None)
        if payment:
            ptype = getattr(payment, 'payment_type', '')
            amt = abs(getattr(payment, 'amount', 0.0) or 0.0)
            liq_lines = move.line_ids.filtered(
                lambda l: self._is_liquidity(l.account_id)
                or (move.journal_id.default_account_id
                    and l.account_id.id == move.journal_id.default_account_id.id)
            )
            if liq_lines:
                dr = sum(l.debit for l in liq_lines)
                cr = sum(l.credit for l in liq_lines)
                net = dr - cr
                if net > 0:
                    return net, 0.0
                if net < 0:
                    return 0.0, abs(net)
            if ptype == 'inbound':
                return amt, 0.0
            if ptype == 'outbound':
                return 0.0, amt

        # Method 2: Journal default_account_id
        default_acc = move.journal_id.default_account_id
        if default_acc:
            lines = move.line_ids.filtered(lambda l: l.account_id.id == default_acc.id)
            if lines:
                dr = sum(l.debit for l in lines)
                cr = sum(l.credit for l in lines)
                net = dr - cr
                if net != 0:
                    return (net, 0.0) if net > 0 else (0.0, abs(net))

        # Method 3: Any bank/cash account
        liq_lines = move.line_ids.filtered(lambda l: self._is_liquidity(l.account_id))
        if liq_lines:
            dr = sum(l.debit for l in liq_lines)
            cr = sum(l.credit for l in liq_lines)
            net = dr - cr
            if net != 0:
                return (net, 0.0) if net > 0 else (0.0, abs(net))

        # Method 4: move_type
        mtype = getattr(move, 'move_type', 'entry')
        amt = abs(getattr(move, 'amount_total', 0.0) or 0.0)
        if mtype == 'out_invoice':
            return amt, 0.0
        if mtype == 'in_invoice':
            return 0.0, amt
        if mtype == 'out_refund':
            return 0.0, amt
        if mtype == 'in_refund':
            return amt, 0.0

        # Method 5: AR/AP lines
        ar_dr = sum(l.debit for l in move.line_ids if self._is_receivable(l.account_id))
        ap_cr = sum(l.credit for l in move.line_ids if self._is_payable(l.account_id))
        if ar_dr > 0 and ap_cr <= 0:
            return ar_dr, 0.0
        if ap_cr > 0 and ar_dr <= 0:
            return 0.0, ap_cr
        if ar_dr > 0 and ap_cr > 0:
            return (ar_dr, 0.0) if ar_dr >= ap_cr else (0.0, ap_cr)

        # Method 6: Income / Expense
        inc_cr = sum(l.credit for l in move.line_ids if self._is_income(l.account_id))
        exp_dr = sum(l.debit for l in move.line_ids if self._is_expense(l.account_id))
        if inc_cr > 0 and exp_dr <= 0:
            return inc_cr, 0.0
        if exp_dr > 0 and inc_cr <= 0:
            return 0.0, exp_dr
        if inc_cr > 0 and exp_dr > 0:
            return (inc_cr, 0.0) if inc_cr >= exp_dr else (0.0, exp_dr)

        # Method 7: Fallback
        total_dr = sum(l.debit for l in move.line_ids)
        total_cr = sum(l.credit for l in move.line_ids)
        if amt > 0:
            return (amt, 0.0) if total_dr >= total_cr else (0.0, amt)

        return 0.0, 0.0

    # ─────────────────────────────────────────────
    #  Partner helper
    # ─────────────────────────────────────────────

    def _get_partner(self, move):
        if move.partner_id:
            return move.partner_id
        for line in move.line_ids:
            if (self._is_receivable(line.account_id) or self._is_payable(line.account_id)) and line.partner_id:
                return line.partner_id
        for line in move.line_ids:
            if line.partner_id:
                return line.partner_id
        return self.env['res.partner']

    # ─────────────────────────────────────────────
    #  Main data fetcher
    # ─────────────────────────────────────────────

    def _get_moves(self, debit_credit):
        domain = [("state", "!=", "cancel")]

        if self.date_from:
            domain.append(("date", ">=", self.date_from))
        if self.date_to:
            domain.append(("date", "<=", self.date_to))
        if self.journal_id:
            domain.append(("journal_id", "=", self.journal_id.id))
        if self.state == "posted":
            domain.append(("state", "=", "posted"))
        elif self.state == "draft":
            domain.append(("state", "=", "draft"))

        moves = self.env["account.move"].search(domain, order="date asc, id asc")

        result = []
        for move in moves:
            if not move.line_ids:
                continue

            net_dr, net_cr = self._get_direction_and_amount(move)

            if debit_credit == "debit":
                if net_dr <= 0:
                    continue
                amount = net_dr
            else:
                if net_cr <= 0:
                    continue
                amount = net_cr

            partner = self._get_partner(move)

            if self.partner_id and partner != self.partner_id:
                continue

            result.append({
                "partner": partner.name if partner else "No Partner",
                "name": move.name or move.ref or "",
                "date": move.date,
                "journal": move.journal_id.name,
                "amount": amount,
            })

        return result

    # ─────────────────────────────────────────────
    #  Report data
    # ─────────────────────────────────────────────

    def get_report_data(self):
        report_data = {
            "today": fields.Date.context_today(self),
            "date_from": self.date_from,
            "date_to": self.date_to,
            "partner_name": self.partner_id.name if self.partner_id else "All Partners",
            "journal_name": self.journal_id.name if self.journal_id else "All Journals",
            "state": dict(self._fields["state"].selection).get(self.state, "All"),
            "payment_type": self.payment_type,
            "receive": [],
            "payment": [],
            "receive_total": 0.0,
            "payment_total": 0.0,
        }

        if self.payment_type in ("all", "receive"):
            report_data["receive"] = self._get_moves("debit")
            report_data["receive_total"] = sum(r["amount"] for r in report_data["receive"])

        if self.payment_type in ("all", "payment"):
            report_data["payment"] = self._get_moves("credit")
            report_data["payment_total"] = sum(p["amount"] for p in report_data["payment"])

        if not report_data["receive"] and not report_data["payment"]:
            report_data["no_data"] = True

        return report_data

    # ─────────────────────────────────────────────
    #  Actions
    # ─────────────────────────────────────────────

    def action_generate_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "custom_account_reports.action_account_payment_receive_report_pdf"
        ).report_action(self)

    def action_generate_excel(self):
        self.ensure_one()
        report_data = self.get_report_data()

        if report_data.get("no_data"):
            raise UserError(_("No data found for the selected criteria."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Payment-Receive Report")

        def fmt(**kw):
            return workbook.add_format(kw)

        title_fmt  = fmt(bold=True, font_size=14, align="center", valign="vcenter", font_color="#714B67")
        filter_fmt = fmt(italic=True, bold=True, align="center", valign="vcenter", font_color="#000000")
        header_fmt = fmt(bold=True, font_color="#FFFFFF", bg_color="#714B67", align="center", border=1)
        number_fmt = fmt(num_format="#,##0.00", border=1, align="right")
        date_fmt   = fmt(num_format="dd/mm/yyyy", border=1, align="center")
        total_lbl  = fmt(bold=True, bg_color="#017E84", font_color="#FFFFFF", border=1)
        total_num  = fmt(bold=True, bg_color="#017E84", font_color="#FFFFFF", num_format="#,##0.00", border=1, align="right")
        blank_fmt  = fmt(bg_color="#9FD8DA", border=1)
        odd_fmt    = fmt(bg_color="#F9F9F9", border=1)
        even_fmt   = fmt(bg_color="#FFFFFF", border=1)

        for idx, w in enumerate([30, 25, 15, 20, 15]):
            sheet.set_column(idx, idx, w)

        today_str = fields.Date.context_today(self).strftime("%d/%m/%Y")
        from_str  = report_data["date_from"].strftime("%d/%m/%Y") if report_data["date_from"] else ""
        to_str    = report_data["date_to"].strftime("%d/%m/%Y")   if report_data["date_to"]   else ""
        row = 0

        def write_section(title, data, col_header, type_label):
            nonlocal row
            sheet.merge_range(row, 0, row, 4, title, title_fmt)
            row += 1
            sheet.merge_range(
                row, 0, row, 4,
                (f"Date: {today_str} | From: {from_str} | To: {to_str} | "
                 f"Partner: {report_data['partner_name']} | "
                 f"Journal: {report_data['journal_name']} | "
                 f"Status: {report_data['state']} | Type: {type_label}"),
                filter_fmt,
            )
            row += 1
            for col, h in enumerate([col_header, "Reference", "Date", "Journal", "Amount"]):
                sheet.write(row, col, h, header_fmt)
            row += 1

            total = 0.0
            for i, item in enumerate(data):
                f = odd_fmt if i % 2 == 0 else even_fmt
                sheet.write(row, 0, item["partner"], f)
                sheet.write(row, 1, item["name"],    f)
                sheet.write(row, 2, item["date"],    date_fmt)
                sheet.write(row, 3, item["journal"], f)
                sheet.write(row, 4, item["amount"],  number_fmt)
                total += item["amount"]
                row += 1

            sheet.write(row, 0, f"{title} Total", total_lbl)
            for c in range(1, 4):
                sheet.write_blank(row, c, None, blank_fmt)
            sheet.write(row, 4, total, total_num)
            row += 2
            return total

        recv_total = pay_total = 0.0
        if report_data["receive"]:
            recv_total = write_section("Receive Report", report_data["receive"], "Partner", "Receive (Dr)")
        if report_data["payment"]:
            pay_total = write_section("Payment Report", report_data["payment"], "Partner", "Payment (Cr)")

        row += 1
        sheet.write(row, 0, "Total Balance", total_lbl)
        for c in range(1, 4):
            sheet.write_blank(row, c, None, blank_fmt)
        sheet.write(row, 4, recv_total - pay_total, total_num)

        workbook.close()
        output.seek(0)
        excel_data = base64.b64encode(output.read())

        attachment = self.env["ir.attachment"].create({
            "name": "PaymentReceive_Report.xlsx",
            "type": "binary",
            "datas": excel_data,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "new",
        }
