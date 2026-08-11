/** @odoo-module */
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { Order } from "@point_of_sale/app/store/models";
import { renderToString } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";

patch(TicketScreen.prototype, {
	_setOrder(order) {
		super._setOrder(order);
		var cart_screen = this.pos.db.cart_screen;
		if(this && cart_screen && cart_screen.show_cart_type == 'auto') this.pos.send_data_to_cart(cart_screen);
	}
});

patch(ProductScreen.prototype, {
	_setValue(val) {
		super._setValue(val);
		if (this.currentOrder.get_selected_orderline()) {
			var screen_data = this.pos.db.cart_screen;
			if(screen_data && screen_data.show_cart_type == 'auto') this.pos.send_data_to_cart(screen_data);
		}
	}
});

patch(PaymentScreen.prototype, {
	send_data_to_cart_screen(){
		var self = this;
		self.pos.send_data_to_cart(self.pos.db.cart_screen);
	}
});

patch(ReceiptScreen.prototype, {
	onMounted(){
		var self = this;
		var cart_screen = this.pos.db.cart_screen;

		if(cart_screen && cart_screen.show_cart_type == 'auto'){
			this.pos.send_data_to_cart(cart_screen);
		} else {
			$('.button.cart_data').on('click',function(el){
				self.pos.send_data_to_cart(cart_screen);
			});
		}
	},
	get get_screen_data(){
		return this.pos.db.pos_screen_data;
	},
});

patch(Navbar.prototype, {
	setup(){
		super.setup();
        this.orm = useService("orm");
	},
	closeSession(){
		var self = this;
		var data = {
			'html' : '',
			'status' : false,
			'pos_status' : this.pos.config.has_active_session,
		}
		self.orm.call('pos.screen.config', 'update_cart_screen', [data]
		).then(function (result) {
			SuperHeaderButton.call(self);
		}).catch(function (error) {
			console.log("error", error);
		});
		SuperHeaderButton.call(self);
	}
});

patch(PosStore.prototype, {
	add_new_order(){
		var self = this;
		var res = super.add_new_order();
		var screen_data = this.db.cart_screen;
		if(screen_data){
			var data = {
				'html' : '',
				'status' : false,
				'pos_status' : self.config.has_active_session,
			}
			self.env.services.orm.call('pos.screen.config', 'update_cart_screen', [data]
			).then(function (result) {
			}).catch(function (error) {
				console.log("error", error);
			});
		}
		return res;
	},
	removeOrder(order){
		var self = this;
		super.removeOrder(order);
		if(self.get_order()){
			var orderlines = self.get_order().get_orderlines();
			try{
				if(orderlines && Object.keys(orderlines).length > 0){
					if(self && self.db.cart_screen) self.send_data_to_cart(self.db.cart_screen);
				} else {
					var data = {
						'html' : '',
						'status' : false,
						'pos_status' : this.config.has_active_session,
					}
					self.env.services.orm.call('pos.screen.config', 'update_cart_screen', [data]
					).then(function (result) {
					}).catch(function (error) {
						console.log("error", error);
					});
				}
			}
			catch(err){
				console.log("***************Exception*********",err)
			}
		}
	},
	convert_path_to_image_base64(path, data) {
		return new Promise(function (resolve, reject) {
			var xhr = new XMLHttpRequest();
			xhr.onload = function() {
				var reader = new FileReader();
				reader.onloadend = function() {
					data.image_code = reader.result;
					resolve();
				}
				reader.readAsDataURL(xhr.response);
			};
			xhr.open('GET', path);
			xhr.responseType = 'blob';
			xhr.send();
		});
	},
	get_product_image_path(product){
		return window.location.origin + '/web/image?model=product.product&field=image_128&id=' + product.id;
	},
	getting_orderline_data(){
		var self = this;
		var orderlines_data = { 'orderlines':{}, 'total_amount':0, 'total_tax':0 };
		var image_promises = [];
		var screen_data = this.db.cart_screen;
		var current_order= this.get_order();
		var orderlines = current_order.get_orderlines();
		var data_dict = {};
		orderlines.forEach(orderline => {
			var product = orderline.product;
			var path = self.get_product_image_path(product);
			var price = self.env.utils.formatCurrency(orderline.get_display_price());
			data_dict[orderline.id] = {
				'product_name':product.display_name,
				'quantity':orderline.quantityStr,
				'price':price,
				'path':path
			}
		});
		orderlines_data['orderlines'] = data_dict;
		if(screen_data && screen_data.show_product_image){
			Object.values(data_dict).forEach(line => {
				image_promises.push(self.convert_path_to_image_base64(line.path,line));
			});
			return Promise.all(image_promises).then(function() {
				return orderlines_data
			});
		} else return orderlines_data;
	},
	async send_data_to_cart(screen){
		var self = this;
		var config = this.config;
		var current_order = this.get_order();
		var screen_data = screen;
		var order = this.get_order();
		var orderline_html = '';
		var welcome_html = this.db.welcome_html;
		var paymentlines = [];

		if(current_order.is_paid() && current_order.get_paymentlines() && current_order.get_paymentlines().length){
			current_order.get_paymentlines().forEach(paymentline => {
				paymentlines.push(paymentline.export_for_printing());
			});
		}

		var items_count = 0;
		current_order.get_orderlines().forEach(orderline => {
			items_count += orderline.quantity;
		});

		var data = await self.getting_orderline_data()
		var orderlines_data = data;
		orderlines_data['items_count'] = items_count;
		orderlines_data['paymentlines'] = paymentlines;
		orderlines_data['order'] = current_order;
		orderlines_data['pos_name'] = self.config.name;
		orderlines_data['show_product_image'] = screen_data.show_product_image;
		const sum = Object.values(data.orderlines).reduce((accumulator, line) => accumulator + parseFloat(line.quantity), 0);

		if (order) {
			orderline_html = await renderToString('CustomerCartScreen', {
				'orderlines': Object.values(data.orderlines).reverse(),
				'orderlines_details':orderlines_data,
				'paymentlines': Object.values(paymentlines),
				'widget':self.chrome,
				'env':self.env,
				'sum' : sum,
			});
			var data = {
				'html' : orderline_html,
				'status' : true,
				'pos_status' : self.config.has_active_session,
			}

			await self.env.services.orm.call('pos.screen.config', 'update_cart_screen', [data],
			).then(function (result) {
			}).catch(function (error) {
				console.log("error", error);
			});
		}
	}
});

patch(Order.prototype, {
	add_product(product, options){
		var cart_screen = this.pos.db.cart_screen;
		var res = super.add_product(product, options);
		if(this.pos && cart_screen && cart_screen.show_cart_type == 'auto') this.pos.send_data_to_cart(cart_screen);
		return res;
	}
});