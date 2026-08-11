/**
 * Splits addon static/src/jslib/chatroom.js (CRM / Sale / …) into chatroom_modules/
 * and rewrites dependencies: base whatsapp_connector hashes -> @whatsapp_connector/chatroom_mod/…
 * and local hashes -> @<addon>/chatroom_ext/…
 *
 * Usage (from odoo-modules/):
 *   node whatsapp_connector/scripts/split-chatroom-extension.mjs whatsapp_connector_crm
 *   node whatsapp_connector/scripts/split-chatroom-extension.mjs whatsapp_connector_sale
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ODOO_MODULES = path.join(__dirname, '..', '..');
const ADDON = process.argv[2];
if (!ADDON) {
    console.error('Usage: node split-chatroom-extension.mjs <addon_name>  e.g. whatsapp_connector_crm');
    process.exit(1);
}

const kebab = (s) =>
    s
        .replace(/([a-z])([A-Z])/g, '$1-$2')
        .replace(/_/g, '-')
        .toLowerCase();

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
    if (body.includes("registry.category('views').add('acrux_whatsapp_sale_order'")) {
        return 'register-sale-form-view';
    }
    return 'module';
}

function loadBaseHashToModuleId() {
    const vendorPath = path.join(ODOO_MODULES, 'whatsapp_connector/static/src/jslib/chatroom.vendor.bundle.js');
    const baseDir = path.join(ODOO_MODULES, 'whatsapp_connector/static/src/jslib/chatroom_modules');
    if (!fs.existsSync(vendorPath)) {
        throw new Error(`Missing ${vendorPath} (split whatsapp_connector bundle first)`);
    }
    if (!fs.existsSync(baseDir)) {
        throw new Error(`Missing ${baseDir}`);
    }
    const vendor = fs.readFileSync(vendorPath, 'utf8');
    const hashOrder = [...vendor.matchAll(/odoo\.define\('(@[^']+)'/g)].map((x) => x[1]);
    const files = fs
        .readdirSync(baseDir)
        .filter((f) => /^\d{2}_/.test(f) && f.endsWith('.js'))
        .sort();
    const map = new Map();
    const n = Math.min(hashOrder.length, files.length);
    for (let i = 0; i < n; i++) {
        const line = fs.readFileSync(path.join(baseDir, files[i]), 'utf8').split(/\r?\n/)[0];
        const m = line.match(/odoo\.define\('([^']+)'/);
        if (m) map.set(hashOrder[i], m[1]);
    }
    if (hashOrder.length !== files.length) {
        console.warn(`Base: ${hashOrder.length} hashes vs ${files.length} files — check whatsapp_connector split`);
    }
    return map;
}

const addonRoot = path.join(ODOO_MODULES, ADDON);
const SRC_LIB = path.join(addonRoot, 'static', 'src', 'jslib');
let bundlePath = path.join(SRC_LIB, 'chatroom.vendor.bundle.js');
if (!fs.existsSync(bundlePath)) bundlePath = path.join(SRC_LIB, 'chatroom.js');
if (!fs.existsSync(bundlePath)) {
    console.error(`No chatroom.vendor.bundle.js or chatroom.js under ${path.relative(ODOO_MODULES, SRC_LIB)}`);
    process.exit(1);
}

const OUT_DIR = path.join(SRC_LIB, 'chatroom_modules');
const moduleNs = `@${ADDON}/chatroom_ext`;

const content = fs.readFileSync(bundlePath, 'utf8');
console.log(`Source: ${path.relative(ODOO_MODULES, bundlePath)}`);

const pieces = content.split(/\}\);\;\s*(?=odoo\.define)/);
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

const hashToModuleId = new Map(loadBaseHashToModuleId());
for (const m of modules) {
    hashToModuleId.set(m.hash, `${moduleNs}/${m.fileSlug}`);
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
for (const f of fs.readdirSync(OUT_DIR)) {
    if (f.endsWith('.js') && /^\d{2}_/.test(f)) fs.unlinkSync(path.join(OUT_DIR, f));
}

const manifestLines = [];
for (const m of modules) {
    const newBody = rewriteBody(m.body);
    const fname = `${String(m.index).padStart(2, '0')}_${m.fileSlug.replace(/-/g, '_')}.js`;
    const fpath = path.join(OUT_DIR, fname);
    fs.writeFileSync(fpath, newBody + '\n', 'utf8');
    manifestLines.push(`            '${ADDON}/static/src/jslib/chatroom_modules/${fname}',`);
}

const readme = `# ${ADDON} — chatroom extension modules

Split from \`static/src/jslib/chatroom.vendor.bundle.js\` (or \`chatroom.js\`) using
\`whatsapp_connector/scripts/split-chatroom-extension.mjs\`. Module ids: \`@${ADDON}/chatroom_ext/<slug>\`.

Dependencies on the base ChatRoom bundle resolve to \`@whatsapp_connector/chatroom_mod/…\` (pairing
\`chatroom.vendor.bundle.js\` with \`whatsapp_connector/…/chatroom_modules/NN_*.js\`).

Regenerate: \`node whatsapp_connector/scripts/split-chatroom-extension.mjs ${ADDON}\`
`;

fs.writeFileSync(path.join(OUT_DIR, 'README.md'), readme);
fs.writeFileSync(
    path.join(OUT_DIR, '_manifest_snippet.txt'),
    `// In ${ADDON}/__manifest__.py assets, replace chatroom.js with:\n` + manifestLines.join('\n') + '\n',
);

console.log(`Wrote ${modules.length} modules to ${path.relative(ODOO_MODULES, OUT_DIR)}`);
console.log(`Namespace: ${moduleNs}`);
