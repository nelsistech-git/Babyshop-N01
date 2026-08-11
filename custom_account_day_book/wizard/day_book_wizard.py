from odoo import models


class DayBookWizard(models.TransientModel):
    _name = 'day.book.print.wizards'
    _description = 'Merge Req Wizard'

    def action_print_pdf(self):
        active_ids = self.env.context.get('active_ids')
        customer_invoice_list = []
        for data in active_ids:
            move_id = self.env['account.move'].browse(data)
            vals = {
                'name': move_id.name,
                'date': move_id.date,
                'account_name': move_id.account_name,
                'amount_total_signed': move_id.amount_total_signed,
                'partner_id': move_id.partner_id.name,
                'ref': move_id.ref,
                'journal_id': move_id.journal_id.name,
                'create_uid': move_id.create_uid.name,
                'write_uid': move_id.write_uid.name,
                'state': move_id.state,
            }
            customer_invoice_list.append(vals)
        data = {
            'model': "day.book.print.wizards",
            'form': self.read()[0],
            'csr': customer_invoice_list
        }

        # get data from sql
        return self.env.ref('custom_account_day_book.day_book_report_ids').with_context(
            landscape=True).report_action(self, data=data)
