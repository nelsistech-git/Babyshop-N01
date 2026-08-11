/** @odoo-module **/

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";

export const appCollectionService = {
    dependencies: ["orm"],
    async start(env, { orm }) {
        const state = reactive({
            collections: [],
            loaded: false,
        });

        async function load() {
            const result = await orm.call("app.collection", "get_user_collections", []);
            state.collections = result;
            state.loaded = true;
        }

        // After every mutation we reload from the server so state.collections gets
        // a fresh assignment on the reactive proxy, guaranteeing OWL re-renders.
        async function createCollection(name, icon) {
            const col = await orm.call("app.collection", "create_collection", [name, icon]);
            await load();
            return state.collections.find((c) => c.id === col.id) || col;
        }

        async function deleteCollection(collectionId) {
            await orm.call("app.collection", "delete_collection", [collectionId]);
            await load();
        }

        async function renameCollection(collectionId, name, icon) {
            await orm.call("app.collection", "rename_collection", [collectionId, name, icon]);
            await load();
        }

        async function addApp(menuId, collectionId) {
            await orm.call("app.collection", "add_app_to_collection", [menuId, collectionId]);
            await load();
        }

        async function removeApp(menuId, collectionId) {
            await orm.call("app.collection", "remove_app_from_collection", [menuId, collectionId]);
            await load();
        }

        await load();

        return { state, load, createCollection, deleteCollection, renameCollection, addApp, removeApp };
    },
};

registry.category("services").add("app_collection", appCollectionService);
