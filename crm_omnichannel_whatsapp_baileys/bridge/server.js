/**
 * QuickCRM Baileys Bridge
 * ------------------------------------------------------------------
 * Small standalone Node.js service that owns the actual WhatsApp Web
 * (multi-device) connection using @whiskeysockets/baileys, and talks
 * to the crm_omnichannel_whatsapp_baileys Odoo module over plain
 * HTTP/JSON in both directions:
 *
 *   Odoo  -> bridge : POST /session/start, GET /session/:id/status,
 *                      POST /session/:id/logout, POST /send
 *   bridge -> Odoo   : POST <ODOO_WEBHOOK_URL> with events
 *                      {event:"qr"|"connection"|"message"|"ack", ...}
 *
 * Run this as its own process (pm2 / systemd / docker), NOT inside Odoo.
 * See README.md in this folder for setup.
 *
 * Every control endpoint requires header:  X-Bridge-Api-Key: <key>
 * matching BRIDGE_API_KEY below - keep this behind HTTPS.
 */
'use strict';

const express = require('express');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const QRCode = require('qrcode');
const pino = require('pino');
const {
  default: makeWASocket,
  DisconnectReason,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
  downloadMediaMessage,
} = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');

const PORT = process.env.PORT || 3300;
const BRIDGE_API_KEY = process.env.BRIDGE_API_KEY || 'change-me';
const PUBLIC_BASE_URL = process.env.PUBLIC_BASE_URL || `http://localhost:${PORT}`;
const AUTH_DIR = process.env.AUTH_DIR || path.join(__dirname, 'auth');
const MEDIA_DIR = process.env.MEDIA_DIR || path.join(__dirname, 'media');
const logger = pino({ level: process.env.LOG_LEVEL || 'warn' });

fs.mkdirSync(AUTH_DIR, { recursive: true });
fs.mkdirSync(MEDIA_DIR, { recursive: true });

/** In-memory registry of active sessions: session_id -> SessionEntry */
const sessions = new Map();

function requireApiKey(req, res, next) {
  if (req.header('X-Bridge-Api-Key') !== BRIDGE_API_KEY) {
    return res.status(403).json({ ok: false, error: 'forbidden' });
  }
  next();
}

async function postToOdoo(webhookUrl, body) {
  if (!webhookUrl) return;
  try {
    await axios.post(webhookUrl, body, {
      headers: { 'X-Bridge-Api-Key': BRIDGE_API_KEY, 'Content-Type': 'application/json' },
      timeout: 15000,
    });
  } catch (err) {
    logger.warn({ err: err.message, webhookUrl }, 'Failed to POST event to Odoo webhook');
  }
}

/** Start (or resume) a WhatsApp session and wire up its event handlers. */
async function startSession(sessionId, webhookUrl) {
  let entry = sessions.get(sessionId);
  if (entry && entry.sock) {
    entry.webhookUrl = webhookUrl || entry.webhookUrl;
    return entry;
  }

  const authFolder = path.join(AUTH_DIR, sessionId);
  fs.mkdirSync(authFolder, { recursive: true });
  const { state, saveCreds } = await useMultiFileAuthState(authFolder);
  const { version } = await fetchLatestBaileysVersion();

  entry = { sock: null, webhookUrl, state: 'qr_pending', phoneNumber: null };
  sessions.set(sessionId, entry);

  const sock = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: false,
    browser: ['QuickCRM', 'Chrome', '1.0'],
  });
  entry.sock = sock;

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      const qrPngBase64 = (await QRCode.toDataURL(qr)).split(',')[1];
      entry.state = 'qr_pending';
      await postToOdoo(entry.webhookUrl, { event: 'qr', session_id: sessionId, qr_base64: qrPngBase64 });
    }

    if (connection === 'open') {
      entry.state = 'connected';
      entry.phoneNumber = (sock.user && sock.user.id ? sock.user.id.split(':')[0] : null);
      await postToOdoo(entry.webhookUrl, {
        event: 'connection', session_id: sessionId, state: 'connected', phone_number: entry.phoneNumber,
      });
    }

    if (connection === 'close') {
      const statusCode = new Boom(lastDisconnect?.error)?.output?.statusCode;
      const loggedOut = statusCode === DisconnectReason.loggedOut;
      entry.state = 'disconnected';
      await postToOdoo(entry.webhookUrl, { event: 'connection', session_id: sessionId, state: 'disconnected' });
      if (!loggedOut) {
        // Transient drop (network blip, restart, etc.) - reconnect automatically.
        sessions.delete(sessionId);
        setTimeout(() => startSession(sessionId, webhookUrl).catch((e) => logger.error(e)), 2000);
      } else {
        // User unpaired from their phone - clear creds so a fresh QR is required.
        fs.rmSync(authFolder, { recursive: true, force: true });
        sessions.delete(sessionId);
      }
    }
  });

  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const msg of messages) {
      try {
        await handleInboundMessage(sessionId, entry, sock, msg);
      } catch (err) {
        logger.error({ err: err.message }, 'Failed handling inbound message');
      }
    }
  });

  sock.ev.on('messages.update', async (updates) => {
    for (const u of updates) {
      const status = mapAckStatus(u.update && u.update.status);
      if (status) {
        await postToOdoo(entry.webhookUrl, {
          event: 'ack', session_id: sessionId, message_id: u.key.id, status,
        });
      }
    }
  });

  return entry;
}

