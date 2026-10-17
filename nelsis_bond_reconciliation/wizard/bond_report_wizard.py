# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
import base64
import csv
import io
from datetime import datetime, time

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError

STATUTORY_NOTICE = (
    "INTERNAL MANAGEMENT REPORT. This is not an official statutory customs form. Its format, "
    "calculations and legal acceptance have NOT been verified for submission to NBR / "
    "Bangladesh Customs. Have it reviewed by a qualified Bangladesh customs professional "
    "before any official use.")

REPORT_TYPES = [
    ('lc_wise', '1. LC-wise Stock Report'),
    ('boe_wise', '2. Bill of Entry-wise Stock Report'),
    ('classification', '3. Bonded / Non-Bonded Stock Report'),
    ('product_hs', '4. Product / HS Code-wise Stock Report'),
    ('location_ledger', '5. Warehouse / Location Ledger'),
    ('rir', '6. Receipt, Issue and Return Report'),
    ('entitlement', '7. Entitlement Utilization Report'),
    ('discrepancy', '8. Physical Stock Discrepancy Report'),
    ('missing_docs', '9. Missing Document Report'),
    ('exceptions', '10. Expired / Invalid Authorization Exceptions'),
    ('audit_index', '11. Audit Document Index'),
    ('register_export', '12. Bond Register Export'),
]
LEDGER_LIMIT = 20000


