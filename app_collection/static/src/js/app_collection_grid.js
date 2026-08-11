/** @odoo-module **/

import { Component, useState, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";

export class AppCollectionGrid extends Component {
    static template = "app_collection.AppCollectionGrid";
    static props = { apps: { type: Array } };

    setup() {
        this.collectionSvc = useService("app_collection");
        this.state = useState({
            activeTab: null,        // null = All Apps, or collection id
            draggedAppId: null,
            dropOnFolderId: null,   // folder icon / tab being hovered (drop target)
            dropOnAppId: null,      // standalone app being hovered (create-folder target)
            editingTabId: null,     // which tab is in rename mode
            editingTabName: "",     // controlled input value while renaming
        });

        // Close folder view on navigation
        const onUIUpdated = () => { this.state.activeTab = null; };
        this.env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", onUIUpdated);
        onWillUnmount(() => {
            this.env.bus.removeEventListener("ACTION_MANAGER:UI-UPDATED", onUIUpdated);
        });
    }

    // ── Data helpers ─────────────────────────────────────────────────────────

    get collections() {
        return this.collectionSvc.state.collections;
    }

    get standaloneApps() {
        const inFolders = new Set(this.collections.flatMap((c) => c.menu_ids));
        return this.props.apps.filter((a) => !inFolders.has(a.id));
    }

    getCollectionApps(col) {
        return this.props.apps.filter((a) => col.menu_ids.includes(a.id));
    }

    // Returns 4 slots (app | null) for the iOS folder icon mosaic
    getFolderPreview(col) {
        const apps = this.getCollectionApps(col);
        return [0, 1, 2, 3].map((i) => apps[i] || null);
    }

    getActiveCollection() {
        return this.collections.find((c) => c.id === this.state.activeTab) || null;
    }

    // ── Navigation ────────────────────────────────────────────────────────────

    selectTab(colId) {
        this.state.activeTab = colId;
        this.state.editingTabId = null;
    }

    launchApp(app) {
        this.state.activeTab = null;
        app.action();
    }

    // ── Drag from standalone app ──────────────────────────────────────────────

    onAppDragStart(ev, app) {
        this.state.draggedAppId = app.id;
        ev.dataTransfer.effectAllowed = "copy";
        ev.dataTransfer.setData("text/plain", String(app.id));
    }

    onDragEnd() {
        this.state.draggedAppId = null;
        this.state.dropOnFolderId = null;
        this.state.dropOnAppId = null;
    }

    // ── Drop on folder (icon in grid OR tab in bar) ───────────────────────────
    // Key fix: check ev.relatedTarget so dragleave from parent→child is ignored

    onFolderDragEnter(ev, colId) {
        ev.preventDefault();
        this.state.dropOnFolderId = colId;
    }

    onFolderDragOver(ev, colId) {
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "copy";
        this.state.dropOnFolderId = colId;
    }

    onFolderDragLeave(ev, colId) {
        // Ignore leave events that go to a *child* element
        if (ev.currentTarget.contains(ev.relatedTarget)) return;
        if (this.state.dropOnFolderId === colId) {
            this.state.dropOnFolderId = null;
        }
    }

    async onFolderDrop(ev, col) {
        ev.preventDefault();
        ev.stopPropagation();
        this.state.dropOnFolderId = null;
        const appId = parseInt(ev.dataTransfer.getData("text/plain") || "0");
        if (!appId) return;
        // Always fetch fresh col from state to avoid stale menu_ids
        const freshCol = this.collections.find((c) => c.id === col.id);
        if (freshCol && !freshCol.menu_ids.includes(appId)) {
            await this.collectionSvc.addApp(appId, col.id);
        }
    }

    // ── Drop on another standalone app → create folder ────────────────────────

    onAppOverDragOver(ev, app) {
        if (this.state.draggedAppId && this.state.draggedAppId !== app.id) {
            ev.preventDefault();
            ev.dataTransfer.dropEffect = "copy";
            this.state.dropOnAppId = app.id;
        }
    }

    onAppOverDragLeave(ev, app) {
        if (ev.currentTarget.contains(ev.relatedTarget)) return;
        if (this.state.dropOnAppId === app.id) {
            this.state.dropOnAppId = null;
        }
    }

    async onAppOverDrop(ev, targetApp) {
        ev.preventDefault();
        this.state.dropOnAppId = null;
        const draggedId = parseInt(ev.dataTransfer.getData("text/plain") || "0");
        if (!draggedId || draggedId === targetApp.id) return;

        const col = await this.collectionSvc.createCollection("New Folder", "📁");
        await this.collectionSvc.addApp(draggedId, col.id);
        await this.collectionSvc.addApp(targetApp.id, col.id);
        this.state.activeTab = col.id;
        // Auto-enter rename mode for the new folder
        this.state.editingTabId = col.id;
        this.state.editingTabName = "New Folder";
    }

    // ── Remove app from active folder ─────────────────────────────────────────

    async removeFromFolder(app) {
        const colId = this.state.activeTab;
        if (!colId) return;
        await this.collectionSvc.removeApp(app.id, colId);
    }

    // ── Folder creation via button ────────────────────────────────────────────

    async addFolder() {
        const col = await this.collectionSvc.createCollection("New Folder", "📁");
        this.state.activeTab = col.id;
        this.state.editingTabId = col.id;
        this.state.editingTabName = "New Folder";
    }

    // ── Folder rename (controlled input on the tab) ───────────────────────────

    startRename(ev, col) {
        ev.stopPropagation();
        this.state.editingTabId = col.id;
        this.state.editingTabName = col.name; // only the name, not the icon
    }

    onRenameInput(ev) {
        this.state.editingTabName = ev.target.value;
    }

    async confirmRename(col) {
        const colId = this.state.editingTabId;
        const name = this.state.editingTabName.trim();
        this.state.editingTabId = null;
        this.state.editingTabName = "";
        if (colId && name && name !== col.name) {
            await this.collectionSvc.renameCollection(colId, name, col.icon);
        }
    }

    onRenameKeydown(ev, col) {
        // CRITICAL: stop propagation so muk_web_theme's global window keydown
        // listener doesn't open the command palette while we're typing.
        ev.stopPropagation();
        if (ev.key === "Enter") { ev.preventDefault(); this.confirmRename(col); }
        if (ev.key === "Escape") { this.state.editingTabId = null; }
    }

    // ── Folder delete ─────────────────────────────────────────────────────────

    async deleteFolder(ev, col) {
        ev.stopPropagation();
        if (!window.confirm(`Delete folder "${col.icon} ${col.name}"?\nApps will return to All Apps.`)) return;
        if (this.state.activeTab === col.id) this.state.activeTab = null;
        this.state.editingTabId = null;
        await this.collectionSvc.deleteCollection(col.id);
    }
}

patch(NavBar, {
    components: {
        ...NavBar.components,
        AppCollectionGrid,
    },
});
