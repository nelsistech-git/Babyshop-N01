/** @odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

var globalSelf;
var src = window.location.pathname;
var config_id = src.replace(/[^0-9]/g, '');
const UPDATE_BUS_PRESENCE_DELAY = 60000;
var filter= '';
var avg_duration = 0;
import { browser } from "@web/core/browser/browser";
import { renderToString } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";
import ServicesMixin from "@web/legacy/js/core/service_mixins";
import { _t } from "@web/core/l10n/translation";
import { throttleForAnimation } from "@web/core/utils/timing";

publicWidget.registry.kitchenWidget = publicWidget.Widget.extend(
	ServicesMixin,
	{
	selector: ".o_pos_kitchen_management",
	events: {
		"click body": "_OnclickSelector",
		"click .wk-details": "_OnclickViewDetails",
		"click .bell,.bell-notification": "_OnclickBellButton",
		"click .list-hover": "_OnclickListHoverButton",
		"click .wk-next": "_OnclickListWkNext",
		"click .grid-view": "_OnclickChefHatButton",
		"click .wk-back": "_OnclickChefHatButton",
		"click .process-order .dropdown-item": "_onDropdownItemClick",
		"click .close-notif-bar":"_onCloseNotifBarClick",
		"click .product-category": "_onToggleCategProducts",
		"click .view-order": "_viewOrder",
		"click .accept": "_acceptOrder",
		"click .proceed-order": "_proceedOrder",
		"click .view-detail": "_viewOrderDetail",
		"click .decline": "_declineOrder",
		"click .cancel": "_closePopup",
		"click .order-done": "_doneOrder",
		"click .cancel-order": "_cancelOrder",
		"click .orderline-done": "_doneOrderLine",
		"input input.search-orders": "_searchOrders",
		"click .status-update": "_updateKitchenScreen",
		"click .picked-up": "_orderPickedUp",
		"click .fullscreen": "_onToggleFullScreen",
		"click .toggle-sidebar": "_ontoggleSideBar",
		"click .close-sidebar": "_onCloseSideBar",

		"click .toggle-search": "_toggleSearchbar",
		"click .chef-hat" : "_onHomeClick",
		"click .filter-fresh": "_filterFreshOrders",
		"click .filter-done": "_filterDoneOrders",
		"click .filter-pending": "_filterPendingOrders",
		"click .filter-alert": "_filterAlertOrders",
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
		self.kitchen_orders_by_id = {};
		self.products = {};
		self.config;
		self.lines = {};
		self.is_websocket_connected = false;
		self.max_duration = {'duration' : 0, 'date' : ''};
		self.bus_service = self.__parentedParent.env.services.bus_service;
		await self.startpolling();
		await self._fetch_kitchen_order_data();
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
	async _beforeLoading(){
		if(globalSelf.config){
			if(!globalSelf.config['has_active_session']){
				$('.wk-loader').hide();
				$('.loading-content').text('No active Session for Kitchen Screen, Please start the Session!!!')
			}else{
				var orders = $('.kitchen-order');
				$('.loading-review-screen').hide();
				$('.container').show();
				$('.sidebar').hide();
				var notifications = $('.notification');
				if(notifications.length) $('.notify').show();
				if(orders.length > 0) $('.chef').hide();
				else $('.kitchen-order-list').hide();
				await globalSelf._setPendingTime();
				$('.order-time').hide();
				globalSelf._noProductsMessage();
				$('.fa-toggle-on').hide();

				if(globalSelf.config.accepted_order_color){
					$('.filter-fresh').css({color : globalSelf.config.accepted_order_color})
				}
				if(globalSelf.config.pending_order_color){
					$('.filter-pending').css({color : globalSelf.config.pending_order_color})
				}

				Object.values(orders).forEach(order => {
					var id = $(order).attr('order-id');
					var data = globalSelf.kitchen_orders_by_id[id];
					if(data){
						if(data.order_progress === 'accepted' && globalSelf.config.accepted_order_color) $(order).find('.order-header').css({background : globalSelf.config.accepted_order_color,})
						if(['pending', 'partially_done'].includes(data.order_progress) && globalSelf.config.pending_order_color) $(order).find('.order-header').css({background : globalSelf.config.pending_order_color,})
					}
				});
				setInterval(function() {
					globalSelf._fetch_kitchen_order_data();
					globalSelf._setPendingTime();
					globalSelf._updateKitchenScreen();
				}, 60 * 1000);
			}
		}
	},
	_onNotification: function (notifications) {
		notifications.detail.forEach(notification => {
			if (notification.type === "websocket_status") {
				globalSelf.is_websocket_connected = true;
			}
			if (notification.type === "close_kitchen_session") {
				$('.container').remove();
				$('.notification-bar').remove();
				$('.loading-review-screen').show();
				$('.wk-loader').hide();
				$('.loading-content').text('The Current Kitchen Session is now Closed!!!')
			}
			if (notification.type === "pos_kitchen_data_update") {
				globalSelf.is_websocket_connected = true;
				var data = notification.payload;
				if(data) {
					if(data.screen_id){
						if(data.screen_id.data == config_id){
							var order = data.orders.data[0];
							if(order) {
								globalSelf.kitchen_orders_by_id[order.id] = order;
								if(order.order_progress !== 'new'){
									globalSelf._addNewOrder(data.create, order);
								} else globalSelf.addNotification(order);
							}
						}
					}
				}
			}
		});
	},
	_onToggleCategProducts(ev){
		$(ev.currentTarget).next().toggle();
	},
	_onCloseNotifBarClick(ev){
		$('.notification-bar').hide();
		globalSelf._backgroundfocus();
	},
	_OnclickBellButton(event) {
		event.stopPropagation();
		globalSelf._backgroundBlur();
		$('.notification-bar').show();
	},
	_OnclickSelector(ev){
		// $('.swal-modal').remove();
		$('.notification-bar').hide();
	},
	async _onToggleFullScreen(ev){
		const el = document.body;
		const fullScreenElement = document.webkitFullscreenElement || document.fullscreenElement;
		try {
			if(!fullScreenElement){
				if (el.requestFullscreen) await el.requestFullscreen();
				else if (el.mozRequestFullScreen) await el.mozRequestFullScreen();
				else if (el.webkitRequestFullscreen) await el.webkitRequestFullscreen();
			}
			else{
				if (document.exitFullscreen) await document.exitFullscreen();
				else if (document.mozCancelFullScreen) await document.mozCancelFullScreen();
				else if (document.webkitCancelFullScreen) await document.webkitCancelFullScreen();
			}
		} catch (err) {
			console.log('err', err)
		}
	},
	_searchOrders(ev){
		var lines = [];
		var orders = $('.kitchen-order');
		var products = $('.product-details');
		var search = $(ev.currentTarget).val().toLowerCase();
		if(search){
			orders.hide();
			$('.order-line').removeClass('highlight');
			products.hide();
			if(products.length){
				products.each(product => {
					if(product){
						var id = $(product).attr('product-id');
						if(id){
							var data = globalSelf.products[id];
							if(data){
								var product_name = data.name;
								product_name = product_name.toLowerCase();
								if(product_name.indexOf(search) != -1){
									$(`.product-details[product-id=${id}]`).show();
									lines = $(`.order-line[product-id=${id}]`);
								}
							}
						}
					}
				});
			}
			lines.forEach(line => {
				$(line).addClass('highlight');
				$(line).parents('.kitchen-order').show();
			});

			// search by token no
			orders.each((i, order) => {
				var id = $(order).attr('order-id');
				var data = globalSelf.kitchen_orders_by_id[id];
				var order_ref = data.kitchen_order_name;
				if(order_ref.indexOf(search) != -1){
					$(`.kitchen-order[order-id=${id}]`).show();
				}
			});
		} else{
			orders.show();
			$('.order-line').removeClass('highlight');
			products.show();
		}
	},
	_fetch_kitchen_order_data: async function () {
		await this.orm.call('pos.kitchen.order', 'get_queue_orders_data', [[], parseInt(config_id)]
		).then(function (res) {
			globalSelf.kitchen_orders_by_id = {};
			globalSelf.products = res['products'];
			globalSelf.config = res['config'];
			globalSelf.pending_orders = res['pending_orders'];
			globalSelf.orders_last_hour = res['orders_last_hour'];
			globalSelf.orders_last_15_min = res['orders_last_15_min'];
			if(res['orders']){
				res['orders'].forEach(order => {
					globalSelf.kitchen_orders_by_id[order.id] = order;
				});
			}
			if(res['lines']){
				res['lines'].forEach(line => {
					globalSelf.lines[line.id] = line;
				});
			}
		}).catch(function (error) {
			console.log("error", error);
		})
	},
	addNotification(order){
		var html = `
		<div class="notification" order-id=${order.id}>
			<div class="status">
				<i class="fa fa-circle" style="color:green"></i>
			</div>
			<div style="padding-left:4%; width:100%;">
				<div class="notif-detail">
					<span class=""> ${order.kitchen_order_name} </span>
					<span class="order-time"> ${order.order_date} </span>
				</div>
				<div class="notif-body">
					Total ${order.lines.length} Products in this Order.
				</div>
				<div class="view-order">
					View
				</div>
			</div>
		</div>`
		var ele = $(`.notification[order-id=${order.id}]`);

		if(!ele.length){
			$('.notifications').prepend(html);
			order = globalSelf.kitchen_orders_by_id[order.id];
		} else ele.replaceWith(html);

		$('.notify').show();
	},
	_viewOrder(ev){
		var id = $(ev.currentTarget).closest('.notification').attr('order-id');
		if(id) var order = globalSelf.kitchen_orders_by_id[id];
		if(order){
			$('.notification-bar').hide();
			var order_html = renderToString('ViewKitchenOrder', { order: order });
			$('.o_pos_kitchen_management').append(order_html);
		}
	},
	_acceptOrder(ev){
		var element = $('.new-order');
		var id = element.attr('order-id');
		if (id) var order = globalSelf.kitchen_orders_by_id[id];
		if(order){
			globalSelf._processOrder(id, 'accept', '');
			$('.chef').hide();
			globalSelf._closePopup();
			$(`.notification[order-id=${id}]`).remove();
			if(!$('.notification').length) $('.notify').hide();
			
			if(globalSelf.config.accepted_order_color) {
				$(`.kitchen-order[order-id=${id}]`).find('.order-header').css({background : globalSelf.config.accepted_order_color});
			}
		}
	},
	_addNewOrder(create, order){
		var type = order['order_type'];
		type = type === 'takeaway' ? 'Takeaway' : 'Dining';
		var member = '';
		
		var exists = $(`.kitchen-order[order-id=${order.id}]`).length;
		globalSelf.kitchen_orders_by_id[order.id].lines_count = 0;

		if(order['order_date']){
			let res = globalSelf._calculateTime(order['order_date']);

			if(typeof res === 'object') res = res.duration;
			var time = `
				<span class="order-time" style="display:none">${order['order_date']}</span>
				<span class="pending-time">${res}</span>
			`
		}
		if(order['members']) member = `
			<span>
				<i class="fa fa-users" aria-hidden="true"></i>
				<span>${order['members']}</span>
			</span>
		`

		var html = `
			<div class="kitchen-order" order-id="${order['id']}">
				<div class="order-header">
					${member}
					<span class="token"> ${order['kitchen_order_name']} </span>
					<span class="time">
						<i class="fa fa-clock-o" aria-hidden="true"></i>  ${time}
					</span>
				</div>

				<div class="order-status"> ${type} </div>

				<div class="order-body"></div>

				<div class="order-footer">
					<span class="wk-button proceed-order">Start</span>
					<span class="wk-button button order-done" style="display:none;">Done</span>
					<span class="wk-button button view-detail">View Details</span>
					<span class="wk-button picked-up done-button" style="display:none;">Picked Up</span>
				</div>
			</div>
		`
		$('.kitchen-order-list').show();
		$('.chef').hide();

		if(create && !exists) $('.kitchen-order-list').prepend(html);	
		if(!create && !exists && order.order_progress === 'accepted') $('.kitchen-order-list').prepend(html);	
		else $(`.kitchen-order[order-id=${order.id}]`).replaceWith(html);

		order.lines.forEach(line => {
			if(line){
				globalSelf.lines[line.id] = line;
				if(line.state !== 'done') globalSelf.kitchen_orders_by_id[order.id].lines_count += 1; 
				var discount = line.discount;
				var qty_added = line.qty_added;
				var qty_removed = line.qty_removed;
				var product_id = line.product_id[0];
				var categ = line.pos_categ_ids;
	
				discount = (discount && discount > 0) ? `${discount}%` : '';
	
				var addQty =  qty_added ? `
					<span class="qty-added" style="color:green;">
					[+ ${qty_added} ]
					</span>
				` : '';
				var removeQty = qty_removed ? `
					<span class="qty-added" style="color:red;">
					[- ${qty_removed}]
					</span>
				`: '';
	
				var note = line.note ? `<div style="word-wrap: break-word; font-style: italic; color: #868686;"> ${line.note} </div>` : '';
	
				var line_html = `
					<div class="order-line" line-id=${line.id}>
						<span style="color:green"> ${line.qty} </span> x
						<span>${line.product_id[1]}</span>
						<span style="color:green">${discount}</span>
						${addQty}
						${removeQty}
						<i class="done-line fa fa-check" style="display:none;"></i>
						${note}
					</div>
				`;
	
				$(`.kitchen-order[order-id=${line['order_id'][0]}]`).find('.order-body').append(line_html);
				if(line.state === 'done') $(`.order-line[line-id=${line.id}]`).find('.done-line').show();
	
				var product_line = $(`.product-details[product-id=${product_id}]`);
	
				if(line.qty){
					if(!product_line.length) {
						if(line.state !== 'done') globalSelf.addProductDetail(categ, product_id, line.product_id[1], line.qty);
					}
					else{
						if(!exists) globalSelf.updateProductValue(product_id, 'add', line.qty);
						if(line.qty_added) globalSelf.updateProductValue(product_id, 'add', line.qty_added);
						if(line.qty_removed) globalSelf.updateProductValue(product_id, 'remove', line.qty_removed);
					}
				}
			}
		});

		if(order['order_progress'] === 'accepted' && globalSelf.config.accepted_order_color) $(`.kitchen-order[order-id=${order.id}]`).find('.order-header').css({background : globalSelf.config.accepted_order_color});

		if(['pending', 'partially_done'].includes(order['order_progress'])){
			$(`.kitchen-order[order-id=${order.id}]`).find('.proceed-order').hide();
			$(`.kitchen-order[order-id=${order.id}]`).find('.order-done').show();
			if(globalSelf.config.pending_order_color) $(`.kitchen-order[order-id=${order.id}]`).find('.order-header').css({background : globalSelf.config.pending_order_color});
			else $(`.kitchen-order[order-id=${order.id}]`).find('.order-header').css({background : '#fda400'});
		}
	},
	_declineOrder(ev){
		var element = $('.new-order');
		var id = element.attr('order-id');
		if (id) var order = globalSelf.kitchen_orders_by_id[id];
		if(order){
			element.remove();
			globalSelf._backgroundBlur();
			var order_html = renderToString('declineOrder', { order: order });
			$('.o_pos_kitchen_management').append(order_html);
		}
	},
	_cancelOrder(ev){
		var element = $('.decline-order');
		var id = element.attr('order-id');
		var reason = $('#cancel_reason').val();
		globalSelf._processOrder(id, 'cancel', reason);
		$(`.notification[order-id=${id}]`).remove();
		if(!$('.notification').length) $('.notify').hide();
		globalSelf._closePopup();
		swal("Success!", "Order Successfully Cancelled!", "success");
	},
	_viewOrderDetail(ev){
		var id = $(ev.currentTarget).parents('.kitchen-order').attr('order-id');
		if(id) var order = globalSelf.kitchen_orders_by_id[id];
		if(order){
			globalSelf._backgroundBlur();
			var order_html = renderToString('viewOrderDetail', { order: order });
			$('.o_pos_kitchen_management').append(order_html);
		}
	},
	_doneOrder(ev){
		var is_detail_done = $(ev.currentTarget).attr('name');
		if(is_detail_done) var element = $(ev.currentTarget).parents('.order-detail');
		else element = $(ev.currentTarget).parents('.kitchen-order');
		var id = element.attr('order-id');

		globalSelf._processOrder(id, 'done', '');
		globalSelf.kitchen_orders_by_id[id]['order_progress'] = 'done';
		globalSelf._doneStatus(id);
		globalSelf._closePopup();
		swal("Success!", "Order is Successfully Done!", "success");
	},
	async _doneOrderLine(ev){
		var element = $(ev.currentTarget).parents('.order-line');
		var line_id = element.attr('line-id');
		var order_id = $(ev.currentTarget).parents('.order-detail').attr('order-id');
		var order =  globalSelf.kitchen_orders_by_id[order_id];
		var is_order_done = order.lines_count === 1;
		
		await this.orm.call('pos.kitchen.orderline', 'write', [[parseInt(line_id)], { 
			is_orderline_done: true, state: 'done' 
		}]).then(function (res) {
			$(ev.currentTarget).remove();
			element.append(`<i class="done-line fa fa-check"></i>`);
			var line = globalSelf.lines[line_id];
			var qty = 0;
			if(line.qty) qty += line.qty;
			if(line['qty_added']) qty += line['qty_added'];
			if(line['qty_removed']) qty -= line['qty_removed'];
			globalSelf.updateProductValue(line['product_id'][0], 'remove', qty);
		}).catch(function (error) {
			console.log("error", error);
		});

		if(is_order_done) var state = 'done';
		else state = 'partially_done';

		this.orm.call('pos.kitchen.order', 'write', [[parseInt(order_id)], { 
			order_progress: state, is_state_updated: true
		}]).then(function (res) {
			if(is_order_done){
				var order_line = $(`.kitchen-order[order-id=${order_id}]`).find(`.order-line[line-id=${line_id}]`);
				order_line.find('.done-line').show();
				globalSelf.kitchen_orders_by_id[order_id]['order_progress'] = 'done';
				globalSelf._doneStatus(order_id);
				globalSelf._closePopup();
			}
		}).catch(function (error) {
			console.log("error", error);
		});
	},
	_orderPickedUp(ev){
		var order = $(ev.currentTarget).parents('.kitchen-order');
		var id = order.attr('order-id');
		globalSelf._processOrder(id, 'picked_up', '');
		order.remove();
		globalSelf._checkOrders();
	},
	_processOrder(id, status, reason){
		this.orm.call('pos.kitchen.order', 'process_order', [config_id, parseInt(id), status, reason],
		).then(function (res) {
		}).catch(function (error) {
			console.log("error", error);
		})
	},
	_proceedOrder(ev){
		var is_detail_start = $(ev.currentTarget).attr('name');
		if(is_detail_start) var element = $(ev.currentTarget).parents('.order-detail');
		else element = $(ev.currentTarget).parents('.kitchen-order');
		var id = element.attr('order-id');
		element.find('.proceed-order').hide();
		element.find('.order-done').show();
		globalSelf._closePopup();
		globalSelf._processOrder(id, 'pending', '');
	},
	_doneStatus(id){
		var order = $(`.kitchen-order[order-id=${id}]`);
		order.find('.order-header').css({background : '#21a321'});
		order.find('.order-body').find('.done-line').show();

		var lines = order.find('.order-body').find('.order-line');
		lines.each(line => {
			var id = $(line).attr('line-id');
			var line = globalSelf.lines[id];
			if(line) globalSelf.updateProductValue(line['product_id'][0], 'remove', line.qty);
		});

		order.find('.order-done').hide();
		order.find('.view-detail').hide();
		if(!order.find('.done-button').length){
			var html = `
				<span class="wk-button picked-up done-button">Picked Up</span>
			`
			order.find('.order-footer').append(html);
		}else order.find('.done-button').show();

		globalSelf._checkOrders();
		order = globalSelf.kitchen_orders_by_id[id];

		if(!order.order_type) $(`.kitchen-order[order-id=${id}]`).remove();
	},
	_setPendingTime(){
		var times = $('.order-time');
		var orders = $('.kitchen-order');

		if(times.length){
			avg_duration = 0;
			times.each((i, time) => {
				var orderId = $()
				var pending = globalSelf._calculateTime($(time).text());
				if(pending.alert) {
					$(time).closest('.kitchen-order').attr('alert', true);
					if(globalSelf.config.threshold_order_color){
						$(time).closest('.order-header').css({
							background : globalSelf.config.threshold_order_color,
						});
					}
				}

				if(pending === 'now') {
					$(time).parents('.time').find('span.pending-time').text('now');
				}else $(time).parents('.time').find('span.pending-time').text(pending.duration);
			});
			$('.max-pending').text(globalSelf.getTimeFromNow(globalSelf.max_duration.date));
		}else $('.max-pending').text(0);

		if(avg_duration){
			var avg_date = new Date();
			avg_duration /= times.length * 3600;
			avg_date.setHours((avg_date.getHours() -  avg_duration)/orders.length);
			$('.average-pending').text(globalSelf.getTimeFromNow(avg_date));
		}else $('.average-pending').text(0);
	},
	_calculateTime(s) {
		var date = new Date();
		var alert = false;
		const now = new Date();
		s = s.split(':');
		date.setHours(s[0], s[1], s[2]);
		var diffInMs = now - date;
		var diffInSeconds = Math.floor(diffInMs / 1000);
		var diffInMinutes = Math.floor(diffInSeconds / 60);
		var diffInHours = Math.floor(diffInMinutes / 60);
	  
		var min = diffInMinutes % 60;
	  
		if (min > globalSelf.config.threshold_time) alert = true;
	  
		avg_duration += (min + diffInHours * 60) * 60;
	  
		if (globalSelf.max_duration.duration === 0) {
			globalSelf.max_duration.duration = diffInSeconds;
			globalSelf.max_duration.date = date;
		} else if (globalSelf.max_duration.duration < diffInSeconds) {
			globalSelf.max_duration.duration = diffInSeconds;
			globalSelf.max_duration.date = date;
		}
		if ((now - date) / 1000 < 45) return "now";
		return {
			'alert': alert,
			'duration': globalSelf.getTimeFromNow(date),
		};
	},
	_toggleSearchbar(){
		$('.search-orders').toggle('slow', 'swing');
		$('.filter').toggle();
		filter = '';
		$('.kitchen-order').show();
	},
	_onHomeClick(){
		$('.filter').toggle();
		filter = '';
		$('.kitchen-order').show();
	},
	_filterFreshOrders(){
		var orders = $('.kitchen-order');
		if(filter === '') orders.hide();

		if(filter === 'new'){
			filter = '';
			return;
		}else filter = 'new';

		if(filter === 'new'){
			orders.each((i, order) => {
				var id = $(order).attr('order-id');
				var data = globalSelf.kitchen_orders_by_id[id];
				if(data && data.order_progress === 'accepted') $(order).toggle();
				filter = 'buffer';
			});
		}
	},
	_filterDoneOrders(){
		var orders = $('.kitchen-order');
		if(filter === '') orders.hide();
		if(filter === 'done'){
			filter = '';
			return;
		}else filter = 'done';
		if(filter === 'done'){
			orders.each((i, order) => {
				var id = $(order).attr('order-id');
				var data = globalSelf.kitchen_orders_by_id[id];
				if(data && data.order_progress === 'done') $(order).toggle();
			});
			filter = 'buffer';
		}
	},
	_filterPendingOrders(){
		var orders = $('.kitchen-order');
		if(filter === '') orders.hide();
		if(filter === 'pending'){
			filter = '';
			return;
		}else filter = 'pending';
		if(filter === 'pending'){
			orders.each((i, order) => {
				var id = $(order).attr('order-id');
				var data = globalSelf.kitchen_orders_by_id[id];
				if(data && ['pending', 'partially_done'].includes(data.order_progress)) $(order).toggle();
			});
			filter = 'buffer';
		}
	},
	_filterAlertOrders(){
		var orders = $('.kitchen-order');
		if(filter === '') orders.hide();
		if(filter === 'alert'){
			filter = '';
			return;
		}else filter = 'alert';
		if(filter === 'alert'){
			orders.each((i, order) => {
				if($(order).attr('alert')) $(order).toggle();
			});
			filter = 'buffer';
		}
	},
	_closePopup(ev){
		$('.wk-popup').remove();
		globalSelf._backgroundfocus();
	},
	_backgroundBlur(){
		$('.overlay').addClass('blur')
		$('.container').addClass('disabled');
	},
	_backgroundfocus(){
		$('.overlay').removeClass('blur')
		$('.container').removeClass('disabled');
	},
	_noProductsMessage(){
		var categs = $('.categ-products');
		categs.each(categ => {
			if(!$(categ).children().length){
				var html = `
					<div class='product-details' product-id='' style='font-style: italic; justify-content: center;'>
						product not available for prepare
					</div>
				`
				// $(categ).append(html);
			}
		});
	},
	addProductDetail(categ, id, name, qty){
		var categ = $(`.categ-products[categ-id=${categ}]`);
		if(categ){
			var html = `
				<div class="product-details" product-id=${id}>
					<span class="product-name">${name}</span>
					<span class="product-quantity">${qty}</span>
				</div>
			`
			categ.append(html);
			var remove_lines = categ.find(`.product-details[product-id='']`);
			remove_lines.remove();
		}
	},
	updateProductValue(id, status, qty){
		var product = $(`.product-details[product-id=${id}]`);
		if(product.length){
			var ele_qty = parseInt(product.find('.product-quantity').text());

			if(status === 'add'){
				qty += ele_qty;
				product.find('.product-quantity').text(qty);
			}
			else {
				qty = ele_qty - parseInt(qty);
				if(!qty) product.remove();
				else product.find('.product-quantity').text(qty);
			}
		}
	},
	_updateKitchenScreen(){
		globalSelf._fetch_kitchen_order_data();
		globalSelf._setPendingTime();
		if(globalSelf.pending_orders) $('.pending-orders').text(globalSelf.pending_orders);
		if(globalSelf.order_last_hour) $('.order-last-hour').text(globalSelf.order_last_hour);
		if(globalSelf.orders_last_15_min) $('.order-last-15-min').text(globalSelf.orders_last_15_min);
		globalSelf._checkOrders();
	},
	_checkOrders(){
		var orders = $('.kitchen-order');
		if(orders.length < 1){
			$('.kitchen-order-list').hide();
			$('.chef').show();
		}
		else{
			$('.kitchen-order-list').show();
			$('.chef').hide();
		}
	},
	_ontoggleSideBar(ev){
		$('.sidebar').toggle('slow', 'linear');
		$('.fa-toggle-off').toggle();
		$('.fa-toggle-on').toggle();
	},
	getTimeFromNow(date) {
		const currentDate = new Date(date);
		const diffInMs =  new Date() - currentDate;
		const diffInMinutes = Math.floor(diffInMs / (1000 * 60));
		const diffInHours = Math.floor(diffInMinutes / 60);
		
		if(diffInMinutes < 2) return 'now';
		else if (diffInHours < 1) return `${diffInMinutes} minutes`;
		else return `${diffInHours} hours`;
	}
});