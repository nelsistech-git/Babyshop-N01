
from odoo import models, api, fields,_
import logging
import requests
from datetime import timedelta
from odoo.fields import Datetime

_logger = logging.getLogger(__name__)

class InheritPosOrder(models.Model):
    _inherit = 'pos.order'

    def send_sms(self, phone, message):
        """Send SMS using Shishu Poribohon SMS Gateway."""
        api_url = "http://bulksmsbd.net/api/smsapi"
        api_key = "IeHxV9QcIyQWt1H8lcMY"
        sender_id = "8809617623225"
        _logger.info('dhukse')
        #print('dhukse')
        #print(phone)
        payload = {
            "api_key": api_key,
            "type": "text",
            "number": phone,
            "senderid": sender_id,
            "message": message,
        }

        try:
            response = requests.post(api_url, data=payload,timeout=15)
            if response.status_code == 200:
                # result = response.json()
                try:
                    result = response.json()
                except ValueError:
                    _logger.error(response.text)
                    return False

                if result.get("status") == "SUCCESS":
                    return True
                else:
                    _logger.error("SMS failed: %s", result.get("error_message", "Unknown error"))
            else:
                _logger.error("SMS request failed with status code: %s", response.status_code)
        except Exception as e:
            _logger.exception("Error sending SMS: %s", e)

        return False

    def action_pos_order_paid(self):
        """Override the validate action to send SMS after order is validated."""
        res = super(InheritPosOrder, self).action_pos_order_paid()

        #return res
        # sms send off for few times

        _logger.info('dhukse1')

        for order in self:
            # customer_phone = order.partner_id.phone
            customer_phone = order.partner_id.mobile or order.partner_id.phone

            if customer_phone:
                # Generate the correct POS receipt link

                # order_time = (order.date_order + timedelta(hours=6)).strftime("%I:%M%p")  # Format as 06:54PM
                # order_date = order.date_order.strftime("%d-%m-%Y")  # Format as 11-11-2024

                local_dt = Datetime.context_timestamp(self, order.date_order)
                order_time = local_dt.strftime("%I:%M %p")
                order_date = local_dt.strftime("%d-%m-%Y")

                message = _(
                    f"(Shishu Poribohon) Thanks for shopping at Shishu Poribohon Bashundhara City at {order_time} on {order_date}. "
                    f"Total Paid: {order.amount_total:.2f}, Invoice No: {order.pos_reference}")

                sms_sent = self.send_sms(customer_phone, message)
                if sms_sent:
                    _logger.info("SMS sent successfully to %s", customer_phone)
                else:
                    _logger.warning("Failed to send SMS to %s", customer_phone)

        return res