function mapAckStatus(baileysStatus) {
  // Baileys ack numeric: 2=server, 3=delivered, 4=read
  if (baileysStatus === 3) return 'delivered';
  if (baileysStatus === 4) return 'read';
  return null;
}

async function handleInboundMessage(sessionId, entry, sock, msg) {
  if (!msg.message || msg.key.fromMe) return; // ignore our own echoes
  const from = msg.key.remoteJid;
  if (!from || from.endsWith('@g.us')) return; // skip group chats by default

  const pushName = msg.pushName || null;
  const messageId = msg.key.id;
  const content = msg.message;

  let type = 'text';
  let text = '';
  let mediaUrl = null;

  if (content.conversation) {
    text = content.conversation;
  } else if (content.extendedTextMessage) {
    text = content.extendedTextMessage.text || '';
  } else if (content.imageMessage) {
    type = 'image'; text = content.imageMessage.caption || '';
    mediaUrl = await saveIncomingMedia(sock, msg, 'image', sessionId);
  } else if (content.videoMessage) {
    type = 'video'; text = content.videoMessage.caption || '';
    mediaUrl = await saveIncomingMedia(sock, msg, 'video', sessionId);
  } else if (content.audioMessage) {
    type = 'audio';
    mediaUrl = await saveIncomingMedia(sock, msg, 'audio', sessionId);
  } else if (content.documentMessage) {
    type = 'document'; text = content.documentMessage.fileName || '';
    mediaUrl = await saveIncomingMedia(sock, msg, 'document', sessionId);
  } else if (content.stickerMessage) {
    type = 'sticker';
    mediaUrl = await saveIncomingMedia(sock, msg, 'sticker', sessionId);
  } else if (content.locationMessage) {
    type = 'location';
    text = `${content.locationMessage.degreesLatitude}, ${content.locationMessage.degreesLongitude}`;
  } else {
    return; // unsupported type (reactions, protocol messages, etc.) - ignore
  }

  await postToOdoo(entry.webhookUrl, {
    event: 'message',
    session_id: sessionId,
    from,
    name: pushName,
    message_id: messageId,
    type,
    text,
    caption: text,
    media_url: mediaUrl,
    timestamp: msg.messageTimestamp,
  });
}

async function saveIncomingMedia(sock, msg, type, sessionId) {
  const buffer = await downloadMediaMessage(msg, 'buffer', {}, { logger });
  const ext = { image: 'jpg', video: 'mp4', audio: 'ogg', document: 'bin', sticker: 'webp' }[type] || 'bin';
  const fileName = `${sessionId}_${msg.key.id}.${ext}`;
  fs.writeFileSync(path.join(MEDIA_DIR, fileName), buffer);
  return `${PUBLIC_BASE_URL}/media/${fileName}`;
}

// =====================================================================
// HTTP API (Odoo -> bridge)
// =====================================================================
const app = express();
app.use(express.json({ limit: '25mb' }));
app.use('/media', express.static(MEDIA_DIR));

app.post('/session/start', requireApiKey, async (req, res) => {
  const { session_id, webhook_url } = req.body || {};
  if (!session_id) return res.status(400).json({ ok: false, error: 'session_id required' });
  try {
    const entry = await startSession(session_id, webhook_url);
    res.json({ ok: true, state: entry.state });
  } catch (err) {
    logger.error({ err: err.message }, 'startSession failed');
    res.status(500).json({ ok: false, error: err.message });
  }
});

app.get('/session/:id/status', requireApiKey, (req, res) => {
  const entry = sessions.get(req.params.id);
  if (!entry) return res.json({ ok: true, state: 'disconnected' });
  res.json({ ok: true, state: entry.state, phone_number: entry.phoneNumber });
});

app.post('/session/:id/logout', requireApiKey, async (req, res) => {
  const entry = sessions.get(req.params.id);
  if (entry && entry.sock) {
    try { await entry.sock.logout(); } catch (e) { /* already gone */ }
  }
  sessions.delete(req.params.id);
  fs.rmSync(path.join(AUTH_DIR, req.params.id), { recursive: true, force: true });
  res.json({ ok: true });
});

app.post('/send', requireApiKey, async (req, res) => {
  const { session_id, to, type, text, media_url, caption } = req.body || {};
  const entry = sessions.get(session_id);
  if (!entry || !entry.sock || entry.state !== 'connected') {
    return res.status(409).json({ ok: false, error: 'session not connected' });
  }
  const jid = to.includes('@') ? to : `${to}@s.whatsapp.net`;
  try {
    let sent;
    if (type === 'text' || !type) {
      sent = await entry.sock.sendMessage(jid, { text: text || '' });
    } else if (['image', 'video', 'audio', 'document', 'sticker'].includes(type)) {
      const mediaResp = await axios.get(media_url, { responseType: 'arraybuffer', timeout: 30000 });
      const buffer = Buffer.from(mediaResp.data);
      const key = type === 'document' ? 'document' : type;
      const payload = { [key]: buffer, caption: caption || undefined, mimetype: mediaResp.headers['content-type'] };
      sent = await entry.sock.sendMessage(jid, payload);
    } else {
      return res.status(400).json({ ok: false, error: `unsupported type ${type}` });
    }
    res.json({ ok: true, message_id: sent.key.id });
  } catch (err) {
    logger.error({ err: err.message }, 'send failed');
    res.status(500).json({ ok: false, error: err.message });
  }
});

app.get('/health', (req, res) => res.json({ ok: true, sessions: sessions.size }));

app.listen(PORT, () => logger.info(`QuickCRM Baileys bridge listening on :${PORT}`));