class BondReportWizard(models.TransientModel):
    _name = 'bond.warehouse.report.wizard'
    _description = 'Bond Report Wizard'

    report_type = fields.Selection(REPORT_TYPES, required=True, default='lc_wise')
    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company)
    date_from = fields.Date(string='From',
                            default=lambda s: fields.Date.context_today(s).replace(day=1))
    date_to = fields.Date(string='To', default=fields.Date.context_today)
    bond_classification = fields.Selection(
        [('all', 'All'), ('bonded', 'Bonded'), ('non_bonded', 'Non-Bonded')],
        string='Bond Classification', default='bonded', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', domain="[('company_id', '=', company_id)]")
    location_ids = fields.Many2many('stock.location', string='Locations',
                                    domain="[('usage', '=', 'internal')]")
    product_ids = fields.Many2many('product.product', string='Products')
    lc_ref = fields.Char(string='LC Reference')
    boe_ref = fields.Char(string='Bill of Entry')
    reconciliation_id = fields.Many2one('bond.warehouse.reconciliation', string='Reconciliation')
    require_lc = fields.Boolean(string='Require LC Reference', default=True)
    require_boe = fields.Boolean(string='Require Bill of Entry', default=True)
    require_license = fields.Boolean(string='Require License Reference', default=True)
    require_attachment = fields.Boolean(string='Require Attachment', default=True)
    xlsx_available = fields.Boolean(compute='_compute_xlsx_available')
    statutory_notice = fields.Char(compute='_compute_statutory_notice')

    def _compute_xlsx_available(self):
        try:
            import xlsxwriter  # noqa: F401
            ok = True
        except ImportError:
            ok = False
        for rec in self:
            rec.xlsx_available = ok

    def _compute_statutory_notice(self):
        for rec in self:
            rec.statutory_notice = STATUTORY_NOTICE

    # ------------------------------------------------------------------
    # Domains and helpers
    # ------------------------------------------------------------------
    def _bound(self, day, end=False):
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        moment = datetime.combine(day, time.max if end else time.min)
        return tz.localize(moment).astimezone(pytz.utc).replace(tzinfo=None)

    def _base_domain(self):
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id)]
        if self.bond_classification != 'all':
            domain.append(('bond_classification', '=', self.bond_classification))
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
        if self.location_ids:
            domain.append(('location_id', 'child_of', self.location_ids.ids))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.lc_ref:
            domain.append(('lc_ref', '=', self.lc_ref.strip()))
        if self.boe_ref:
            domain.append(('boe_ref', '=', self.boe_ref.strip()))
        return domain

    def _period_domain(self):
        domain = []
        if self.date_from:
            domain.append(('date', '>=', self._bound(self.date_from)))
        if self.date_to:
            domain.append(('date', '<=', self._bound(self.date_to, end=True)))
        return domain

    def _asof_domain(self):
        return [('date', '<=', self._bound(self.date_to, end=True))] if self.date_to else []

    @staticmethod
    def _name_of(value):
        if isinstance(value, (tuple, list)) and len(value) == 2:
            return value[1]
        return value or ''

    def _filters_text(self):
        parts = [_("Company: %s", self.company_id.name)]
        if self.date_from or self.date_to:
            parts.append(_("Period: %(a)s to %(b)s", a=self.date_from or '...', b=self.date_to or '...'))
        parts.append(_("Classification: %s", dict(self._fields['bond_classification'].selection)[self.bond_classification]))
        if self.warehouse_id:
            parts.append(_("Warehouse: %s", self.warehouse_id.name))
        if self.location_ids:
            parts.append(_("Locations: %s", ', '.join(self.location_ids.mapped('complete_name'))))
        if self.product_ids:
            parts.append(_("Products: %s", ', '.join(self.product_ids.mapped('display_name'))))
        if self.lc_ref:
            parts.append(_("LC: %s", self.lc_ref))
        if self.boe_ref:
            parts.append(_("BoE: %s", self.boe_ref))
        return parts

    def _grouped(self, domain, keys):
        """Aggregate validated ledger rows by ``keys`` and movement type."""
        groups = self.env['bond.warehouse.ledger'].read_group(
            domain, ['qty_in', 'qty_out', 'signed_qty'], keys + ['move_type'], lazy=False)
        result = {}
        for g in groups:
            key = tuple(self._name_of(g.get(k)) for k in keys)
            b = result.setdefault(key, dict.fromkeys(
                ['receipt', 'return_in', 'issue', 'return_out', 'transfer_in', 'transfer_out',
                 'adjustment', 'balance'], 0.0))
            move_type = g.get('move_type')
            qin, qout, net = g.get('qty_in') or 0.0, g.get('qty_out') or 0.0, g.get('signed_qty') or 0.0
            if move_type in ('receipt', 'return_in'):
                b[move_type] += qin
            elif move_type in ('issue', 'return_out'):
                b[move_type] += qout
            elif move_type == 'transfer':
                b['transfer_in'] += qin
                b['transfer_out'] += qout
            elif move_type == 'adjustment':
                b['adjustment'] += net
            b['balance'] += net
        return result

    # ------------------------------------------------------------------
    # Report builders - each returns (headers, rows, notes)
    # ------------------------------------------------------------------
    def _stock_table(self, ref_field, ref_label):
        domain = self._base_domain() + self._asof_domain()
        keys = [ref_field, 'product_id', 'product_uom_id']
        data = self._grouped(domain, keys)
        headers = [ref_label, 'Product', 'UoM', 'Receipts', 'Returns In', 'Issues', 'Returns Out',
                   'Transfers (net)', 'Adjustments', 'Balance']
        rows = []
        for key in sorted(data, key=lambda k: tuple(str(x) for x in k)):
            b = data[key]
            rows.append([key[0] or '(not recorded)', key[1], key[2], b['receipt'], b['return_in'],
                         b['issue'], b['return_out'], b['transfer_in'] - b['transfer_out'],
                         b['adjustment'], b['balance']])
        notes = [_("Balance = all validated Odoo movements up to the end date, including adjustments "
                   "not yet approved for bond purposes.")]
        return headers, rows, notes

    def _data_lc_wise(self):
        return self._stock_table('lc_ref', 'LC Reference')

    def _data_boe_wise(self):
        return self._stock_table('boe_ref', 'Bill of Entry')

    def _data_classification(self):
        domain = self._base_domain() + self._asof_domain()
        data = self._grouped(domain, ['bond_classification', 'product_id', 'product_uom_id'])
        labels = dict(self.env['bond.warehouse.ledger']._fields['bond_classification'].selection)
        headers = ['Classification', 'Product', 'UoM', 'Receipts', 'Returns In', 'Issues',
                   'Returns Out', 'Transfers (net)', 'Adjustments', 'Balance']
        rows = [[labels.get(k[0], k[0]), k[1], k[2], b['receipt'], b['return_in'], b['issue'],
                 b['return_out'], b['transfer_in'] - b['transfer_out'], b['adjustment'], b['balance']]
                for k, b in sorted(data.items(), key=lambda i: tuple(str(x) for x in i[0]))]
        return headers, rows, []

    def _data_product_hs(self):
        domain = self._base_domain() + self._asof_domain()
        data = self._grouped(domain, ['product_id', 'hs_code', 'product_uom_id'])
        headers = ['Product', 'HS Code', 'UoM', 'Receipts', 'Returns In', 'Issues', 'Returns Out',
                   'Transfers (net)', 'Adjustments', 'Balance']
        rows = [[k[0], k[1] or '(not set)', k[2], b['receipt'], b['return_in'], b['issue'],
                 b['return_out'], b['transfer_in'] - b['transfer_out'], b['adjustment'], b['balance']]
                for k, b in sorted(data.items(), key=lambda i: tuple(str(x) for x in i[0]))]
        return headers, rows, []

    def _data_location_ledger(self):
        domain = self._base_domain() + self._period_domain()
        records = self.env['bond.warehouse.ledger'].search_read(
            domain, ['date', 'reference', 'product_id', 'lot_id', 'location_id',
                     'counterpart_location_id', 'move_type', 'qty_in', 'qty_out',
                     'running_balance', 'product_uom_id', 'lc_ref', 'boe_ref', 'processed_by_id'],
            order='location_id, product_id, lot_id, date, id', limit=LEDGER_LIMIT)
        headers = ['Location', 'Date', 'Reference', 'Product', 'Lot/Batch', 'Source / Destination',
                   'Type', 'Qty In', 'Qty Out', 'Running Balance', 'UoM', 'LC', 'BoE', 'User']
        types = dict(self.env['bond.warehouse.ledger']._fields['move_type'].selection)
        rows = [[self._name_of(r['location_id']), r['date'], r['reference'], self._name_of(r['product_id']),
                 self._name_of(r['lot_id']), self._name_of(r['counterpart_location_id']),
                 types.get(r['move_type'], ''), r['qty_in'], r['qty_out'], r['running_balance'],
                 self._name_of(r['product_uom_id']), r['lc_ref'], r['boe_ref'],
                 self._name_of(r['processed_by_id'])] for r in records]
        notes = [_("Running balance is per product / lot / location over all validated movements.")]
        if len(records) >= LEDGER_LIMIT:
            notes.append(_("Output truncated at %s rows. Narrow the filters.", LEDGER_LIMIT))
        return headers, rows, notes

    def _data_rir(self):
        if not (self.date_from and self.date_to):
            raise UserError(_("Select both period dates for this report."))
        base = self._base_domain()
        opening = self._grouped(base + [('date', '<', self._bound(self.date_from))],
                                ['product_id', 'product_uom_id'])
        period = self._grouped(base + self._period_domain(), ['product_id', 'product_uom_id'])
        headers = ['Product', 'UoM', 'Opening', 'Receipts', 'Returns In', 'Issues', 'Returns Out',
                   'Transfers (net)', 'Adjustments', 'Closing']
        rows = []
        for key in sorted(set(opening) | set(period), key=lambda k: tuple(str(x) for x in k)):
            o = opening.get(key, {}).get('balance', 0.0)
            b = period.get(key, dict.fromkeys(['receipt', 'return_in', 'issue', 'return_out',
                                               'transfer_in', 'transfer_out', 'adjustment', 'balance'], 0.0))
            rows.append([key[0], key[1], o, b['receipt'], b['return_in'], b['issue'], b['return_out'],
                         b['transfer_in'] - b['transfer_out'], b['adjustment'], o + b['balance']])
        notes = [_("Closing = Opening + all validated movements of the period (adjustments included "
                   "whether or not approved). The reconciliation counts approved adjustments only.")]
        return headers, rows, notes

    def _data_entitlement(self):
        domain = self._base_domain() + self._asof_domain() + [('entitlement_ref', '!=', False)]
        data = self._grouped(domain, ['entitlement_ref', 'product_id', 'product_uom_id'])
        headers = ['Entitlement', 'Product', 'UoM', 'Received', 'Returned In', 'Issued',
                   'Returned Out', 'Balance']
        rows = [[k[0], k[1], k[2], b['receipt'], b['return_in'], b['issue'], b['return_out'], b['balance']]
                for k, b in sorted(data.items(), key=lambda i: tuple(str(x) for x in i[0]))]
        notes = [_("Entitlement limits are not stored in this module and no limit is assumed. "
                   "Compare these quantities against the approved entitlement register / customs record.")]
        return headers, rows, notes

    def _data_discrepancy(self):
        domain = [('has_discrepancy', '=', True), ('company_id', '=', self.company_id.id),
                  ('reconciliation_id.state', '!=', 'draft')]
        if self.reconciliation_id:
            domain.append(('reconciliation_id', '=', self.reconciliation_id.id))
        else:
            if self.date_from:
                domain.append(('reconciliation_id.date_to', '>=', self.date_from))
            if self.date_to:
                domain.append(('reconciliation_id.date_from', '<=', self.date_to))
        lines = self.env['bond.warehouse.reconciliation.line'].search(domain)
        headers = ['Reconciliation', 'Status', 'Product', 'Lot/Batch', 'UoM', 'Book Closing', 'Odoo Stock',
                   'Odoo - Book', 'Physical', 'Physical - Book', 'Unapproved Adj.', 'Explanation']
        state_labels = dict(self.env['bond.warehouse.reconciliation']._fields['state'].selection)
        rows = [[l.reconciliation_id.name, state_labels.get(l.reconciliation_id.state),
                 l.product_id.display_name, l.lot_id.name or '', l.uom_id.name, l.closing_qty,
                 l.system_qty if l.system_available else '', l.system_diff,
                 l.physical_qty if l.physical_counted else '', l.physical_diff,
                 l.unapproved_adjustment_qty, l.reason or ''] for l in lines]
        return headers, rows, []

    def _data_missing_docs(self):
        domain = self._base_domain() + self._period_domain() + [('picking_id', '!=', False)]
        records = self.env['bond.warehouse.ledger'].search_read(
            domain, ['picking_id', 'date', 'move_type', 'lc_ref', 'boe_ref', 'license_ref', 'has_documents'])
        types = dict(self.env['bond.warehouse.ledger']._fields['move_type'].selection)
        found = {}
        for r in records:
            pid = r['picking_id'][0]
            if pid in found:
                continue
            missing = []
            if self.require_lc and not r['lc_ref']:
                missing.append('LC reference')
            if self.require_boe and not r['boe_ref']:
                missing.append('Bill of Entry')
            if self.require_license and not r['license_ref']:
                missing.append('License reference')
            if self.require_attachment and not r['has_documents']:
                missing.append('Attachment')
            if missing:
                found[pid] = [r['picking_id'][1], r['date'], types.get(r['move_type'], ''),
                              r['lc_ref'], r['boe_ref'], r['license_ref'], ', '.join(missing)]
        headers = ['Transfer', 'Date', 'Type', 'LC', 'BoE', 'License', 'Missing']
        notes = [_("Which items are required is configurable in the report options. No legal "
                   "requirement is assumed by this report.")]
        return headers, sorted(found.values(), key=lambda x: str(x[1])), notes

    def _license_expiry_map(self):
        """Discover licence validity from an optional ``bond.warehouse.license`` model.

        Nothing is assumed: it is used only if the model exists and exposes a
        ``name`` field and one date field from a short list of common names.
        """
        if 'bond.warehouse.license' not in self.env:
            return None
        model = self.env['bond.warehouse.license']
        field = next((f for f in ('expiry_date', 'date_expiry', 'valid_until', 'valid_to',
                                  'date_end', 'date_to')
                      if f in model._fields and model._fields[f].type in ('date', 'datetime')), None)
        if not field or 'name' not in model._fields:
            return None
        return {r['name']: r[field] for r in model.sudo().search_read([], ['name', field])}

    def _data_exceptions(self):
        Ledger = self.env['bond.warehouse.ledger']
        base = self._base_domain() + self._period_domain()
        fields_ = ['date', 'reference', 'product_id', 'lot_id', 'qty_in', 'qty_out', 'license_ref',
                   'move_type', 'picking_id', 'move_line_id', 'verification_state']
        seen, rows = set(), []

        def add(kind, rec, detail):
            key = (kind, rec['move_line_id'][0] if rec['move_line_id'] else rec['id'])
            if key in seen:
                return
            seen.add(key)
            rows.append([kind, rec['reference'], rec['date'], self._name_of(rec['product_id']),
                         self._name_of(rec['lot_id']), rec['qty_in'] or rec['qty_out'],
                         rec['license_ref'] or '', detail])

        expiry = self._license_expiry_map()
        non_transfer = [('move_type', '!=', 'transfer')]
        for rec in Ledger.search_read(base + non_transfer + [('license_ref', '=', False)], fields_):
            add('No license reference', rec, 'Bonded movement without a license reference')
        for rec in Ledger.search_read(base + [('verification_state', '=', 'rejected')], fields_):
            add('Verification rejected', rec, 'Transaction verification was rejected')
        for rec in Ledger.search_read(
                base + non_transfer + [('move_type', '!=', 'adjustment'),
                                       ('verification_state', 'in', ['draft', 'pending'])], fields_):
            add('Not verified', rec, 'Validated movement not yet verified')
        for rec in Ledger.search_read(
                base + [('move_type', '=', 'adjustment'), ('adj_approved', '=', False)], fields_):
            add('Unapproved adjustment', rec, 'Adjustment not approved; excluded from reconciliations')
        if expiry is not None:
            for rec in Ledger.search_read(base + non_transfer + [('license_ref', '!=', False)], fields_):
                lic = rec['license_ref']
                if lic not in expiry:
                    add('Unknown license', rec, 'License reference not found in the license register')
                elif expiry[lic] and fields.Datetime.to_datetime(rec['date']).date() > fields.Date.to_date(expiry[lic]):
                    add('Expired license', rec, 'Movement dated after license expiry %s' % expiry[lic])
        headers = ['Exception', 'Reference', 'Date', 'Product', 'Lot/Batch', 'Qty', 'License', 'Detail']
        notes = []
        if expiry is None:
            notes.append(_("License validity was NOT checked: no readable license register "
                           "(bond.warehouse.license with name and an expiry date field) was found."))
        else:
            notes.append(_("License validity checked against the license register (expiry date only)."))
        return headers, sorted(rows, key=lambda r: (r[0], str(r[2]))), notes

    def _data_audit_index(self):
        records = self.env['bond.warehouse.ledger'].search_read(
            self._base_domain() + self._period_domain() + [('picking_id', '!=', False)],
            ['picking_id', 'date', 'lc_ref', 'boe_ref', 'license_ref'])
        picks = {}
        for r in records:
            picks.setdefault(r['picking_id'][0], r)
        attachments = self.env['ir.attachment'].search_read(
            [('res_model', '=', 'stock.picking'), ('res_id', 'in', list(picks))],
            ['res_id', 'name', 'mimetype', 'create_uid', 'create_date'], order='res_id, id')
        headers = ['Transfer', 'Date', 'LC', 'BoE', 'License', 'Document', 'Type', 'Uploaded By', 'Uploaded On']
        rows = []
        for a in attachments:
            r = picks[a['res_id']]
            rows.append([r['picking_id'][1], r['date'], r['lc_ref'], r['boe_ref'], r['license_ref'],
                         a['name'], a['mimetype'], self._name_of(a['create_uid']), a['create_date']])
        return headers, rows, [_("Lists attachments of validated transfers in scope. Transfers "
                                 "without attachments appear in the Missing Document Report.")]

    def _data_register_export(self):
        domain = [('company_id', '=', self.company_id.id)]
        if self.bond_classification != 'all':
            domain.append(('bond_classification', '=', self.bond_classification))
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
        if self.location_ids:
            domain.append(('location_id', 'child_of', self.location_ids.ids))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.lc_ref:
            domain.append(('lc_ref', '=', self.lc_ref.strip()))
        if self.boe_ref:
            domain.append(('boe_ref', '=', self.boe_ref.strip()))
        recs = self.env['bond.warehouse.register'].search(domain)
        verif = dict(self.env['bond.warehouse.register']._fields['verification_state'].selection)
        headers = ['Company', 'License', 'LC', 'BoE', 'Product', 'HS Code', 'Lot/Batch', 'Classification',
                   'Warehouse', 'Location', 'UoM', 'Received', 'Returned In', 'Issued', 'Returned Out',
                   'Transfers In', 'Transfers Out', 'Approved Adj.', 'Unapproved Adj.', 'Balance',
                   'Traceable Balance', 'First Receipt', 'Last Movement', 'Receipts', 'Verification']
        classes = dict(self.env['bond.warehouse.register']._fields['bond_classification'].selection)
        rows = [[r.company_id.name, r.license_ref, r.lc_ref, r.boe_ref, r.product_id.display_name,
                 r.hs_code, r.lot_id.name, classes.get(r.bond_classification), r.warehouse_id.name,
                 r.location_id.complete_name, r.product_uom_id.name, r.received_qty, r.return_in_qty,
                 r.issued_qty, r.return_out_qty, r.transfer_in_qty, r.transfer_out_qty, r.adjusted_qty,
                 r.unapproved_adjusted_qty, r.balance_qty, r.traceable_balance_qty,
                 r.first_receipt_date, r.last_move_date, r.receipt_refs, verif.get(r.verification_state)]
                for r in recs]
        return headers, rows, [_("Register shows the current validated position (no as-of date).")]

    # ------------------------------------------------------------------
    def _get_report_data(self):
        self.ensure_one()
        title = dict(REPORT_TYPES)[self.report_type]
        headers, rows, notes = getattr(self, '_data_%s' % self.report_type)()
        return {
            'title': title,
            'headers': headers,
            'rows': rows,
            'notes': notes,
            'filters': self._filters_text(),
            'notice': STATUTORY_NOTICE,
            'generated': '%s - %s' % (fields.Datetime.now(), self.env.user.name),
        }

    @staticmethod
    def _plain(value):
        if value is None or value is False:
            return ''
        return value

    @staticmethod
    def fmt_cell(value):
        if value is None or value is False:
            return ''
        if isinstance(value, float):
            return '{:,.3f}'.format(value)
        return str(value)

    @staticmethod
    def is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref('nelsis_bond_reconciliation.action_report_bond_generic').report_action(self)

    def _attach(self, filename, content, mimetype):
        attachment = self.env['ir.attachment'].create({
            'name': filename, 'type': 'binary', 'datas': base64.b64encode(content),
            'res_model': self._name, 'res_id': self.id, 'mimetype': mimetype,
        })
        return {'type': 'ir.actions.act_url', 'url': '/web/content/%s?download=true' % attachment.id,
                'target': 'self'}

    def action_export_csv(self):
        self.ensure_one()
        data = self._get_report_data()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([data['title']])
        writer.writerow([data['notice']])
        for line in data['filters']:
            writer.writerow([line])
        writer.writerow([])
        writer.writerow(data['headers'])
        for row in data['rows']:
            writer.writerow([self._plain(c) for c in row])
        for note in data['notes']:
            writer.writerow([note])
        return self._attach('bond_%s.csv' % self.report_type, buf.getvalue().encode('utf-8-sig'),
                            'text/csv')

    def action_export_xlsx(self):
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("XLSX export needs the Python package 'xlsxwriter' (pip install xlsxwriter). "
                              "Use CSV or PDF instead."))
        data = self._get_report_data()
        stream = io.BytesIO()
        wb = xlsxwriter.Workbook(stream, {'in_memory': True, 'default_date_format': 'yyyy-mm-dd hh:mm'})
        ws = wb.add_worksheet('Report')
        bold = wb.add_format({'bold': True, 'bg_color': '#1F4E79', 'font_color': '#FFFFFF', 'border': 1})
        warn = wb.add_format({'italic': True, 'font_color': '#9C0006'})
        num = wb.add_format({'num_format': '#,##0.000'})
        ws.write(0, 0, data['title'], wb.add_format({'bold': True, 'font_size': 14}))
        ws.write(1, 0, data['notice'], warn)
        for i, line in enumerate(data['filters']):
            ws.write(2 + i, 0, line)
        top = 3 + len(data['filters'])
        for c, head in enumerate(data['headers']):
            ws.write(top, c, head, bold)
            ws.set_column(c, c, 18)
        for r, row in enumerate(data['rows'], start=top + 1):
            for c, cell in enumerate(row):
                cell = self._plain(cell)
                if isinstance(cell, bool):
                    cell = str(cell)
                if isinstance(cell, (int, float)):
                    ws.write_number(r, c, cell, num)
                else:
                    ws.write(r, c, str(cell))
        for i, note in enumerate(data['notes'], start=top + len(data['rows']) + 2):
            ws.write(i, 0, note)
        ws.freeze_panes(top + 1, 0)
        wb.close()
        return self._attach('bond_%s.xlsx' % self.report_type, stream.getvalue(),
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def action_open_analysis(self):
        """Open the matching interactive list / pivot / graph view."""
        self.ensure_one()
        t = self.report_type
        if t == 'register_export':
            domain = [('company_id', '=', self.company_id.id)]
            if self.bond_classification != 'all':
                domain.append(('bond_classification', '=', self.bond_classification))
            return {'type': 'ir.actions.act_window', 'name': _('Bond Register'),
                    'res_model': 'bond.warehouse.register', 'view_mode': 'tree,pivot,graph',
                    'domain': domain}
        if t in ('discrepancy',):
            return {'type': 'ir.actions.act_window', 'name': _('Discrepancies'),
                    'res_model': 'bond.warehouse.reconciliation.line', 'view_mode': 'tree,form',
                    'domain': [('has_discrepancy', '=', True)]}
        if t in ('missing_docs', 'exceptions', 'audit_index'):
            raise UserError(_("This report has no on-screen analysis view. Use PDF, CSV or XLSX."))
        rows = {
            'lc_wise': ['lc_ref', 'product_id'], 'boe_wise': ['boe_ref', 'product_id'],
            'classification': ['bond_classification', 'product_id'],
            'product_hs': ['hs_code', 'product_id'], 'rir': ['product_id'],
            'entitlement': ['entitlement_ref', 'product_id'], 'location_ledger': ['location_id', 'product_id'],
        }[t]
        domain = self._base_domain() + (self._period_domain() if t in ('rir', 'location_ledger')
                                        else self._asof_domain())
        return {
            'type': 'ir.actions.act_window', 'name': dict(REPORT_TYPES)[t],
            'res_model': 'bond.warehouse.ledger', 'view_mode': 'pivot,tree,graph',
            'domain': domain,
            'context': {'pivot_row_groupby': rows, 'pivot_column_groupby': ['move_type'],
                        'pivot_measures': ['signed_qty']},
        }
