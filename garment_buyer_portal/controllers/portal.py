# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

PPG = 20  # records per page (Odoo portal convention)


class GarmentBuyerPortal(CustomerPortal):
    """Buyer Portal controller (SRS Module 10). Every route below is a
    read-only view or a buyer-approval-action over the real transactional
    models of the other Nelsis Smart Garment modules - this module never
    stores its own copy of order/sample/shipment/techpack/quality data."""

    # ==================================================================
    # Helpers
    # ==================================================================
    def _get_portal_buyer(self):
        """Resolve the garment.buyer this logged-in portal user belongs to
        (SRS section 24 - Buyer Access Control)."""
        partner = request.env.user.partner_id
        buyer = partner.garment_buyer_id
        if not buyer:
            commercial = partner.commercial_partner_id
            buyer = request.env['garment.buyer'].sudo().search([('partner_id', '=', commercial.id)], limit=1)
        return buyer

    def _log_activity(self, activity_type, description, res_model=False, res_id=False):
        partner = request.env.user.partner_id
        request.env['garment.portal.activity.log'].log(
            partner, activity_type, description, res_model=res_model, res_id=res_id, http_request=request)

    def _document_check_access(self, model_name, document_id):
        """Fetch `document_id` of `model_name` and make sure it belongs to
        the current portal buyer (SRS section 25 - Data Visibility Rules)."""
        document_sudo = request.env[model_name].sudo().browse(document_id).exists()
        if not document_sudo:
            raise MissingError(_('This document does not exist.'))
        buyer = self._get_portal_buyer()
        if not buyer or document_sudo.buyer_id != buyer:
            raise AccessError(_('You do not have access to this document.'))
        return document_sudo

    def _buyer_dashboard_values(self, buyer):
        """Buyer Dashboard cards (SRS section 8)."""
        Order = request.env['garment.order'].sudo()
        Sample = request.env['garment.sample'].sudo()
        Shipment = request.env['garment.shipment'].sudo()
        orders = Order.search([('buyer_id', '=', buyer.id)])
        samples = Sample.search([('buyer_id', '=', buyer.id)])
        shipments = Shipment.search([('buyer_id', '=', buyer.id)])
        running_states = ('confirmed', 'tna_created', 'material_planning', 'production_running',
                           'quality_checking', 'ready_for_shipment')
        upcoming_states = ('planning', 'allocation', 'booking')
        transit_states = ('loading', 'port', 'vessel_departed', 'in_transit')
        return {
            'garment_buyer': buyer,
            'dashboard_orders_total': len(orders),
            'dashboard_orders_running': len(orders.filtered(lambda o: o.state in running_states)),
            'dashboard_orders_completed': len(orders.filtered(lambda o: o.state in ('completed', 'closed'))),
            'dashboard_samples_pending': len(samples.filtered(
                lambda s: s.status in ('submitted', 'buyer_review', 'comments_received'))),
            'dashboard_samples_approved': len(samples.filtered(lambda s: s.status == 'approved')),
            'dashboard_samples_revision': len(samples.filtered(lambda s: s.status == 'revision')),
            'dashboard_shipments_upcoming': len(shipments.filtered(lambda s: s.status in upcoming_states)),
            'dashboard_shipments_transit': len(shipments.filtered(lambda s: s.status in transit_states)),
            'dashboard_shipments_delivered': len(shipments.filtered(lambda s: s.status == 'delivered')),
        }

    # ==================================================================
    # Home / Dashboard (SRS section 8)
    # ==================================================================
    @http.route(['/my', '/my/home'], type='http', auth='user', website=True)
    def home(self, **kw):
        response = super().home(**kw)
        buyer = self._get_portal_buyer()
        if buyer and hasattr(response, 'qcontext'):
            response.qcontext.update(self._buyer_dashboard_values(buyer))
            self._log_activity('login', _('Buyer portal dashboard viewed.'))
        return response

    # ==================================================================
    # Orders (SRS sections 9-10)
    # ==================================================================
    @http.route(['/my/orders', '/my/orders/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_orders(self, page=1, sortby=None, **kw):
        buyer = self._get_portal_buyer()
        Order = request.env['garment.order'].sudo()
        domain = [('buyer_id', '=', buyer.id)] if buyer else [('id', '=', 0)]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'order_date desc'},
            'name': {'label': _('Order Number'), 'order': 'name desc'},
            'delivery': {'label': _('Delivery Date'), 'order': 'delivery_date asc'},
        }
        sortby = sortby if sortby in searchbar_sortings else 'date'
        order_by = searchbar_sortings[sortby]['order']

        order_count = Order.search_count(domain)
        pager = portal_pager(url='/my/orders', total=order_count, page=page, step=PPG,
                              url_args={'sortby': sortby})
        orders = Order.search(domain, order=order_by, limit=PPG, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'orders': orders,
            'page_name': 'garment_order',
            'pager': pager,
            'default_url': '/my/orders',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render('garment_buyer_portal.portal_my_orders', values)

    @http.route(['/my/orders/<int:order_id>'], type='http', auth='user', website=True)
    def portal_order_detail(self, order_id, **kw):
        order = self._document_check_access('garment.order', order_id)
        self._log_activity('view_order', _('Viewed Order %s') % order.name, 'garment.order', order.id)
        values = {'order': order, 'page_name': 'garment_order'}
        return request.render('garment_buyer_portal.portal_order_detail', values)

    # ==================================================================
    # Samples (SRS section 12)
    # ==================================================================
    @http.route(['/my/samples', '/my/samples/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_samples(self, page=1, **kw):
        buyer = self._get_portal_buyer()
        Sample = request.env['garment.sample'].sudo()
        domain = [('buyer_id', '=', buyer.id)] if buyer else [('id', '=', 0)]

        sample_count = Sample.search_count(domain)
        pager = portal_pager(url='/my/samples', total=sample_count, page=page, step=PPG)
        samples = Sample.search(domain, order='create_date desc', limit=PPG, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'samples': samples, 'page_name': 'garment_sample',
            'pager': pager, 'default_url': '/my/samples',
        })
        return request.render('garment_buyer_portal.portal_my_samples', values)

    @http.route(['/my/samples/<int:sample_id>'], type='http', auth='user', website=True)
    def portal_sample_detail(self, sample_id, **kw):
        sample = self._document_check_access('garment.sample', sample_id)
        self._log_activity('view_sample', _('Viewed Sample %s') % sample.sample_number,
                            'garment.sample', sample.id)
        values = {'sample': sample, 'page_name': 'garment_sample'}
        return request.render('garment_buyer_portal.portal_sample_detail', values)

    # ==================================================================
    # Shipments (SRS section 30)
    # ==================================================================
    @http.route(['/my/shipments', '/my/shipments/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_shipments(self, page=1, **kw):
        buyer = self._get_portal_buyer()
        Shipment = request.env['garment.shipment'].sudo()
        domain = [('buyer_id', '=', buyer.id)] if buyer else [('id', '=', 0)]

        shipment_count = Shipment.search_count(domain)
        pager = portal_pager(url='/my/shipments', total=shipment_count, page=page, step=PPG)
        shipments = Shipment.search(domain, order='shipment_date desc', limit=PPG, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'shipments': shipments, 'page_name': 'garment_shipment',
            'pager': pager, 'default_url': '/my/shipments',
        })
        return request.render('garment_buyer_portal.portal_my_shipments', values)

    @http.route(['/my/shipments/<int:shipment_id>'], type='http', auth='user', website=True)
    def portal_shipment_detail(self, shipment_id, **kw):
        shipment = self._document_check_access('garment.shipment', shipment_id)
        self._log_activity('view_shipment', _('Viewed Shipment %s') % shipment.shipment_no,
                            'garment.shipment', shipment.id)
        values = {'shipment': shipment, 'page_name': 'garment_shipment'}
        return request.render('garment_buyer_portal.portal_shipment_detail', values)

    # ==================================================================
    # Quality (SRS section 29)
    # ==================================================================
    @http.route(['/my/quality', '/my/quality/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_quality(self, page=1, **kw):
        buyer = self._get_portal_buyer()
        Inspection = request.env['garment.quality.inspection'].sudo()
        domain = [('buyer_id', '=', buyer.id), ('state', 'in', ('approved', 'released'))] \
            if buyer else [('id', '=', 0)]

        inspection_count = Inspection.search_count(domain)
        pager = portal_pager(url='/my/quality', total=inspection_count, page=page, step=PPG)
        inspections = Inspection.search(domain, order='inspection_date desc', limit=PPG, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'inspections': inspections, 'page_name': 'garment_quality_inspection',
            'pager': pager, 'default_url': '/my/quality',
        })
        return request.render('garment_buyer_portal.portal_my_quality', values)

    @http.route(['/my/quality/<int:inspection_id>'], type='http', auth='user', website=True)
    def portal_quality_detail(self, inspection_id, **kw):
        inspection = self._document_check_access('garment.quality.inspection', inspection_id)
        self._log_activity('view_quality', _('Viewed Inspection %s') % inspection.inspection_no,
                            'garment.quality.inspection', inspection.id)
        values = {'inspection': inspection, 'page_name': 'garment_quality_inspection'}
        return request.render('garment_buyer_portal.portal_quality_detail', values)

    # ==================================================================
    # Tech Packs (context page reached from the Approvals inbox - SRS 32)
    # ==================================================================
    @http.route(['/my/techpacks/<int:techpack_id>'], type='http', auth='user', website=True)
    def portal_techpack_detail(self, techpack_id, **kw):
        techpack = self._document_check_access('garment.techpack', techpack_id)
        self._log_activity('view_approval', _('Viewed Tech Pack %s') % techpack.name,
                            'garment.techpack', techpack.id)
        values = {'techpack': techpack, 'page_name': 'garment_techpack'}
        return request.render('garment_buyer_portal.portal_techpack_detail', values)

    # ==================================================================
    # Approvals inbox — Tech Pack / Sample / Style buyer sign-off
    # (SRS sections 12, 26, 32)
    # ==================================================================
    @http.route(['/my/approvals', '/my/approvals/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_approvals(self, page=1, filterby=None, **kw):
        buyer = self._get_portal_buyer()
        Approval = request.env['garment.portal.approval.action'].sudo()
        if buyer:
            Approval._sync_pending_for_buyer(buyer)
        domain = [('buyer_id', '=', buyer.id)] if buyer else [('id', '=', 0)]

        searchbar_filters = {
            'pending': {'label': _('Pending'), 'domain': [('decision', '=', 'pending')]},
            'all': {'label': _('All'), 'domain': []},
        }
        filterby = filterby if filterby in searchbar_filters else 'pending'
        domain = domain + searchbar_filters[filterby]['domain']

        approval_count = Approval.search_count(domain)
        pager = portal_pager(url='/my/approvals', total=approval_count, page=page, step=PPG,
                              url_args={'filterby': filterby})
        approvals = Approval.search(domain, order='requested_date desc', limit=PPG, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'approvals': approvals, 'page_name': 'garment_portal_approval',
            'pager': pager, 'default_url': '/my/approvals',
            'searchbar_filters': searchbar_filters, 'filterby': filterby,
        })
        return request.render('garment_buyer_portal.portal_my_approvals', values)

    @http.route(['/my/approvals/<int:approval_id>'], type='http', auth='user', website=True)
    def portal_approval_detail(self, approval_id, **kw):
        approval = self._document_check_access('garment.portal.approval.action', approval_id)
        self._log_activity('view_approval', _('Viewed approval %s') % approval.name,
                            'garment.portal.approval.action', approval.id)
        values = {'approval': approval, 'page_name': 'garment_portal_approval'}
        return request.render('garment_buyer_portal.portal_approval_detail', values)

    @http.route(['/my/approvals/<int:approval_id>/action'], type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def portal_approval_action(self, approval_id, decision=None, comments=None, **kw):
        approval = self._document_check_access('garment.portal.approval.action', approval_id)
        if decision not in ('approved', 'revision_required', 'rejected'):
            raise UserError(_('Please choose Approve, Request Revision or Reject.'))
        approval.write({
            'decision': decision,
            'comments': comments,
            'partner_id': request.env.user.partner_id.id,
            'ip_address': request.httprequest.remote_addr,
        })
        approval.action_apply_decision()
        self._log_activity('approval_decision', _('Recorded "%s" decision on %s') % (decision, approval.name),
                            'garment.portal.approval.action', approval.id)
        return request.redirect('/my/approvals/%d' % approval_id)

    # ==================================================================
    # Buyer <-> Factory Messages (SRS sections 13, 16)
    # ==================================================================
    @http.route(['/my/messages', '/my/messages/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_messages(self, page=1, **kw):
        buyer = self._get_portal_buyer()
        Message = request.env['garment.portal.message'].sudo()
        domain = [('buyer_id', '=', buyer.id), ('parent_id', '=', False)] if buyer else [('id', '=', 0)]

        message_count = Message.search_count(domain)
        pager = portal_pager(url='/my/messages', total=message_count, page=page, step=PPG)
        messages = Message.search(domain, order='create_date desc', limit=PPG, offset=pager['offset'])

        values = self._prepare_portal_layout_values()
        values.update({
            'messages': messages, 'page_name': 'garment_portal_message',
            'pager': pager, 'default_url': '/my/messages', 'garment_buyer': buyer,
        })
        return request.render('garment_buyer_portal.portal_my_messages', values)

    @http.route(['/my/messages/new'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_message_new(self, subject=None, body=None, order_id=None, sample_id=None,
                            shipment_id=None, techpack_id=None, responsible_department=None, **kw):
        buyer = self._get_portal_buyer()
        if not buyer:
            return request.redirect('/my')
        vals = {
            'buyer_id': buyer.id,
            'partner_id': request.env.user.partner_id.id,
            'direction': 'inbound',
            'subject': subject,
            'body': body,
            'responsible_department': responsible_department or 'merchandising',
        }
        for fname, value in (('order_id', order_id), ('sample_id', sample_id),
                              ('shipment_id', shipment_id), ('techpack_id', techpack_id)):
            if value:
                vals[fname] = int(value)
        message = request.env['garment.portal.message'].sudo().create(vals)
        message.action_assign(vals['responsible_department'])
        self._log_activity('comment', _('Posted message %s') % message.name, 'garment.portal.message', message.id)
        return request.redirect('/my/messages')

    @http.route(['/my/messages/<int:message_id>/confirm'], type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def portal_message_confirm(self, message_id, **kw):
        message = self._document_check_access('garment.portal.message', message_id)
        message.action_buyer_confirm()
        self._log_activity('comment', _('Buyer confirmed response on %s') % message.name,
                            'garment.portal.message', message.id)
        return request.redirect('/my/messages')

    # ==================================================================
    # Public Buyer Registration (SRS sections 21-22) — no login required
    # ==================================================================
    @http.route(['/buyer-portal/register'], type='http', auth='public', website=True)
    def buyer_portal_register(self, **kw):
        return request.render('garment_buyer_portal.portal_access_request_form', {})

    @http.route(['/buyer-portal/register/submit'], type='http', auth='public', website=True,
                methods=['POST'], csrf=True)
    def buyer_portal_register_submit(self, **post):
        vals = {
            'source': 'manual',
            'company_name': post.get('company_name'),
            'brand_name': post.get('brand_name'),
            'website': post.get('website'),
            'business_category': post.get('business_category'),
            'contact_person': post.get('contact_person'),
            'email': post.get('email'),
            'phone': post.get('phone'),
            'requested_role': post.get('requested_role') or 'buyer_merchandiser',
            'department': post.get('department'),
        }
        request_rec = request.env['garment.portal.access.request'].sudo().create(vals)
        request_rec.sudo().action_submit()
        return request.render('garment_buyer_portal.portal_access_request_thanks', {'access_request': request_rec})
