# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Supplier Portal (SRS sections 19-20, 37-38). Every route below is a
read-only view (or a very limited profile/document self-service action)
over the real transactional data of Module 9 (Purchase) and Module 12
(Finance) — this module never stores its own copy of RFQ/PO/Delivery/
Payment data, only the supplier master and its own performance/audit/risk
records."""

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

PPG = 20


class GarmentSupplierPortal(CustomerPortal):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_portal_supplier(self):
        """Resolve the garment.supplier this logged-in portal user belongs
        to (SRS section 38 - Supplier Data Privacy: a supplier only ever
        sees its own record)."""
        partner = request.env.user.partner_id
        Supplier = request.env['garment.supplier'].sudo()
        supplier = Supplier.search([('partner_id', '=', partner.id)], limit=1)
        if not supplier:
            commercial = partner.commercial_partner_id
            supplier = Supplier.search([('partner_id', '=', commercial.id)], limit=1)
        return supplier

    def _supplier_dashboard_values(self, supplier):
        """Supplier Portal Dashboard (SRS section 20)."""
        Rfq = request.env['garment.purchase.rfq'].sudo()
        Po = request.env['garment.purchase.order'].sudo()
        Delivery = request.env['garment.purchase.delivery'].sudo()
        partner = supplier.partner_id
        rfqs = Rfq.search([('supplier_id', '=', partner.id)]) if partner else Rfq.browse()
        pos = Po.search([('supplier_id', '=', partner.id)]) if partner else Po.browse()
        deliveries = Delivery.search([('supplier_id', '=', partner.id)]) if partner else Delivery.browse()
        return {
            'garment_supplier': supplier,
            'dash_rfq_total': len(rfqs),
            'dash_quotation_pending': len(rfqs.filtered(lambda r: r.status in ('draft', 'sent'))),
            'dash_po_confirmed': len(pos.filtered(lambda p: p.status in ('approved', 'sent'))),
            'dash_delivered_orders': len(pos.filtered(lambda p: p.status in ('received', 'closed'))),
            'dash_delivery_upcoming': len(deliveries.filtered(
                lambda d: d.quality_status == 'pending' and not d.actual_date)),
            'dash_delivery_delayed': len(deliveries.filtered(lambda d: d.delay_days and d.delay_days > 0)),
            'dash_delivery_completed': len(deliveries.filtered(lambda d: d.actual_date)),
            'dash_payment_pending': supplier.payment_pending_count,
            'dash_payment_paid': supplier.payment_paid_count,
            'dash_payment_due': supplier.payment_due_amount,
        }

    # ------------------------------------------------------------------
    # Home / Dashboard
    # ------------------------------------------------------------------
    @http.route(['/my/supplier'], type='http', auth='user', website=True)
    def portal_supplier_home(self, **kw):
        supplier = self._get_portal_supplier()
        values = self._prepare_portal_layout_values()
        if supplier:
            values.update(self._supplier_dashboard_values(supplier))
        values['page_name'] = 'garment_supplier'
        return request.render('garment_supplier.portal_supplier_home', values)

    # ------------------------------------------------------------------
    # Profile (SRS section 38: Profile edit is Limited for a Supplier User)
    # ------------------------------------------------------------------
    @http.route(['/my/supplier/profile'], type='http', auth='user', website=True)
    def portal_supplier_profile(self, **kw):
        supplier = self._get_portal_supplier()
        if not supplier:
            return request.redirect('/my/supplier')
        values = self._prepare_portal_layout_values()
        values.update({'garment_supplier': supplier, 'page_name': 'garment_supplier'})
        return request.render('garment_supplier.portal_supplier_profile', values)

    @http.route(['/my/supplier/profile/update'], type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def portal_supplier_profile_update(self, **post):
        supplier = self._get_portal_supplier()
        if not supplier:
            return request.redirect('/my/supplier')
        # Limited self-service fields only (SRS section 38) - never
        # classification/status/rating/compliance, which stay internal.
        allowed = ('contact_person', 'email', 'phone', 'website', 'factory_location',
                   'production_capacity', 'employee_count')
        vals = {k: post.get(k) for k in allowed if post.get(k) is not None}
        if vals:
            supplier.sudo().write(vals)
        return request.redirect('/my/supplier/profile')

    # ------------------------------------------------------------------
    # Documents (SRS section 19 - Document Upload)
    # ------------------------------------------------------------------
    @http.route(['/my/supplier/documents'], type='http', auth='user', website=True)
    def portal_supplier_documents(self, **kw):
        supplier = self._get_portal_supplier()
        Document = request.env['garment.supplier.document'].sudo()
        documents = Document.search([('supplier_id', '=', supplier.id)]) if supplier else Document.browse()
        values = self._prepare_portal_layout_values()
        values.update({'garment_supplier': supplier, 'documents': documents, 'page_name': 'garment_supplier'})
        return request.render('garment_supplier.portal_supplier_documents', values)

    @http.route(['/my/supplier/documents/upload'], type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def portal_supplier_document_upload(self, document_type=None, name=None, upload=None, **post):
        supplier = self._get_portal_supplier()
        if supplier and upload:
            request.env['garment.supplier.document'].sudo().create({
                'supplier_id': supplier.id,
                'document_type': document_type or 'other',
                'name': name or upload.filename,
                'attachment': upload.read(),
                'attachment_filename': upload.filename,
            })
        return request.redirect('/my/supplier/documents')

    # ------------------------------------------------------------------
    # RFQ / PO / Delivery (read-only - SRS sections 22-24)
    # ------------------------------------------------------------------
    @http.route(['/my/supplier/rfqs', '/my/supplier/rfqs/page/<int:page>'], type='http', auth='user', website=True)
    def portal_supplier_rfqs(self, page=1, **kw):
        supplier = self._get_portal_supplier()
        Rfq = request.env['garment.purchase.rfq'].sudo()
        domain = [('supplier_id', '=', supplier.partner_id.id)] if supplier and supplier.partner_id else [('id', '=', 0)]
        count = Rfq.search_count(domain)
        pager = portal_pager(url='/my/supplier/rfqs', total=count, page=page, step=PPG)
        rfqs = Rfq.search(domain, order='create_date desc', limit=PPG, offset=pager['offset'])
        values = self._prepare_portal_layout_values()
        values.update({'rfqs': rfqs, 'pager': pager, 'default_url': '/my/supplier/rfqs',
                       'page_name': 'garment_supplier'})
        return request.render('garment_supplier.portal_supplier_rfqs', values)

    @http.route(['/my/supplier/pos', '/my/supplier/pos/page/<int:page>'], type='http', auth='user', website=True)
    def portal_supplier_pos(self, page=1, **kw):
        supplier = self._get_portal_supplier()
        Po = request.env['garment.purchase.order'].sudo()
        domain = [('supplier_id', '=', supplier.partner_id.id)] if supplier and supplier.partner_id else [('id', '=', 0)]
        count = Po.search_count(domain)
        pager = portal_pager(url='/my/supplier/pos', total=count, page=page, step=PPG)
        orders = Po.search(domain, order='order_date desc', limit=PPG, offset=pager['offset'])
        values = self._prepare_portal_layout_values()
        values.update({'orders': orders, 'pager': pager, 'default_url': '/my/supplier/pos',
                       'page_name': 'garment_supplier'})
        return request.render('garment_supplier.portal_supplier_pos', values)

    @http.route(['/my/supplier/deliveries', '/my/supplier/deliveries/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_supplier_deliveries(self, page=1, **kw):
        supplier = self._get_portal_supplier()
        Delivery = request.env['garment.purchase.delivery'].sudo()
        domain = [('supplier_id', '=', supplier.partner_id.id)] if supplier and supplier.partner_id else [('id', '=', 0)]
        count = Delivery.search_count(domain)
        pager = portal_pager(url='/my/supplier/deliveries', total=count, page=page, step=PPG)
        deliveries = Delivery.search(domain, order='expected_date desc', limit=PPG, offset=pager['offset'])
        values = self._prepare_portal_layout_values()
        values.update({'deliveries': deliveries, 'pager': pager, 'default_url': '/my/supplier/deliveries',
                       'page_name': 'garment_supplier'})
        return request.render('garment_supplier.portal_supplier_deliveries', values)
