# -*- coding: utf-8 -*-
"""Link the validated bonded receipts to the LC shipments, mark the shipments received
and close the fully received LC."""


def run(ctx):
    links = [('a1', 'a', 'a1'), ('a2', 'a', 'a2'), ('b1', 'b', 'b1'), ('c1', 'c', 'c1'), ('c2', 'c', 'c1')]

    def link():
        for receipt_key, lc_key, shp_key in links:
            receipt = ctx.need('receipt_' + receipt_key)
            picking = receipt.picking_id.sudo()
            picking.write({'lc_id': ctx.need('lc_' + lc_key).id,
                           'lc_shipment_id': ctx.need('shp_' + shp_key).id})

    def receive():
        for shp_key in ('a1', 'a2', 'b1', 'c1'):
            shipment = ctx.u(ctx.need('shp_' + shp_key), 'lc_officer')
            if shipment.state == 'customs_cleared':
                shipment.action_receive()

    def close_lc_a():
        lc = ctx.u(ctx.need('lc_a'), 'lc_manager')
        lc.action_close()

    ctx.step('lclink.link_receipts', link)
    ctx.step('lclink.receive_shipments', receive)
    ctx.step('lclink.close_lc_a', close_lc_a)
