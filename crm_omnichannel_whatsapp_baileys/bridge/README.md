# QuickCRM Baileys Bridge

Standalone Node.js service that owns the WhatsApp Web connection and
relays messages to/from the `crm_omnichannel_whatsapp_baileys` Odoo module.
This must run as its own process, next to Odoo but separate from it
(Baileys is a Node library; Odoo's server is Python).

## 1. Install & run

```bash
cd bridge
npm install
BRIDGE_API_KEY="a-long-random-secret" \
PUBLIC_BASE_URL="https://wa-bridge.yourdomain.com" \
PORT=3300 \
npm start
```

Put it behind Nginx/Caddy with a real TLS certificate at
`wa-bridge.yourdomain.com`, proxying to `127.0.0.1:3300`. Keep it
running with `pm2 start server.js --name wa-bridge` or a systemd unit.

## 2. Configure the channel in Odoo

Settings → CRM Omni-Channel → Channels → WhatsApp:
- WhatsApp Provider: **Baileys**
- Bridge Base URL: `https://wa-bridge.yourdomain.com`
- Session / Account: any short slug, e.g. `main`
- Bridge API Key: the same `BRIDGE_API_KEY` you set above

Click **Start Pairing**, then refresh the form — the QR code appears.
Scan it from WhatsApp on your phone: Settings → Linked Devices → Link
a Device. Status flips to Connected automatically once paired
(the bridge pushes that to Odoo's webhook, no manual refresh needed
in production — refreshing the form just re-reads what's already
been written).

## 3. Firewall

Only the bridge's `/session/*` and `/send` endpoints need to be
reachable from your Odoo server. `/media/*` needs to be reachable
from Odoo too (Odoo downloads inbound media from there). Nothing
needs to be reachable from the public internet except through your
own auth (`BRIDGE_API_KEY`) — there is no public webhook to register
with a third party the way there is for the Meta Cloud API.

## 4. Multiple numbers

One bridge process can hold multiple sessions at once — just create
another `crm.channel` record (code=WhatsApp, provider=Baileys) with a
different Session / Account slug and Start Pairing again.

## Notes / limitations

- This uses the unofficial WhatsApp Web multi-device protocol
  (`@whiskeysockets/baileys`). Meta can and does occasionally break
  or rate-limit unofficial clients — keep the official Cloud API
  connector as a fallback for anything business-critical.
- Group messages are ignored by default (`handleInboundMessage` in
  `server.js` returns early on `@g.us` JIDs) — remove that check if
  you want group support too.
- Auth state is stored on disk under `bridge/auth/<session_id>/` —
  back this up, losing it means re-scanning the QR code.
