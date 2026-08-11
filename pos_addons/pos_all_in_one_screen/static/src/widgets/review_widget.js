/** @odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

var globalSelf, myInterval, rate;
var src = window.location.pathname;
var config_id = src.replace(/[^0-9]/g, '');
const UPDATE_BUS_PRESENCE_DELAY = 60000;
import { browser } from "@web/core/browser/browser";
import { renderToString } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";
import ServicesMixin from "@web/legacy/js/core/service_mixins";
import { _t } from "@web/core/l10n/translation";
import { throttleForAnimation } from "@web/core/utils/timing";

publicWidget.registry.reviewWidget = publicWidget.Widget.extend(
	ServicesMixin,
	{
	selector: ".o_pos_review_management",
	events: {
		"click .cancel": "_closeReviewScreen",
		"click .submit-review": "_submitReview",
		"click .rating": "_onClickRating",
		"click .smiley-block": "_onClickSmiley",
	},
	/**
	 * @constructor
	 */
	init: function () {
		this._super.apply(this, arguments);
		this.added_channel_list = [];
		this.orm = this.bindService("orm");
	},
	/**
	 * @override
	 */
	start: async function () {
		var self = this;
		var res = await this._super(...arguments);
		globalSelf = self;
		self.is_websocket_connected = false;
		self.bus_service = self.__parentedParent.env.services.bus_service;
		await self.startpolling();
		await self.getConfigData(config_id);
		return res;
	},
	startpolling: function () {
		var self = this;
		const imStatusModelToIds = {};
		let updateBusPresenceTimeout;
		const LOCAL_STORAGE_PREFIX = "presence";
		let lastPresenceTime =
		browser.localStorage.getItem(`${LOCAL_STORAGE_PREFIX}.lastPresence`) || new Date().getTime();
		const throttledUpdateBusPresence = throttleForAnimation(
		function updateBusPresence() {
			clearTimeout(updateBusPresenceTimeout);
			const now = new Date().getTime();
			self.bus_service.send("update_presence", {
				inactivity_period: now - lastPresenceTime,
				im_status_ids_by_model: { ...imStatusModelToIds },
			});
			updateBusPresenceTimeout = browser.setTimeout(throttledUpdateBusPresence, UPDATE_BUS_PRESENCE_DELAY);
		}, UPDATE_BUS_PRESENCE_DELAY);
		browser.setTimeout(throttledUpdateBusPresence, 250);
		self.bus_service.addEventListener("notification", self._onNotification);
		self.add_channel(self.get_formatted_channel_name());
		self.bus_service.addEventListener("reconnect", throttledUpdateBusPresence);
		globalSelf = self;
	},
	get_formatted_channel_name: function (channel) {
		return "_wk_pos_screens_poll" + "_" + String(1);
	},
	add_channel: function (channel) {
		var self = this;
		if (self.added_channel_list.indexOf(channel) === -1) {
			self.bus_service.addChannel(channel);
			self.added_channel_list.push(channel);
		}
	},
	async getConfigData(){
		await this.orm.call('pos.screen.config', 'getConfigData', [config_id],
		).then(function (res) {
			if(res) {
				globalSelf.config = res['data'][0];
				globalSelf.status = res['status'];
				if(globalSelf.status){
					$('.loading-review-screen').hide();
					$('.welcome-screen').show();
				}
			}
		}).catch(function (error) {
			console.log("error", error);
		})
	},
	_onNotification: function (notifications) {
		notifications.detail.forEach(notification => {
			if (notification.type === "websocket_status") {
				globalSelf.is_websocket_connected = true;
			}
			if (notification.type === "new_pos_order") {
				var order = notification.payload[0];
				if(order['reload']) globalSelf._addReviewScreen(order);
				else{
					if(globalSelf.config.auto_review_screen_validate) globalSelf._addReviewScreen(order);
				}
			}
			if (notification.type === "new_order_status") globalSelf._closeReviewScreen();
		});
	},
	async _addReviewScreen(order){
		$('.loading-review-screen').hide();
		$('.welcome-screen').hide();
		$('.review-container').remove();

		var config = globalSelf.config;
		var title, content, customer, ratings;
		var image_convert_url = 'data:image/png;base64,';
		config.icons = image_convert_url + config.icons_smiley;
		config.blank = 'data:image/gif;base64,' + config.blank_gif;

		if(order['partner_id'] && order['partner_id'][0]) var customer = `<span class="partner" partner-id=${order['partner_id'][0]}>${order['partner_id'][1]}</span>`;
		else customer =  'Customer';

		if(config['title']) title = `<div style="margin: 10px 10px;">${config['title']}</div>`;
		else title = ''; 

		if(config['review_screen_content']) content = `<div style="margin: 10px 10px;">${config['review_screen_content']}</div>`;
		else content = ''; 

		if(config.banner) var src = image_convert_url + config.banner;

		if(config.type_of_icons == 'smiley'){
			var blank_url = config.blank;
			ratings = `
			<div id="smiley-container">
				<a class="smiley-block radio-option radio-option" rate="1" id="1" role="button" data-content="Very bad">
					<img src="${blank_url}" class="smiley"/>
				</a>
				<a class="smiley-block radio-option radio-option smiley_2" rate="2" id="2" role="button" data-content="Bad">
					<img src="${blank_url}" class="smiley"/>
				</a>
				<a class="smiley-block radio-option radio-option smiley_3" rate="3" id="3" role="button" data-content="Fair ">
					<img src="${blank_url}" class="smiley"/>
				</a>
				<a class="smiley-block radio-option radio-option smiley_4" rate="4" id="4" role="button" data-content="Good :)">
					<img src="${blank_url}" class="smiley"/>
				</a>
				<a class="smiley-block radio-option radio-option smiley_5" rate="5" id="5" role="button" data-content="Love It">
					<img src="${blank_url}" class="smiley"/>
				</a>
			</div>
			`;
		}else{
			ratings = `
				<div style="padding: 15px 0;">
					<i class="fa fa-star-o rating" aria-hidden="true" rate="1"></i>
					<i class="fa fa-star-o rating" aria-hidden="true" rate="2"></i>
					<i class="fa fa-star-o rating" aria-hidden="true" rate="3"></i>
					<i class="fa fa-star-o rating" aria-hidden="true" rate="4"></i>
					<i class="fa fa-star-o rating" aria-hidden="true" rate="5"></i>
				</div>
			`;
		}

		var code = `
		<div class='review-container' style='display:flex;'>
			<div class="left-pane" style="min-width:50%;">
				<img src=${src} style="width:100%; min-height:100%;"/>
			</div>
			<div class="right-pane" style="font-size: 20px; font-family: 'Inconsolata';min-width:50%;">
				<div style="font-size: 30px; background: aliceblue; font-weight: bold; text-align: center;">Review Screen</div>
				<div class="heading" style="margin: 10px 10px;">
					Hi ${customer}
				</div>
				${title}
				<div class="customer-body">
					<div style="margin: 10px 10px;">Shopping with ${order['config_id'][1]}</div>
					${content}
					${ratings}
					<textarea placeholder="Please Enter your feedback here(optional)" class="feedback"></textarea>
				</div>
				<div class="footer" style="margin: 10px 0; display: flex; justify-content: space-between;max-width: 100%;}">
					<span class="wk-button cancel">Cancel</span>
					<span class="wk-button submit-review" style="background: #a4ffa4;">Submit</span>
				</div>
			</div>
		</div>
		`
		$('.loading-review-screen').hide();
		$('.welcome-screen').hide();
		$('.o_pos_review_management').append(code);
		$('.review-container').attr('order-id', order.pos_reference);
		$('.smiley').css('background-image', `url(${config.icons})`);
		if(!config['is_show_content_box']) $('.feedback').remove();

		if(globalSelf.config.screen_reset_timeout){
			myInterval = setInterval(function() {
				globalSelf._closeReviewScreen();
			}, globalSelf.config.screen_reset_timeout * 1000);
		}
	},
	_onClickRating(ev){
		$('.rating').removeClass('active');
		$(ev.currentTarget).addClass('active');
		$(ev.currentTarget).prevAll().addClass('active');
		rate = $(ev.currentTarget).attr('rate');
	},
	_onClickSmiley(ev){
		$('.smiley-block').removeClass('active');
		$(ev.currentTarget).addClass('active');
		rate = $(ev.currentTarget).attr('rate');
	},
	_submitReview(ev){
		var rating = $('.rating.active').length || $('.smiley-block').attr('rate');
		if(!rating) swal("Dear Customer, Please Select a rating first!!!");
		else{
			var data = {
				'rating' : rate,
				'feedback' : $('.feedback').val(),
				'order_id' : $('.review-container').attr('order-id'),
				'partner_id' : $('.partner').attr('partner-id') || false,
				'screen_session_id' : globalSelf.config.current_session_id[0],
			}

			this.orm.call('pos.screen.config', 'review_screen', [], data
			).then(function (res) {
				swal("Success!", "Order is Successfully Done!", "success");
				setTimeout(function () {
					globalSelf._closeReviewScreen();
				}, 5000);
			}).catch(function (error) {
				console.log("error", error);
			})
		}
	},
	_closeReviewScreen(){
		$('.rating').removeClass('active');
		$('.feedback').val('');
		$('.review-container').remove();
		if(!globalSelf.status) $('.loading-review-screen').show();
		else $('.welcome-screen').show();
		clearInterval(myInterval);
	},
});