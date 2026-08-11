/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";
import {Component, useState, onWillStart, onMounted, onWillUnmount, useRef} from "@odoo/owl";
import {ExpressPosPaymentDialog} from "./express_pos_payment_dialog";
import {ExpressPosQuickCustomerDialog} from "./express_pos_quick_customer_dialog";
import {ExpressPosReturnDialog} from "./express_pos_return_dialog";

export class ExpressPosConsole extends Component {
    static template = "express_retail_pos.ExpressPosConsole";

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.barcodeInputRef = useRef("barcodeInput");
        this.searchInputRef = useRef("searchInput");

        this.state = useState({
            order: {
                order_id: false, name: "", partner_id: false, partner_name: "",
                branch_id: false, branch_name: "",
                amount_total: 0, amount_untaxed: 0, amount_tax: 0, lines: [],
            },
            products: [],
            categories: [],
            activeCategoryId: false,
            searchQuery: "",
            barcodeValue: "",
            parkedOrders: [],
            showParkedOrders: false,
            session: {
                journals: [], walkin_partner_id: false, currency_symbol: "",
                block_on_negative_stock: false, branches: [], cashier_name: "", company_name: "",
            },
            kpis: {today_sales: 0, today_orders: 0, held_orders: 0, avg_basket: 0},
            loading: false,
            loyalty: {card_id: false, points: 0, mobile_verified: false},
            clock: "",
        });

        this._searchTimeout = null;

        onWillStart(async () => {
            await this._loadSession();
            await this._loadOrder(false);
            await this._loadProducts("");
            await this._loadKpis();
        });

        onMounted(() => {
            this._onKeydown = (ev) => this._handleGlobalKeydown(ev);
            window.addEventListener("keydown", this._onKeydown);
            if (this.barcodeInputRef.el) {
                this.barcodeInputRef.el.focus();
            }
            this._tickClock();
            this._clockInterval = setInterval(() => this._tickClock(), 30000);
            this._kpiInterval = setInterval(() => this._loadKpis(), 60000);
        });

