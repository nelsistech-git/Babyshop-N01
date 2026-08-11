/** @odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

var globalSelf;
var src = window.location.pathname;
var config_id = src.replace(/[^0-9]/g, '');
const UPDATE_BUS_PRESENCE_DELAY = 60000;
import { browser } from "@web/core/browser/browser";
import { renderToString } from "@web/core/utils/render";
import { throttleForAnimation } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";
import ServicesMixin from "@web/legacy/js/core/service_mixins";

publicWidget.registry.cartWidget = publicWidget.Widget.extend(
	ServicesMixin,
	{
	selector: ".o_pos_cart_management",
	events: {},
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
		await self._beforeLoading();
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
	_onNotification: function (notifications) {
		notifications.detail.forEach(notification => {
			if (notification.type === "websocket_status") globalSelf.is_websocket_connected = true;
			if (notification.type === "update_cart_screen") {
				if(!notification.payload.status) globalSelf.clearCartScreen(notification.payload);
				else globalSelf.addCartScreen(notification.payload);
			}
		});
	},
	async _beforeLoading(){
		await this.orm.call('pos.screen.config', 'get_cart_screen_data', [parseInt(config_id)]
		).then(function (res) {
			globalSelf.clearCartScreen(res);
		}).catch(function (error) {
			console.log("error", error);
		});
	},
	clearCartScreen: function(res){
		if(res.pos_status){
			$('.container-fluid').remove();
			$('.loading-review-screen').hide();
			$('.welcome-screen').show();
		}else {
			$('.container-fluid').remove();
			$('.loading-review-screen').hide();
			$('.welcome-screen').hide();
		}
	},
	addCartScreen : function(res){
		$('.loading-review-screen').hide();
		$('.welcome-screen').hide();
		if($('.container-fluid').length) $('.container-fluid').html(res.html);
		else $('.o_pos_cart_management').append(res.html);
	}
});