/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class AppCollectionManager extends Component {
    static template = "app_collection.AppCollectionManager";
    static components = { DropdownItem };
    static props = {
        apps: { type: Array },
    };

    setup() {
        this.collectionSvc = useService("app_collection");
        this.state = useState({
            activeCollection: null, // null = All Apps
            dragOverCollection: null,
            draggedAppId: null,
            editingCollection: null, // id of collection being renamed
            editingName: "",
            editingIcon: "",
        });
    }

    get collections() {
        return this.collectionSvc.state.collections;
    }

    get filteredApps() {
        const colId = this.state.activeCollection;
        if (!colId) return this.props.apps;
        const col = this.collections.find((c) => c.id === colId);
        if (!col) return this.props.apps;
        return this.props.apps.filter((app) => col.menu_ids.includes(app.id));
    }

    selectCollection(colId) {
        this.state.activeCollection = colId;
    }

    // Drag-and-drop: dragging an app
    onAppDragStart(ev, app) {
        this.state.draggedAppId = app.id;
        ev.dataTransfer.effectAllowed = "copy";
        ev.dataTransfer.setData("text/plain", String(app.id));
    }

    onAppDragEnd() {
        this.state.draggedAppId = null;
    }

    // Drag-and-drop: dropping onto a collection tab
    onTabDragOver(ev, colId) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "copy";
        this.state.dragOverCollection = colId;
    }

    onTabDragLeave(colId) {
        if (this.state.dragOverCollection === colId) {
            this.state.dragOverCollection = null;
        }
    }

    async onTabDrop(ev, colId) {
        ev.preventDefault();
        this.state.dragOverCollection = null;
        const appId = parseInt(ev.dataTransfer.getData("text/plain") || "0");
        if (!appId || !colId) return;
        const col = this.collections.find((c) => c.id === colId);
        if (col && !col.menu_ids.includes(appId)) {
            await this.collectionSvc.addApp(appId, colId);
        }
    }

    async removeApp(ev, app) {
        ev.preventDefault();
        ev.stopPropagation();
        if (this.state.activeCollection) {
            await this.collectionSvc.removeApp(app.id, this.state.activeCollection);
        }
    }

    async addCollection() {
        const name = window.prompt(
            "Enter collection name\n(Optionally start with an emoji, e.g.: 💰 Finance)",
            "📁 New Collection"
        );
        if (!name || !name.trim()) return;
        const { icon, label } = this._parseIconName(name.trim());
        const col = await this.collectionSvc.createCollection(label, icon);
        this.state.activeCollection = col.id;
    }

    async deleteCollection(ev, colId) {
        ev.stopPropagation();
        const col = this.collections.find((c) => c.id === colId);
        if (!col) return;
        if (!window.confirm(`Delete collection "${col.icon} ${col.name}"?`)) return;
        await this.collectionSvc.deleteCollection(colId);
        if (this.state.activeCollection === colId) {
            this.state.activeCollection = null;
        }
    }

    startRename(ev, col) {
        ev.stopPropagation();
        this.state.editingCollection = col.id;
        this.state.editingName = col.name;
        this.state.editingIcon = col.icon;
    }

    async confirmRename(ev) {
        if (ev.key && ev.key !== "Enter") return;
        const colId = this.state.editingCollection;
        const name = this.state.editingName.trim();
        const icon = this.state.editingIcon.trim() || "📁";
        this.state.editingCollection = null;
        if (colId && name) {
            await this.collectionSvc.renameCollection(colId, name, icon);
        }
    }

    cancelRename() {
        this.state.editingCollection = null;
    }

    _parseIconName(input) {
        const chars = [...input];
        if (chars.length > 0 && chars[0].codePointAt(0) > 127) {
            const icon = chars[0];
            const label = input.slice(icon.length).trim() || input;
            return { icon, label };
        }
        return { icon: "📁", label: input };
    }
}

patch(NavBar, {
    components: {
        ...NavBar.components,
        AppCollectionManager,
    },
});
