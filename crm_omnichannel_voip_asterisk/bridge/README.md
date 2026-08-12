# QuickCRM AMI Bridge

Standalone Python daemon that holds the live Asterisk Manager
Interface (AMI) connection and forwards call events to the
`crm_omnichannel_voip_asterisk` Odoo module. Runs separately from Odoo.

## 1. Asterisk side

In `manager.conf`, add a manager user QuickCRM can use:

```ini
[quickcrm]
secret = a-strong-secret
read = call,agent
write = call,originate
permit = <odoo-and-bridge-server-ip>/255.255.255.255
```

Reload: `asterisk -rx "manager reload"`.

If you want recordings picked up automatically, make sure your
dialplan `Monitor()`/`MixMonitor()` writes to a path your web server
(or the bridge) can turn into a URL, and set `RECORDING_BASE_URL`
below accordingly.

## 2. Odoo side

Settings → CRM Omni-Channel → Channels → IP Calling:
- AMI Host / Port / Username / Secret — same manager user as above
- Originate Context — the dialplan context used for outbound calls
  (e.g. `from-internal`)
- Outbound Trunk/Gateway — your SIP trunk name if the dialplan needs it
- Webhook Shared Secret — any random string, matches `ODOO_WEBHOOK_SECRET` below

Per agent, under Settings → Users → (agent) → VoIP tab: set their
VoIP Extension (the PJSIP endpoint Asterisk should ring first when
that agent clicks "Call").

## 3. Run the bridge

```bash
pip install requests
AMI_HOST=pbx.yourdomain.com \
AMI_PORT=5038 \
AMI_USERNAME=quickcrm \
AMI_SECRET=a-strong-secret \
ODOO_WEBHOOK_URL=https://yourcrm.example.com/omni/webhook/asterisk \
ODOO_WEBHOOK_SECRET=same-value-as-Webhook-Shared-Secret-above \
CHANNEL_NAME="IP Calling" \
RECORDING_BASE_URL=https://yourcrm.example.com/recordings/ \
HEALTH_PORT=8088 \
python3 ami_bridge.py
```

The bridge also serves `GET :8088/health` -> `{"ok": true, "ami_connected": true|false}`
so Odoo can tell "the bridge process is up" apart from "the bridge is
actually logged into Asterisk right now". Point
`crm_omnichannel_connect_center`'s Settings > Connections > AMI Bridge
Health URL at `http://<this-host>:8088` (keep it off the public internet -
put it behind the same firewall as AMI itself, or proxy it if Odoo is
remote).

Keep it alive with `pm2 start ami_bridge.py --interpreter python3
--name ami-bridge` or a systemd unit — it auto-reconnects on its own
if the AMI connection drops, but the process itself needs a
supervisor.

## How a call flows end-to-end

1. Agent clicks **Call** on a Contact/Lead in Odoo →
   `crm.call.log.action_click_to_call` creates the record, then
   `_originate_via_asterisk()` sends an AMI `Originate` (synchronous,
   from inside the Odoo request) telling Asterisk to ring the agent's
   extension first.
2. Asterisk starts working the call. Every state change (ringing,
   answered, hold, hangup) fires an AMI event on the *separate*
   long-lived connection `ami_bridge.py` holds open.
3. `ami_bridge.py` forwards each relevant event as JSON to
   `/omni/webhook/asterisk`.
4. Odoo's `crm.call.log._asterisk_sync_event()` updates the same
   record in real time — no polling, no manual "mark as answered".

Inbound calls Asterisk receives that Odoo didn't originate work the
same way from step 2 onward — the webhook creates a fresh
`crm.call.log` the first time it sees a `ring` event with no matching
record.
