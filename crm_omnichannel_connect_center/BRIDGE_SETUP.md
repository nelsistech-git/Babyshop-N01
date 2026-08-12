# Getting the Baileys bridge running

The QR-pairing WhatsApp connector needs `bridge/server.js` (inside
`crm_omnichannel_whatsapp_baileys/bridge/`) running as its own always-on
process, reachable by both Odoo and the public internet (WhatsApp itself
doesn't call it — but your Odoo server does, and if Odoo is hosted
elsewhere than the bridge, it needs a public HTTPS URL and a real TLS cert;
self-signed certs will make `requests` calls from Odoo fail).

Pick ONE of the three options below.

## Option A - Docker (recommended, easiest to keep alive)

```bash
cd crm_omnichannel_whatsapp_baileys/bridge
cat > Dockerfile <<'EOF'
FROM node:20-slim
WORKDIR /app
COPY package.json .
RUN npm install --omit=dev
COPY . .
EXPOSE 3300
CMD ["node", "server.js"]
EOF

docker build -t wa-bridge .
docker run -d --name wa-bridge --restart unless-stopped \
  -p 3300:3300 \
  -e BRIDGE_API_KEY="choose-a-long-random-secret" \
  -e PUBLIC_BASE_URL="https://wa-bridge.yourdomain.com" \
  -v wa-bridge-auth:/app/auth \
  -v wa-bridge-media:/app/media \
  wa-bridge
```

Put an Nginx/Caddy reverse proxy with a real TLS certificate in front of
port 3300 at `wa-bridge.yourdomain.com` (or your chosen host). This is the
URL you'll enter as **Bridge URL** in Settings, and the `BRIDGE_API_KEY`
value is what you enter as **Bridge API Key**.

## Option B - PM2 on the same VPS as Odoo

```bash
cd crm_omnichannel_whatsapp_baileys/bridge
npm install
npm install -g pm2
BRIDGE_API_KEY="choose-a-long-random-secret" \
PUBLIC_BASE_URL="https://your-odoo-host.com/wa-bridge" \
PORT=3300 \
pm2 start server.js --name wa-bridge
pm2 save
pm2 startup   # follow the printed instructions so it survives reboots
```

Then reverse-proxy `/wa-bridge/` (or a subdomain) to `localhost:3300` in
whatever web server already fronts Odoo.

## Option C - systemd

```bash
cd crm_omnichannel_whatsapp_baileys/bridge
npm install
sudo tee /etc/systemd/system/wa-bridge.service > /dev/null <<EOF
[Unit]
Description=WhatsApp Baileys bridge
After=network.target

[Service]
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/node server.js
Restart=always
Environment=BRIDGE_API_KEY=choose-a-long-random-secret
Environment=PUBLIC_BASE_URL=https://wa-bridge.yourdomain.com
Environment=PORT=3300
User=www-data

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now wa-bridge
```

## After it's running

1. In Odoo: **Settings > Omnichannel > Connections**, enter the Bridge URL
   and Bridge API Key, then click **Test Bridge Connection** — it should
   say "Bridge reachable."
2. **Settings > Omnichannel > Add WhatsApp Number** — give it a label,
   click **Start Pairing**, and scan the QR that appears (it refreshes
   itself, no need to reload the page). Repeat for each additional
   number — each run creates a separate session, so numbers don't
   interfere with each other.
3. `docker logs -f wa-bridge` (or `pm2 logs wa-bridge` / `journalctl -u
   wa-bridge -f`) is the first place to look if a QR never appears or a
   number keeps disconnecting.

---

# Getting the VoIP (Asterisk AMI) bridge running

The IP Calling connector needs `bridge/ami_bridge.py` (inside
`crm_omnichannel_voip_asterisk/bridge/`) running as its own always-on
process too - same reasoning as the WhatsApp bridge: AMI is a persistent
socket, which doesn't fit inside a normal Odoo HTTP worker. This is
**separate** from Asterisk itself (which you presumably already have
running as your PBX) - this is a small relay between Asterisk's AMI and
Odoo's webhook.

## 1. Asterisk side (one-time)

In `manager.conf` on your Asterisk box, add a manager user:

```ini
[quickcrm]
secret = a-strong-secret
read = call,agent
write = call,originate
permit = <bridge-server-ip>/255.255.255.255
```

`asterisk -rx "manager reload"` to apply it.

## 2. Run the bridge (Docker)

```bash
cd crm_omnichannel_voip_asterisk/bridge
cat > Dockerfile <<'EOF'
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir requests
EXPOSE 8088
CMD ["python3", "ami_bridge.py"]
EOF

docker build -t ami-bridge .
docker run -d --name ami-bridge --restart unless-stopped \
  -p 8088:8088 \
  -e AMI_HOST="pbx.yourdomain.com" \
  -e AMI_PORT="5038" \
  -e AMI_USERNAME="quickcrm" \
  -e AMI_SECRET="a-strong-secret" \
  -e ODOO_WEBHOOK_URL="https://your-odoo-host.com/omni/webhook/asterisk" \
  -e ODOO_WEBHOOK_SECRET="choose-a-long-random-secret" \
  -e CHANNEL_NAME="IP Calling" \
  -e HEALTH_PORT="8088" \
  ami-bridge
```

(Or PM2 / systemd, same pattern as the WhatsApp bridge above - just
swap `server.js` for `python3 ami_bridge.py`.)

## 3. Wire it up in Odoo

1. **Settings > Omnichannel > Connections**: fill in AMI Host/Port/
   Username/Secret and the AMI Bridge Health URL (`http://<bridge-
   host>:8088`, or wherever you proxied it), then **Test AMI Login**
   and **Test Event Bridge** - both should come back green.
2. **Settings > Omnichannel > Add Calling Line**: give it a label,
   review the pre-filled AMI details, and click **Test & Connect** -
   it checks AMI login live before saving anything.
3. Per agent: **Settings > Users** (their profile) **> VoIP tab** -
   set their Extension so Asterisk knows which endpoint to ring first
   when they click Call.
