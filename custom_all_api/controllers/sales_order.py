import logging

from odoo.tools.translate import _
from odoo import http
from odoo.http import request
import pytz
from odoo import SUPERUSER_ID

_logger = logging.getLogger(__name__)


class Order(http.Controller):
    # -------- Primary sale create
    @http.route('/api/v1/primary_sale/create', type='json', auth="public", methods=['POST'], csrf=False)
    def primary_sale_create(self, **kw):
        # http://localhost:8069/api/v1/primary_sale/create
        """
            {"jsonrpc": "2.0", "params":{"user_email":"{{emp_email}}",
            "access_token":"{{access_token}",
            "customer_mobile":{{customer_mobile}},
            "shop_id":{{shop_id}},
            "product_list":[{"product_barcode":1482,"qty":2,"price":2},
                            {"product_barcode":1557,"qty":1,"price":2}]
             }}
            #if dealer then pass mobile as email
            Returns:
                {
                "jsonrpc": "2.0",
                "id": null,
                "result": {
                    "status": 200,
                    "response": [
                        {
                            "id": 84,
                            "order_no": "S00035"
                        }
                    ],
                    "message": "Success"
                }
            }
            """

        if request.httprequest.method == 'POST':
            emp_obj = request.env['hr.employee'].sudo()
            partner_obj = request.env['res.partner'].sudo()

            access_token = kw.get('access_token')

            customer_name = kw.get('customer_name')
            customer_mobile = kw.get('customer_mobile')

            product_list = kw.get('product_list')

            # --------------------
            user_id = None
            company_id = 1
            super_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
            if super_user:
                user_id = super_user.id
                company_id = super_user.company_id.id or 1

            # --------------- E-com branch/company based on is_ecom_branch flag diye search korte hobe
            # company_id = 1

            partner_id = None
            customer_obj = partner_obj.search([('mobile', '=', customer_mobile)], limit=1)

            if customer_obj:
                partner_id = customer_obj.id
            else:
                # কাস্টমার না পেলে নতুন কাস্টমার তৈরি করার লজিক
                new_customer = partner_obj.create({
                    'name': customer_name if customer_name else 'Unknown Customer',
                    'mobile': customer_mobile,
                })
                partner_id = new_customer.id

            if access_token == '12345':
                sale_order_obj = request.env['sale.order'].sudo()
                sale_order_line_obj = request.env['sale.order.line'].sudo()
                product_obj = request.env['product.product'].sudo()

                # loc_obj = request.env['stock.location'].sudo().search([('id', '=', shop_id)], limit=1)
                # if loc_obj:
                #     shop_id = loc_obj.id
                # else:
                #     shop_id = None

                vals = {
                    'company_id': company_id,
                    'partner_id': partner_id,
                    'is_ecom_sale': True,
                    'user_id': user_id if user_id else False

                }

                order = sale_order_obj.create(vals)

                for product in product_list:
                    prod = product_obj.search([('barcode', '=', product.get('product_barcode'))], limit=1)

                    # যদি প্রোডাক্ট খুঁজে পাওয়া যায়, তবেই অর্ডার লাইন তৈরি হবে
                    if prod:
                        sale_order_line_obj.create({
                            'order_id': order.id,
                            'name': prod.name,
                            'product_id': prod.id,
                            'product_uom_qty': product.get('qty'),
                            'price_unit': product.get('price'),
                            'company_id': order.company_id.id,
                        })

                data = {
                    'status': 200,
                    'response': [
                        {
                            "id": order.id,
                            'order_no': order.name if order.name else None
                        }
                    ],
                    'message': 'Success'
                }
            else:
                data = {
                    'status': 401,
                    'response': ['Unauthorized'],
                    'message': 'Unauthorized'
                }
        else:
            data = {
                'status': 405,
                'response': ['Method Not Allowed'],
                'message': 'Method Not Allowed'
            }

        return data
