from datetime import datetime, timedelta
import random
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class CommonApi(http.Controller):
    @http.route('/api/v4/get_time', type='json', auth="none", methods=['POST'], csrf=False)
    def get_srv_datetime(self, **kw):
        #http://localhost:8069/api/v4/get_time
        """
        {"jsonrpc": "2.0", "params":{}}

        Returns:
            {
                "jsonrpc": "2.0",
                "id": null,
                "result": {
                    "status": 200,
                    "response": "2024-09-02 14:32:37",
                    "message": "Success"
                }
            }
        """
        dt_time = datetime.now() + timedelta(hours=6)  # .strftime('%Y-%m-%d %H:%M:%S')
        data = {
                    'status': 200,
                    'response': dt_time,
                    'message': 'Success'
                }

        return data

