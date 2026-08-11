# -*- coding: utf-8 -*-
{
    "name": "POS Thermal Receipt - Multi Branch & Auto Sync",
    "version": "17.0.1.0.0",
    "category": "Point of Sale",
    "summary": "80mm/58mm thermal receipt with dynamic multi-branch headers, "
                "branch invoice numbering and barcode, built on POS's native "
                "offline-first sync engine.",
    "description": """
POS Thermal Receipt (Multi-Branch & Auto-Sync)
================================================
* Dynamic branch header pulled from res.company (name, address, phone, BIN/VAT)
* Branch invoice numbering, e.g. UTT/POS/2026/08/0145
* Itemized breakdown: qty, unit price, line total, subtotal, VAT, total payable
* Split payment lines, change due, cashier & customer
* Code128 barcode of the order reference for lookup/return validation
* Strict 80mm / 58mm print CSS (monospace, zero margins, dynamic scaling)
* Relies on POS's built-in IndexedDB offline queue + bus/websocket live
  updates for branch metadata and pricing - no data loss on reconnect.
""",
    "author": "Custom Development",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/res_company_views.xml",
        "views/pos_config_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "baby_shop_pos_receipt/static/src/js/order_receipt.js",
            "baby_shop_pos_receipt/static/src/xml/order_receipt.xml",
            "baby_shop_pos_receipt/static/src/scss/receipt.scss",
        ],
    },
    "installable": True,
    "application": False,
}
