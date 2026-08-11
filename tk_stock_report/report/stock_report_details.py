# -*- coding: utf-8 -*-
from odoo import models, api


class StockReportDetails(models.AbstractModel):
    """
    This class is responsible for generating the stock report template.
    It defines the report structure and data retrieval methods for the stock report.
    """
    _name = 'report.tk_stock_report.stock_report_template'
    _description = 'Stock Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        start_date = data.get('form_data').get('start_date')
        end_date = data.get('form_data').get('end_date')
        location_id = data.get('form_data').get('stock_location_id')
        company_id = data.get('form_data').get('company_id')
        docs = self.env['stock.move'].search([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date),
            ('company_id', '=', company_id[0]),
            ('location_id', '=', location_id[0]),
            ('state', 'not in', ['draft', 'cancel']),
        ], order="date ASC")
        product_moves = {}
        for move in docs:
            product = f"[{move.product_id.default_code}] {move.product_id.name}"
            if product not in product_moves:
                product_moves[product] = {'balance': 0, 'moves': [], 'total_in': 0, 'total_out': 0}
            in_qty = 0
            out_qty = 0
            if move.picking_code == 'incoming':
                in_qty = move.product_qty
            elif move.picking_code == 'outgoing':
                out_qty = move.product_qty
            product_moves[product]['balance'] += in_qty - out_qty
            product_moves[product]['total_in'] += in_qty
            product_moves[product]['total_out'] += out_qty
            product_moves[product]['moves'].append({
                'date': move.date.date(),
                'origin': move.origin or move.reference,
                'in_qty': in_qty,
                'out_qty': out_qty,
                'balance': product_moves[product]['balance']
            })
        return {
            'product_moves': product_moves,
            'data': data,
            'docs': docs,
        }
