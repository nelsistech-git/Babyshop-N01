# -*- coding: utf-8 -*-
from markupsafe import escape

from odoo import http
from odoo.http import request


class CsatController(http.Controller):

    @http.route('/omni/csat/<string:token>', type='http', auth='public', methods=['GET'], csrf=False)
    def csat_form(self, token, **kwargs):
        record = self._find_by_token(token)
        if not record:
            return request.make_response(
                self._page('This survey link is invalid or has expired.'),
                headers=[('Content-Type', 'text/html')])
        if record.customer_rating:
            return request.make_response(
                self._page('You already submitted your feedback. Thank you!'),
                headers=[('Content-Type', 'text/html')])
        return request.make_response(self._form(token), headers=[('Content-Type', 'text/html')])

    @http.route('/omni/csat/<string:token>/submit', type='http', auth='public', methods=['POST'], csrf=False)
    def csat_submit(self, token, **kwargs):
        record = self._find_by_token(token)
        if not record:
            return request.make_response(
                self._page('This survey link is invalid or has expired.'),
                headers=[('Content-Type', 'text/html')])
        rating = kwargs.get('rating')
        feedback = kwargs.get('feedback')
        if rating in ('1', '2', '3', '4', '5'):
            record.sudo().action_submit_csat(int(rating), feedback)
            return request.make_response(
                self._page('Thank you for your feedback!'),
                headers=[('Content-Type', 'text/html')])
        return request.make_response(self._form(token, error=True), headers=[('Content-Type', 'text/html')])

    # =====================================================================
    # HELPERS
    # =====================================================================
    def _find_by_token(self, token):
        Session = request.env['crm.chat.session'].sudo()
        rec = Session.search([('csat_token', '=', token)], limit=1)
        if rec:
            return rec
        Call = request.env['crm.call.log'].sudo()
        rec = Call.search([('csat_token', '=', token)], limit=1)
        if rec:
            return rec
        return None

    def _page(self, message):
        return """<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>Feedback</title>%s</head>
<body><div class="omni-csat-wrap"><h2>%s</h2></div></body></html>""" % (self._style(), escape(message))

    def _form(self, token, error=False):
        error_html = '<p style="color:#c0392b;">Please choose a rating before submitting.</p>' if error else ''
        return """<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>Rate your experience</title>%s</head>
<body>
<div class="omni-csat-wrap">
<h2>How was your experience?</h2>
%s
<form method="post" action="/omni/csat/%s/submit">
<div class="omni-stars">
<label><input type="radio" name="rating" value="5"/>5</label>
<label><input type="radio" name="rating" value="4"/>4</label>
<label><input type="radio" name="rating" value="3"/>3</label>
<label><input type="radio" name="rating" value="2"/>2</label>
<label><input type="radio" name="rating" value="1"/>1</label>
</div>
<textarea name="feedback" placeholder="Any additional comments? (optional)"></textarea><br/>
<button type="submit">Submit</button>
</form>
</div>
</body></html>""" % (self._style(), error_html, escape(token))

    def _style(self):
        return """<style>
body{font-family:Arial,Helvetica,sans-serif;background:#f7f7f7;margin:0;}
.omni-csat-wrap{max-width:480px;margin:60px auto;background:#fff;padding:32px;
  border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.1);text-align:center;}
.omni-stars label{font-size:28px;color:#ccc;margin:0 6px;cursor:pointer;}
.omni-stars input{display:none;}
.omni-stars label:hover, .omni-stars label:hover ~ label{color:#f5a623;}
textarea{width:100%;height:80px;margin-top:16px;box-sizing:border-box;
  font-family:inherit;padding:8px;}
button{margin-top:16px;padding:10px 28px;background:#4a4a4a;color:#fff;
  border:none;border-radius:4px;cursor:pointer;font-size:14px;}
button:hover{background:#333;}
</style>"""
