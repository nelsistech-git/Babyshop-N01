# Chatroom JS modules (split from vendor bundle)

These files were produced by `scripts/split-chatroom-bundle.mjs` from the original single-file bundle (`static/src/jslib/chatroom.vendor.bundle.js`). Internal `odoo.define` ids use `@whatsapp_connector/chatroom_mod/<slug>` instead of SHA hashes.

- **Edit here** — this folder is what `__manifest__.py` loads (47 files; order matters).
- **Regenerating** — from `whatsapp_connector/`, run: `node scripts/split-chatroom-bundle.mjs` (overwrites `NN_*.js` here; the script deletes old numbered `*.js` first).
- **Note** — `37_story_dialog.js` defines both `StoryDialog` and `Message` (same as the original bundle).
- A full **modern** rewrite would use `/** @odoo-module **/` and `import`/`export` instead of `odoo.define` + `require`; this split keeps legacy AMD style so behavior stays identical.
