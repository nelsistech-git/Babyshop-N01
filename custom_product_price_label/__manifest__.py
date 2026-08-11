{
    "name": "Custom Product Price Label (1.5in x 1in)",
    "version": "17.0.1.0.0",
    "summary": "Print a compact 1.5in x 1in barcode price label for product variants",
    "description": """
Custom Product Price Label
===========================
Adds a "Custom Product Label" option to the Print menu of Product Variants.

The label (1.5 inch wide x 1 inch high) shows:
- Product name + Internal Reference
- Variant attribute value(s) (e.g. Size)
- Barcode (Code128)
- Sales Price (BDT) - inclusive VAT

Select one or more variants from the Product Variants list, then
Print > Custom Product Label.
""",
    "category": "Inventory/Inventory",
    "author": "Nelsis Tech Limited",
    "license": "LGPL-3",
    "depends": ["product", "stock"],
    "data": [
        "report/report_paperformat.xml",
        "report/product_label_report.xml",
        "report/product_label_template.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
