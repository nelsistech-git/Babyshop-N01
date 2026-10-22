# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""BOM API (SRS section 35). Simple JSON REST endpoints guarded by the
normal Odoo access rights / record rules of the logged-in user (auth='user')
— no extra sudo() is used, so the same security groups and record rules
configured in security/garment_bom_management_security.xml apply."""

import json

from odoo import http
from odoo.http import request


def _bom_to_dict(bom):
    return {
        'id': bom.id,
        'bom_number': bom.bom_number,
        'bom_type': bom.bom_type,
        'style': bom.style_id.display_name,
        'buyer': bom.buyer_id.display_name,
        'status': bom.status,
        'version': bom.version,
        'revision_number': bom.revision_number,
        'order_quantity': bom.order_quantity,
        'cost_per_piece': bom.cost_per_piece,
        'total_material_cost': bom.total_material_cost,
        'is_locked': bom.is_locked,
    }


class GarmentBomApiController(http.Controller):

    @http.route('/api/bom/<int:bom_id>', type='http', auth='user', methods=['GET'], csrf=False)
    def get_bom(self, bom_id, **kwargs):
        bom = request.env['garment.bom'].browse(bom_id).exists()
        if not bom:
            return request.make_response(json.dumps({'error': 'BOM not found'}), status=404,
                                          headers=[('Content-Type', 'application/json')])
        return request.make_response(json.dumps(_bom_to_dict(bom)),
                                      headers=[('Content-Type', 'application/json')])

    @http.route('/api/bom', type='http', auth='user', methods=['POST'], csrf=False)
    def create_bom(self, **kwargs):
        payload = json.loads(request.httprequest.data or b'{}')
        style_id = payload.get('style_id')
        if not style_id:
            return request.make_response(json.dumps({'error': 'style_id is required'}), status=400,
                                          headers=[('Content-Type', 'application/json')])
        vals = {k: v for k, v in payload.items() if k in request.env['garment.bom']._fields}
        bom = request.env['garment.bom'].create(vals)
        return request.make_response(json.dumps(_bom_to_dict(bom)), status=201,
                                      headers=[('Content-Type', 'application/json')])

    @http.route('/api/bom/<int:bom_id>', type='http', auth='user', methods=['PUT'], csrf=False)
    def update_bom(self, bom_id, **kwargs):
        bom = request.env['garment.bom'].browse(bom_id).exists()
        if not bom:
            return request.make_response(json.dumps({'error': 'BOM not found'}), status=404,
                                          headers=[('Content-Type', 'application/json')])
        payload = json.loads(request.httprequest.data or b'{}')
        vals = {k: v for k, v in payload.items() if k in bom._fields}
        bom.write(vals)
        return request.make_response(json.dumps(_bom_to_dict(bom)),
                                      headers=[('Content-Type', 'application/json')])

    @http.route('/api/bom/<int:bom_id>/approve', type='http', auth='user', methods=['POST'], csrf=False)
    def approve_bom(self, bom_id, **kwargs):
        bom = request.env['garment.bom'].browse(bom_id).exists()
        if not bom:
            return request.make_response(json.dumps({'error': 'BOM not found'}), status=404,
                                          headers=[('Content-Type', 'application/json')])
        bom.action_approve_final()
        return request.make_response(json.dumps(_bom_to_dict(bom)),
                                      headers=[('Content-Type', 'application/json')])

    @http.route('/api/bom/<int:bom_id>/requirements', type='http', auth='user', methods=['GET'], csrf=False)
    def bom_requirements(self, bom_id, **kwargs):
        bom = request.env['garment.bom'].browse(bom_id).exists()
        if not bom:
            return request.make_response(json.dumps({'error': 'BOM not found'}), status=404,
                                          headers=[('Content-Type', 'application/json')])
        requirements = []
        for line in bom.fabric_bom_ids:
            requirements.append({'category': 'fabric', 'name': line.fabric_name or line.fabric_role,
                                  'required_qty': line.required_qty, 'purchase_qty': line.purchase_qty,
                                  'uom': line.uom})
        for line in bom.trim_bom_ids:
            requirements.append({'category': 'trim', 'name': line.description or line.trim_type,
                                  'required_qty': line.required_qty, 'purchase_qty': line.purchase_qty,
                                  'uom': line.uom})
        for line in bom.packaging_bom_ids:
            requirements.append({'category': 'packaging', 'name': line.description or line.packaging_type,
                                  'required_qty': line.required_qty, 'purchase_qty': line.purchase_qty,
                                  'uom': line.uom})
        return request.make_response(json.dumps({'bom_id': bom.id, 'requirements': requirements}),
                                      headers=[('Content-Type', 'application/json')])
