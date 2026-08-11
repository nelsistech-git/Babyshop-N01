/**
 * Splits static/src/jslib/chatroom.vendor.bundle.js (or chatroom.js) — vendor bundle with hashed odoo.define ids
 * into readable modules under static/src/jslib/chatroom_modules/
 *
 * Usage: node scripts/split-chatroom-bundle.mjs
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(__dirname, '..');
const SRC = path.join(ROOT, 'static', 'src', 'jslib');
const OUT_DIR = path.join(SRC, 'chatroom_modules');

function kebab(s) {
    return s
        .replace(/([a-z])([A-Z])/g, '$1-$2')
        .replace(/_/g, '-')
        .toLowerCase();
}

function primarySlug(body) {
    const m =
        body.match(/const\s+(\w+)\s*=\s*__exports\.\1\s*=\s*class\b/) ||
        body.match(/const\s+(\w+)\s*=\s*__exports\.\1\s*=\s*\{/) ||
        body.match(/__exports\.(\w+)\s*=\s*(\w+)\s*=\s*class\b/) ||
        body.match(/__exports\.(\w+)\s*=\s*function\b/) ||
        body.match(/const\s+(\w+)\s*=\s*__exports\.\1\s*=/);
    if (m) return kebab(m[1]);
    const patchM = body.match(/patch\(([A-Za-z]+)\.prototype/);
    if (patchM && !body.match(/const\s+\w+\s*=\s*__exports\.\w+\s*=\s*class\b/)) {
        return `patch-${kebab(patchM[1])}`;
    }
    if (body.includes("registry.category('actions').add('acrux.chat.conversation_tag'")) {
        return 'register-chatroom-actions';
    }
    const chatroomSvc = body.match(/__exports\.(chatroomNotificationService)\s*=/);
    if (chatroomSvc) return 'chatroom-notification-service';
    const check = body.match(/__exports\.(checkFileSize)\s*=/);
    if (check) return 'file-size-and-uploader';
    const hook = body.match(/__exports\.(useAttachmentUploader)\s*=/);
    if (hook) return 'use-attachment-uploader';
    return 'module';
}

let bundlePath = path.join(SRC, 'chatroom.vendor.bundle.js');
if (!fs.existsSync(bundlePath)) bundlePath = path.join(SRC, 'chatroom.js');
if (!fs.existsSync(bundlePath)) {
    console.error('Expected chatroom.vendor.bundle.js or chatroom.js under static/src/jslib');
    process.exit(1);
}
const content = fs.readFileSync(bundlePath, 'utf8');
console.log(`Source bundle: ${path.relative(ROOT, bundlePath)}`);
const pieces = content.split(/\}\);\;\r?\n(?=odoo\.define)/);
for (let i = 0; i < pieces.length - 1; i++) pieces[i] += '});;';

const modules = [];
for (let i = 0; i < pieces.length; i++) {
    const body = pieces[i].trim();
    const hm = body.match(/^odoo\.define\('(@[^']+)'/);
    if (!hm) {
        console.error('No odoo.define at chunk', i);
        process.exit(1);
    }
    const hash = hm[1];
    let slug = primarySlug(body);
    modules.push({ hash, slug, body, index: i });
}

const slugCount = new Map();
for (const m of modules) {
    const base = m.slug;
    const n = slugCount.get(base) || 0;
    slugCount.set(base, n + 1);
    m.fileSlug = n === 0 ? base : `${base}-${n + 1}`;
}

const NS = '@whatsapp_connector/chatroom_mod';
const hashToModuleId = new Map();
for (const m of modules) {
    hashToModuleId.set(m.hash, `${NS}/${m.fileSlug}`);
}

function rewriteBody(body) {
    let out = body;
    const hashes = [...hashToModuleId.keys()].sort((a, b) => b.length - a.length);
    for (const h of hashes) {
        const mid = hashToModuleId.get(h);
        const re = new RegExp(h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
        out = out.replace(re, mid);
    }
    return out;
}

if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
// Avoid stale files when slugs are renamed between runs
for (const f of fs.readdirSync(OUT_DIR)) {
    if (f.endsWith('.js') && /^\d{2}_/.test(f)) fs.unlinkSync(path.join(OUT_DIR, f));
}

const manifestLines = [];
for (const m of modules) {
    const newBody = rewriteBody(m.body);
    const fname = `${String(m.index).padStart(2, '0')}_${m.fileSlug.replace(/-/g, '_')}.js`;
    const fpath = path.join(OUT_DIR, fname);
    fs.writeFileSync(fpath, newBody + '\n', 'utf8');
    manifestLines.push(`            'whatsapp_connector/static/src/jslib/chatroom_modules/${fname}',`);
}

const readme = `# Chatroom JS modules (split from vendor bundle)

These files were produced by \`scripts/split-chatroom-bundle.mjs\` from the original single-file bundle (\`static/src/jslib/chatroom.vendor.bundle.js\`). Internal \`odoo.define\` ids use \`@whatsapp_connector/chatroom_mod/<slug>\` instead of SHA hashes.

- **Edit here** — this folder is what \`__manifest__.py\` loads (47 files; order matters).
- **Regenerating** — from \`whatsapp_connector/\`, run: \`node scripts/split-chatroom-bundle.mjs\` (overwrites \`NN_*.js\` here; the script deletes old numbered \`*.js\` first).
- **Note** — \`37_story_dialog.js\` defines both \`StoryDialog\` and \`Message\` (same as the original bundle).
- A full **modern** rewrite would use \`/** @odoo-module **/\` and \`import\`/\`export\` instead of \`odoo.define\` + \`require\`; this split keeps legacy AMD style so behavior stays identical.
`;

fs.writeFileSync(path.join(OUT_DIR, 'README.md'), readme);

const manifestSnippet = manifestLines.join('\n');
fs.writeFileSync(
    path.join(OUT_DIR, '_manifest_snippet.txt'),
    "// Replace single chatroom bundle entry in __manifest__.py with:\n" + manifestSnippet,
);

console.log(`Wrote ${modules.length} modules to ${path.relative(ROOT, OUT_DIR)}`);
console.log('Manifest snippet: chatroom_modules/_manifest_snippet.txt');
