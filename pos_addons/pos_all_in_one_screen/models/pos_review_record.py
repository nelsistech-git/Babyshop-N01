# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################
from odoo import fields, models

class PosReviewRecord(models.Model):
	_name = 'pos.review.record'
	_order = 'id desc'
	_description = "Review Records"

	name = fields.Many2one('pos.order',string="POS Order")
	review_rating = fields.Selection([('0','Zero'),('1','One Star'),('2','Two Stars'),('3','Three Stars'),('4','Four Stars'),('5','Five Stars')], string="Review Ratings")
	review_content = fields.Text(string="Review")
	customer = fields.Many2one('res.partner',string="Customer")
	salesperson = fields.Many2one('res.users', string="Sales Person")
	screen_session_id = fields.Many2one('pos.screen.session', string='Session', domain="[('state', '=', 'opened')]", states={'draft': [('readonly', False)]}, readonly=True)
