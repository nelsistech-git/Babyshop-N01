# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 12: Logistics & Shipment Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Logistics & Shipment Management System',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Shipment planning, container/freight/forwarder management, transportation and B/L',
    'description': """
Smart Complete Garment Software — Logistics & Shipment Management System
=============================================================================
Module 12 of the Smart Complete Garment Software suite — the last piece
of the Supply Chain phase before Finance.

Key Features
------------
* Shipment Master (Sea/Air/Road/Courier) with the full Planning ->
  Allocation -> Booking -> Loading -> Port -> Vessel Departed -> In
  Transit -> Delivered lifecycle
* Shipment Allocation (style/PO/quantity/carton/warehouse location)
* Container Management with the 8-stage tracking status (Booked -> Empty
  Picked -> Factory Loading -> Loaded -> Port Arrival -> Vessel Departed
  -> Destination Port -> Delivered)
* Freight Cost Management (ocean freight/local transport/port charges/
  documentation/handling/insurance) with forwarder quotation comparison
* Freight Forwarder and Shipping Line management with performance rating
* Transportation Management: Vehicle, Driver, and Trip (folding in
  Transport Request and GPS tracking fields) covering Factory -> Port
  movement
* Bill of Lading and Shipment Document management with expiry alerts
* AI Logistics Optimization: shipment delay prediction, freight cost
  prediction, route optimization, forwarder recommendation from cost/
  performance comparison, and container utilization analysis — extends
  the shared Garment AI Engine
* Port Management master data (Chittagong Port/Mongla Port/Dhaka ICD)
  with Port Delivery Tracking on the transport trip
* Carrier Performance KPIs (damage rate, response time, rating grade)
  and Freight Cost / Container Monitoring / Shipment Status dashboards
* Logistics Alert System (Shipment Delay / Document Missing) via a daily
  scheduled action, and Container Booking / Delivery Completion
  automation with buyer notifications
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'garment_buyer_crm', 'garment_style_library', 'garment_merchandising',
                'garment_warehouse'],
    'data': [
        'security/garment_logistics_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_logistics_data.xml',
        'data/ir_cron_data.xml',
        'views/garment_shipment_views.xml',
        'views/garment_container_views.xml',
        'views/garment_freight_views.xml',
        'views/garment_forwarder_views.xml',
        'views/garment_shipping_line_views.xml',
        'views/garment_port_views.xml',
        'views/garment_vehicle_driver_views.xml',
        'views/garment_transport_trip_views.xml',
        'views/garment_bill_lading_views.xml',
        'views/garment_shipment_document_views.xml',
        'report/garment_shipment_report.xml',
        'views/garment_logistics_dashboard_views.xml',
        'views/garment_logistics_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