        onWillUnmount(() => {
            window.removeEventListener("keydown", this._onKeydown);
            clearInterval(this._clockInterval);
            clearInterval(this._kpiInterval);
        });
    }

    _tickClock() {
        this.state.clock = new Date().toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
    }

    // ------------------------------------------------------------------
    // Loaders
    // ------------------------------------------------------------------
    async _loadSession() {
        const data = await this.orm.call("sale.order", "express_pos_get_session_data", []);
        Object.assign(this.state.session, data);
        this.state.categories = data.categories || [];
    }

    async _loadOrder(orderId, branchId) {
        const data = await this.orm.call("sale.order", "express_pos_get_or_create_draft", [
            orderId || false, branchId || false,
        ]);
        Object.assign(this.state.order, data);
    }

    async _loadProducts(query) {
        const products = await this.orm.call("sale.order", "express_pos_search_products", [
            query, 60, this.state.activeCategoryId || false,
        ]);
        this.state.products = products;
    }

    async _loadParkedOrders() {
        const orders = await this.orm.call("sale.order", "express_pos_get_parked_orders", []);
        this.state.parkedOrders = orders;
    }

    async _loadKpis() {
        try {
            const kpis = await this.orm.call("sale.order", "express_pos_get_dashboard_kpis", [
                this.state.order.branch_id || false,
            ]);
            Object.assign(this.state.kpis, kpis);
        } catch (error) {
            // KPI ribbon is a nice-to-have; never block the console on it.
        }
    }

    // ------------------------------------------------------------------
    // Branch / Category switching
    // ------------------------------------------------------------------
    get currentBranchColor() {
        const branch = this.state.session.branches.find((b) => b.id === this.state.order.branch_id);
        return (branch && branch.color) || "#1f5c3d";
    }

    async switchBranch(ev) {
        const branchId = parseInt(ev.target.value);
        if (!branchId) return;
        if (this.state.order.lines.length) {
            const ok = window.confirm("Switching branch will hold the current cart. Continue?");
            if (!ok) return;
            await this.holdCart();
        }
        await this._loadOrder(false, branchId);
        await this._loadKpis();
    }

    async selectCategory(categoryId) {
        this.state.activeCategoryId = this.state.activeCategoryId === categoryId ? false : categoryId;
        await this._loadProducts(this.state.searchQuery);
    }

    // ------------------------------------------------------------------
    // Product search & barcode
    // ------------------------------------------------------------------
    onSearchInput(ev) {
        const value = ev.target.value;
        this.state.searchQuery = value;
        clearTimeout(this._searchTimeout);
        this._searchTimeout = setTimeout(() => this._loadProducts(value), 250);
    }

    onBarcodeInput(ev) {
        // As the scanner types (or the cashier types manually), live-filter
        // the product grid so the matching product is visible right away —
        // not just after pressing Enter. Kept independent of the separate
        // search box's state so the two fields don't visibly overwrite
        // each other.
        const value = ev.target.value;
        clearTimeout(this._barcodeSearchTimeout);
        this._barcodeSearchTimeout = setTimeout(() => this._loadProducts(value), 150);
    }

    async onBarcodeKeydown(ev) {
        if (ev.key !== "Enter") return;
        clearTimeout(this._barcodeSearchTimeout);
        const barcode = ev.target.value.trim();
        if (!barcode) return;
        const result = await this.orm.call("sale.order", "express_pos_scan_barcode", [barcode]);
        if (!result.found) {
            // Not an exact barcode match — fall back to a normal search so
            // the cashier still sees any product matching that text/code.
            this.notification.add(`No exact barcode match for "${barcode}" — showing search results.`, {type: "warning"});
            await this._loadProducts(barcode);
            return;
        }
        await this.addProduct(result.id);
        ev.target.value = "";
        this.state.barcodeValue = "";
        await this._loadProducts(this.state.searchQuery);
    }

    async addProduct(productId) {
        if (!this.state.order.order_id) {
            await this._loadOrder(false);
        }
        const data = await this.orm.call("sale.order", "express_pos_add_product", [
            this.state.order.order_id, productId, 1.0, "add",
        ]);
        const warning = data.stock_warning;
        delete data.stock_warning;
        Object.assign(this.state.order, data);
        if (warning) {
            this.notification.add("Warning: Insufficient Stock!", {type: "danger"});
        }
    }

    async updateLineQty(line, qty) {
        qty = parseFloat(qty);
        if (isNaN(qty)) return;
        const data = await this.orm.call("sale.order", "express_pos_add_product", [
            this.state.order.order_id, line.product_id, qty, "set",
        ]);
        delete data.stock_warning;
        Object.assign(this.state.order, data);
    }

    async incrementLine(line, delta) {
        await this.updateLineQty(line, Math.max(0, line.product_uom_qty + delta));
    }

    async removeLine(line) {
        const data = await this.orm.call("sale.order", "express_pos_remove_line", [
            this.state.order.order_id, line.id,
        ]);
        Object.assign(this.state.order, data);
    }

    // ------------------------------------------------------------------
    // Customer
    // ------------------------------------------------------------------
    openQuickCustomerDialog() {
        this.dialog.add(ExpressPosQuickCustomerDialog, {
            onConfirm: async (name, mobile) => {
                const partner = await this.orm.call("sale.order", "express_pos_quick_create_customer", [name, mobile]);
                const data = await this.orm.call("sale.order", "express_pos_set_customer", [
                    this.state.order.order_id, partner.id,
                ]);
                Object.assign(this.state.order, data);
            },
        });
    }

    // ------------------------------------------------------------------
    // Hold / Park
    // ------------------------------------------------------------------
    async holdCart() {
        if (!this.state.order.order_id || !this.state.order.lines.length) {
            this.notification.add("Cart is empty, nothing to hold.", {type: "warning"});
            return;
        }
        await this.orm.call("sale.order", "action_express_hold", [[this.state.order.order_id]]);
        this.notification.add(`Order ${this.state.order.name} held.`, {type: "success"});
        await this._loadOrder(false);
        await this._loadKpis();
    }

    async toggleParkedOrders() {
        this.state.showParkedOrders = !this.state.showParkedOrders;
        if (this.state.showParkedOrders) {
            await this._loadParkedOrders();
        }
    }

    async resumeParkedOrder(orderId) {
        await this._loadOrder(orderId);
        this.state.showParkedOrders = false;
    }

    // ------------------------------------------------------------------
    // Loyalty / Offers
    // ------------------------------------------------------------------
    async applyOffers() {
        if (!this.state.order.lines.length) {
            this.notification.add("Cart is empty, nothing to discount.", {type: "warning"});
            return;
        }
        const data = await this.orm.call("sale.order", "express_pos_apply_offers", [this.state.order.order_id]);
        Object.assign(this.state.order, data);
        this.notification.add("Offers applied to the cart.", {type: "success"});
    }

    async lookupLoyaltyCard(ev) {
        if (ev.key !== "Enter") return;
        const code = ev.target.value.trim();
        if (!code) return;
        try {
            const data = await this.orm.call("sale.order", "express_pos_set_loyalty_card", [
                this.state.order.order_id, code,
            ]);
            Object.assign(this.state.loyalty, {
                card_id: data.card_id,
                points: data.points,
                mobile_verified: data.mobile_verified
            });
            this.notification.add(`Loyalty card linked. Current points: ${data.points}`, {type: "success"});
        } catch (error) {
            this.notification.add(error.data ? error.data.message : String(error), {type: "danger"});
        }
    }

    // ------------------------------------------------------------------
    // Payment / Checkout
    // ------------------------------------------------------------------
    openPaymentDialog() {
        if (!this.state.order.lines.length) {
            this.notification.add("Cannot checkout an empty cart.", {type: "warning"});
            return;
        }
        this.dialog.add(ExpressPosPaymentDialog, {
            amountDue: this.state.order.amount_total,
            journals: this.state.session.journals,
            currencySymbol: this.state.session.currency_symbol,
            isWalkin: this.state.order.partner_id === this.state.session.walkin_partner_id,
            onConfirm: async (paymentLines, giftCardLines, allowDue) => {
                await this._checkout(paymentLines, giftCardLines, allowDue);
            },
        });
    }

    async _checkout(paymentLines, giftCardLines, allowDue) {
        this.state.loading = true;
        try {
            const result = await this.orm.call("sale.order", "express_pos_checkout", [
                this.state.order.order_id, paymentLines, giftCardLines || [], allowDue || false,
            ]);
            let msg = `Order ${this.state.order.name} completed. Invoice ${result.invoice_names.join(", ")}`;
            if (result.loyalty_points_earned) {
                msg += ` — ${result.loyalty_points_earned.toFixed(2)} points earned.`;
            }
            if (result.amount_due_remaining) {
                msg += ` — ${result.amount_due_remaining.toFixed(2)} left as due/credit.`;
            }
            this.notification.add(msg, {type: "success"});
            this._printReceipt(result.order_id);
            await this._loadOrder(false);
            await this._loadKpis();
            this.state.loyalty = {card_id: false, points: 0, mobile_verified: false};
        } catch (error) {
            this.notification.add(error.data ? error.data.message : String(error), {type: "danger"});
        } finally {
            this.state.loading = false;
        }
    }

    _printReceipt(orderId) {
        const url = `/report/pdf/express_retail_pos.action_report_express_pos_receipt/${orderId}`;
        const printWindow = window.open(url, "_blank");
        if (printWindow) {
            printWindow.addEventListener("load", () => {
                try {
                    printWindow.print();
                } catch (e) {
                    // Some browsers block scripted print on cross-origin PDF viewers; ignore silently.
                }
            });
        }
    }

    // ------------------------------------------------------------------
    // Return / Exchange
    // ------------------------------------------------------------------
    openReturnDialog() {
        this.dialog.add(ExpressPosReturnDialog, {
            onDone: (message) => {
                this.notification.add(message, {type: "success"});
                this._loadKpis();
            },
        });
    }

    // ------------------------------------------------------------------
    // Keyboard shortcuts
    // ------------------------------------------------------------------
    _handleGlobalKeydown(ev) {
        const tag = (ev.target.tagName || "").toLowerCase();
        const isTyping = tag === "input" || tag === "textarea";

        if (ev.key === "F2") {
            ev.preventDefault();
            if (this.searchInputRef.el) this.searchInputRef.el.focus();
        } else if (ev.key === "F4") {
            ev.preventDefault();
            this._promptDiscount();
        } else if (ev.code === "Space" && !isTyping) {
            ev.preventDefault();
            this.openPaymentDialog();
        }
    }

    async _promptDiscount() {
        if (!this.state.order.lines.length) return;
        const lastLine = this.state.order.lines[this.state.order.lines.length - 1];
        const value = window.prompt(`Discount % for "${lastLine.name}":`, lastLine.discount || 0);
        if (value === null) return;
        const discount = parseFloat(value);
        if (isNaN(discount)) return;
        await this.orm.write("sale.order.line", [lastLine.id], {discount});
        await this._loadOrder(this.state.order.order_id);
    }

    get formattedTotal() {
        return this.state.order.amount_total.toFixed(2);
    }
}

registry.category("actions").add("express_pos_console", ExpressPosConsole);