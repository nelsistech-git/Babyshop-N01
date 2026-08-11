from odoo import fields, models, api, tools


class MinimumStockList(models.Model):
    """ List View of Minimum Stock """
    _name = 'minimum.stock.list'
    _description = 'Minimum Stock List'
    _auto = False

    product_id = fields.Many2one('product.product', string="Product", required=True)
    on_hand_stock = fields.Float(string='On Hand Qty.')
    minimum_stock = fields.Float(string='Minimum Qty.', store=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'minimum_stock_list')
        self._cr.execute("""
            CREATE OR REPLACE VIEW minimum_stock_list AS (
                SELECT
                    row_number() OVER () as id,product_id, COALESCE(SUM(on_hand_stock), 0) AS on_hand_stock, COALESCE(SUM(minimum_stock), 0) AS minimum_stock
                FROM(
                    SELECT tbl1.product_id, COALESCE(SUM(tbl2.on_hand_stock), 0) AS on_hand_stock, COALESCE(SUM(tbl1.minimum_stock), 0) AS minimum_stock
                    FROM (
                        SELECT pp.id AS product_id,
                        COALESCE(SUM(pt.minimum_stock_qty), 0) AS minimum_stock
                        FROM
                            product_product AS pp
                        JOIN
                            product_template AS pt ON pt.id = pp.product_tmpl_id
                        WHERE pt.minimum_stock_qty > 0
                        GROUP BY pp.id 
                    ) tbl1
                    LEFT JOIN (
                        SELECT
                            stq.product_id, COALESCE(SUM(stq.quantity), 0) AS on_hand_stock
                        FROM
                            stock_quant stq
                        JOIN
                            stock_location stl ON stl.id = stq.location_id
                        WHERE
                            stl.usage = 'internal' AND stl.state='done'
                        GROUP BY
                            stq.product_id						
                    ) tbl2 ON tbl2.product_id = tbl1.product_id
                    WHERE tbl1.minimum_stock > 0
                    GROUP BY tbl1.product_id
                ) AS main_tbl
                GROUP BY product_id
                ORDER BY product_id
            )
        """)

    @api.model
    def action_generate_minimum_stock_list_report(self):
        """ Action Method """
        tools.drop_view_if_exists(self._cr, 'minimum_stock_list')
        self._cr.execute("""
            CREATE OR REPLACE VIEW minimum_stock_list AS (
                SELECT
                    row_number() OVER () as id,product_id, COALESCE(SUM(on_hand_stock), 0) AS on_hand_stock, COALESCE(SUM(minimum_stock), 0) AS minimum_stock
                FROM(
                    SELECT tbl1.product_id, COALESCE(SUM(tbl2.on_hand_stock), 0) AS on_hand_stock, COALESCE(SUM(tbl1.minimum_stock), 0) AS minimum_stock
                    FROM (
                        SELECT pp.id AS product_id,
                        COALESCE(SUM(pt.minimum_stock_qty), 0) AS minimum_stock
                        FROM
                            product_product AS pp
                        JOIN
                            product_template AS pt ON pt.id = pp.product_tmpl_id
                        WHERE pt.minimum_stock_qty > 0
                        GROUP BY pp.id 
                    ) tbl1
                    LEFT JOIN (
                        SELECT
                            stq.product_id, COALESCE(SUM(stq.quantity), 0) AS on_hand_stock
                        FROM
                            stock_quant stq
                        JOIN
                            stock_location stl ON stl.id = stq.location_id
                        WHERE
                            stl.usage = 'internal' AND stl.state='done'
                        GROUP BY
                            stq.product_id						
                    ) tbl2 ON tbl2.product_id = tbl1.product_id
                    WHERE tbl1.minimum_stock > 0
                    GROUP BY tbl1.product_id
                ) AS main_tbl
                GROUP BY product_id
                ORDER BY product_id
            )
        """)

        IrModelData = self.env['ir.model.data']
        tree_view_id = tree_view_id = IrModelData._xmlid_to_res_id('custom_stock.view_minimum_stock_list_tree')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Minimum Stock List',
            'view_mode': 'tree',
            'res_model': 'minimum.stock.list',
            'views': [(tree_view_id, 'tree')],
            # 'context': {'search_default_group_by_product_id': 1, 'search_default_group_by_location_id': 1},
            'target': 'current'
        }

    def old_action_generate_minimum_stock_list_report(self):
        """ Action Method """
        tools.drop_view_if_exists(self._cr, 'minimum_stock_list')
        self._cr.execute("""
            CREATE OR REPLACE VIEW minimum_stock_list AS (
                SELECT
                    row_number() OVER () as id,product_id, COALESCE(SUM(on_hand_stock), 0) AS on_hand_stock, COALESCE(SUM(minimum_stock), 0) AS minimum_stock
                FROM(
                    SELECT tbl1.product_id, COALESCE(SUM(tbl1.on_hand_stock), 0) AS on_hand_stock, COALESCE(SUM(tbl2.minimum_stock), 0) AS minimum_stock
                    FROM (
                        SELECT
                            stq.product_id, COALESCE(SUM(stq.quantity), 0) AS on_hand_stock
                        FROM
                            stock_quant stq
                        LEFT JOIN
                            stock_location stl ON stl.id = stq.location_id
                        WHERE
                            stl.usage = 'internal' AND stl.state='done'
                        GROUP BY
                            stq.product_id
                    ) tbl1
                    LEFT JOIN (
                        SELECT 
                        pp.id AS product_id,
                        COALESCE(SUM(pt.minimum_stock_qty), 0) AS minimum_stock
                        FROM
                            product_product AS pp
                        LEFT JOIN
                            product_template AS pt ON pt.id = pp.product_tmpl_id
                        GROUP BY pp.id
                    ) tbl2 ON tbl2.product_id = tbl1.product_id
                    WHERE tbl2.minimum_stock > 0
                    GROUP BY tbl1.product_id
                ) AS main_tbl
                GROUP BY product_id
                ORDER BY product_id
            )
        """)

        IrModelData = self.env['ir.model.data']
        tree_view_id = IrModelData.xmlid_to_res_id('custom_stock.view_minimum_stock_list_tree')
        actionObject = IrModelData.xmlid_to_object('custom_stock.action_minimum_stock_list')

        action = actionObject.sudo().read(
            ['name', 'help', 'res_model', 'target', 'domain', 'search_view_id'])
        if not action:
            action = {}
        else:
            action = action[0]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Minimum Stock List',
            'view_mode': 'tree',
            'res_model': 'minimum.stock.list',
            'views': [(tree_view_id, 'tree')],
            # 'context': {'search_default_group_by_product_id': 1, 'search_default_group_by_location_id': 1},
            'target': 'current'
        }
