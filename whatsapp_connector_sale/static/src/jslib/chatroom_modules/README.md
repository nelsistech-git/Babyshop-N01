# whatsapp_connector_sale — chatroom extension modules

Split from `static/src/jslib/chatroom.vendor.bundle.js` (or `chatroom.js`) using
`whatsapp_connector/scripts/split-chatroom-extension.mjs`. Module ids: `@whatsapp_connector_sale/chatroom_ext/<slug>`.

Dependencies on the base ChatRoom bundle resolve to `@whatsapp_connector/chatroom_mod/…` (pairing
`chatroom.vendor.bundle.js` with `whatsapp_connector/…/chatroom_modules/NN_*.js`).

Regenerate: `node whatsapp_connector/scripts/split-chatroom-extension.mjs whatsapp_connector_sale`
