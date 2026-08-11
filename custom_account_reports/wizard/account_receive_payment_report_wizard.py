from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64
import xlsxwriter


class AccountReceivePaymentReportWizard(models.TransientModel):
    _name = "account.receive.payment.report.wizard"
    _description = "Receive/Payment Report Wizard"

    date_from = fields.Date(string="From Date", required=True)
    date_to = fields.Date(string="To Date", required=True)
    partner_id = fields.Many2one("res.partner", string="Partner")
    journal_id = fields.Many2one("account.journal", string="Journal")
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

    def _get_partner(self, move, lines=None):
        if move.partner_id:
            return move.partner_id
        if lines:
            for l in lines:
                if l.partner_id:
                    return l.partner_id
        for l in move.line_ids:
            if l.partner_id:
                return l.partner_id
        return self.env['res.partner']

    def _classify_move(self, move):
        """
        Classify if move is Receive or Payment.
        True = Receive, False = Payment
        """
        if move.move_type in ('out_invoice', 'out_receipt'):
            return True
        if move.move_type == 'out_refund':
            return False
        if move.move_type in ('in_invoice', 'in_receipt'):
            return False
        if move.move_type == 'in_refund':
            return True

        # Check payment_id first
        if move.payment_id:
            return move.payment_id.payment_type == 'inbound'

        # Check move-level payment_type directly (Vendor Reimbursement fix)
        move_payment_type = getattr(move, 'payment_type', None)
        if move_payment_type == 'inbound':
            return True
        if move_payment_type == 'outbound':
            return False

        journal = move.journal_id

        if getattr(journal, 'is_payment_journal', False):
            return False

        if journal.type == 'sale':
            return True
        if journal.type == 'purchase':
            return False

        # Bank/Cash fallback: check liquidity account direction
        liq_lines = move.line_ids.filtered(
            lambda l: (
                getattr(l.account_id, 'account_type', None) in ('asset_cash', 'liquidity')
                or (l.account_id.code or '').startswith('1001')
            )
        )
        if liq_lines:
            liq_dr = sum(l.debit for l in liq_lines)
            liq_cr = sum(l.credit for l in liq_lines)
            if liq_dr != liq_cr:
                return liq_dr > liq_cr

        # Final fallback
        total_dr = sum(l.debit for l in move.line_ids)
        total_cr = sum(l.credit for l in move.line_ids)
        return total_dr > total_cr

    def _get_move_lines_detail_payment(self, move):
        """
        Payment side: line-by-line DEBIT lines only.
        Skip: credit lines, payable, receivable, bank/cash accounts.
        Account column-এ Receivable/Payable আসবে না।
        """
        journal = move.journal_id
        partner = self._get_partner(move)
        result = []

        def should_skip(line):
            code = line.account_id.code or ''
            at = (
                getattr(line.account_id, 'account_type', None)
                or getattr(line.account_id, 'internal_type', None)
                or ''
            )

            # Skip zero amount lines
            if line.debit == 0 and line.credit == 0:
                return True

            # Skip all CREDIT lines
            if line.credit > 0:
                return True

            # Skip Payable accounts
            if at in ('liability_payable', 'payable'):
                return True
            if code.startswith('200') or code.startswith('201'):
                return True

            # Skip Receivable accounts
            if at in ('asset_receivable', 'receivable'):
                return True
            if code.startswith('1002'):
                return True

            # Skip Bank/Cash/Liquidity accounts
            if at in ('asset_cash', 'liquidity'):
                return True
            if code.startswith('1001'):
                return True

            return False

        def make_row(line, amount):
            return {
                "partner": (line.partner_id or partner).name if (line.partner_id or partner) else "No Partner",
                "name": move.name or move.ref or "",
                "date": move.date,
                "journal": journal.name,
                "account_code": line.account_id.code or "",
                "account": line.account_id.name or "",
                "amount": amount,
            }

        for line in move.line_ids:
            if should_skip(line):
                continue
            if line.debit > 0:
                result.append(make_row(line, line.debit))

        return result

    def _get_moves(self, side):
        domain = [
            ("state", "!=", "cancel"),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ]

        if self.state == "posted":
            domain.append(("state", "=", "posted"))
        elif self.state == "draft":
            domain.append(("state", "=", "draft"))

        if self.journal_id:
            domain.append(("journal_id", "=", self.journal_id.id))

        moves = self.env["account.move"].search(domain, order="date asc, id asc")
        result = []

        for move in moves:
            if not move.line_ids and move.move_type == 'entry':
                continue

            journal = move.journal_id
            partner = self._get_partner(move)

            if self.partner_id and partner != self.partner_id:
                continue

            is_receive = self._classify_move(move)

            is_payment_journal = getattr(journal, 'is_payment_journal', False)
            if is_payment_journal and side == "receive":
                continue

            if side == "receive" and not is_receive:
                continue
            if side == "payment" and is_receive:
                continue

            # PAYMENT SIDE - line-by-line with account details
            if side == "payment":
                line_details = self._get_move_lines_detail_payment(move)
                if line_details:
                    result.extend(line_details)
                else:
                    # Fallback: total amount excluding payable/receivable/cash
                    amount = sum(
                        l.debit for l in move.line_ids
                        if l.debit > 0
                        and (getattr(l.account_id, 'account_type', None) or '') not in (
                            'liability_payable', 'payable', 'asset_receivable', 'receivable', 'asset_cash', 'liquidity'
                        )
                        and not (l.account_id.code or '').startswith('200')
                        and not (l.account_id.code or '').startswith('1001')
                        and not (l.account_id.code or '').startswith('1002')
                    )
                    if amount <= 0:
                        continue
                    result.append({
                        "partner": partner.name if partner else "No Partner",
                        "name": move.name or move.ref or "",
                        "date": move.date,
                        "journal": journal.name,
                        "amount": amount,
                        "account": "",
                        "account_code": "",
                    })
                continue

            # RECEIVE SIDE - total debit amount
            amount = sum(l.debit for l in move.line_ids if l.debit > 0)
            if amount <= 0:
                continue

            result.append({
                "partner": partner.name if partner else "No Partner",
                "name": move.name or move.ref or "",
                "date": move.date,
                "journal": journal.name,
                "amount": amount,
                "account": "",
                "account_code": "",
            })

        return result

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
            "no_data": False,
        }

        if self.payment_type in ("all", "receive"):
            report_data["receive"] = self._get_moves("receive")
            report_data["receive_total"] = sum(r["amount"] for r in report_data["receive"])

        if self.payment_type in ("all", "payment"):
            report_data["payment"] = self._get_moves("payment")
            report_data["payment_total"] = sum(p["amount"] for p in report_data["payment"])

        if not report_data["receive"] and not report_data["payment"]:
            report_data["no_data"] = True

        return report_data

    def action_generate_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "custom_account_reports.action_account_receive_payment_report_pdf"
        ).report_action(self)

    def action_generate_excel(self):
        self.ensure_one()
        report_data = self.get_report_data()

        if report_data.get("no_data"):
            raise UserError(_("No data found for the selected criteria."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Receive-Payment Report")

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

        today_str = fields.Date.context_today(self).strftime("%d/%m/%Y")
        from_str  = report_data["date_from"].strftime("%d/%m/%Y") if report_data["date_from"] else ""
        to_str    = report_data["date_to"].strftime("%d/%m/%Y") if report_data["date_to"] else ""
        row = 0

        def write_receive_section(title, data):
            nonlocal row
            last_col = 4
            sheet.merge_range(row, 0, row, last_col, title, title_fmt)
            row += 1
            sheet.merge_range(
                row, 0, row, last_col,
                (f"Date: {today_str} | From: {from_str} | To: {to_str} | "
                 f"Partner: {report_data['partner_name']} | "
                 f"Journal: {report_data['journal_name']} | "
                 f"Status: {report_data['state']}"),
                filter_fmt,
            )
            row += 1
            for col, h in enumerate(["Partner", "Reference", "Date", "Journal", "Amount (Dr)"]):
                sheet.write(row, col, h, header_fmt)
            row += 1

            total = 0.0
            for i, item in enumerate(data):
                f = odd_fmt if i % 2 == 0 else even_fmt
                sheet.write(row, 0, item["partner"], f)
                sheet.write(row, 1, item["name"], f)
                sheet.write(row, 2, item["date"], date_fmt)
                sheet.write(row, 3, item["journal"], f)
                sheet.write(row, 4, item["amount"], number_fmt)
                total += item["amount"]
                row += 1

            sheet.write(row, 0, f"{title} Total", total_lbl)
            for c in range(1, last_col):
                sheet.write_blank(row, c, None, blank_fmt)
            sheet.write(row, last_col, total, total_num)
            row += 2
            return total

        def write_payment_section(title, data):
            nonlocal row
            last_col = 5
            sheet.merge_range(row, 0, row, last_col, title, title_fmt)
            row += 1
            sheet.merge_range(
                row, 0, row, last_col,
                (f"Date: {today_str} | From: {from_str} | To: {to_str} | "
                 f"Partner: {report_data['partner_name']} | "
                 f"Journal: {report_data['journal_name']} | "
                 f"Status: {report_data['state']}"),
                filter_fmt,
            )
            row += 1
            for col, h in enumerate(["Partner", "Reference", "Date", "Journal", "Account", "Amount (Cr)"]):
                sheet.write(row, col, h, header_fmt)
            row += 1

            total = 0.0
            for i, item in enumerate(data):
                f = odd_fmt if i % 2 == 0 else even_fmt
                sheet.write(row, 0, item["partner"], f)
                sheet.write(row, 1, item["name"], f)
                sheet.write(row, 2, item["date"], date_fmt)
                sheet.write(row, 3, item["journal"], f)
                account_display = ""
                if item.get('account_code') or item.get('account'):
                    account_display = f"{item.get('account_code', '')} {item.get('account', '')}".strip()
                sheet.write(row, 4, account_display, f)
                sheet.write(row, 5, item["amount"], number_fmt)
                total += item["amount"]
                row += 1

            sheet.write(row, 0, f"{title} Total", total_lbl)
            for c in range(1, last_col):
                sheet.write_blank(row, c, None, blank_fmt)
            sheet.write(row, last_col, total, total_num)
            row += 2
            return total

        # Receive section — 5 columns
        for idx, w in enumerate([30, 25, 15, 20, 15]):
            sheet.set_column(idx, idx, w)

        recv_total = pay_total = 0.0

        if report_data["receive"]:
            recv_total = write_receive_section("Receive Report", report_data["receive"])

        # Payment section — 6 columns
        for idx, w in enumerate([25, 20, 12, 18, 18, 15]):
            sheet.set_column(idx, idx, w)

        if report_data["payment"]:
            pay_total = write_payment_section("Payment Report", report_data["payment"])

        row += 1
        sheet.write(row, 0, "Total Balance", total_lbl)
        for c in range(1, 3):
            sheet.write_blank(row, c, None, blank_fmt)
        sheet.write(row, 3, f"Receive: {recv_total:,.2f}", total_num)
        sheet.write(row, 4, f"Payment: {pay_total:,.2f}", total_num)
        sheet.write(row, 5, f"Balance: {recv_total - pay_total:,.2f}", total_num)

        workbook.close()
        output.seek(0)
        excel_data = base64.b64encode(output.read())

        attachment = self.env["ir.attachment"].create({
            "name": "ReceivePayment_Report.xlsx",
            "type": "binary",
            "datas": excel_data,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "new",
        }