/** @odoo-module **/
import { loadJS, loadCSS } from "@web/core/assets";

const LEAFLET = "/nelsis_field_tracking/static/lib/leaflet/";

export const STATUS_COLOR = {
    online: "#16a34a", offline: "#94a3b8", flagged: "#dc2626", in: "#0b5fb8", out: "#7c3aed",
};

export function pinHtml(color, text = "") {
    return `<div class="nl-pin"><div class="b" style="background:${color}"><i>${text}</i></div></div>`;
}

function pinSvg(color) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="34" height="44" viewBox="0 0 34 44">
      <path d="M17 1C8.7 1 2 7.6 2 15.8 2 27 17 43 17 43s15-16 15-27.2C32 7.6 25.3 1 17 1z" fill="${color}" stroke="#fff" stroke-width="2.5"/>
      <circle cx="17" cy="16" r="6" fill="#fff"/></svg>`;
    return "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg);
}

/** Google Maps implementation */
export class GoogleAdapter {
    static async load(key) {
        if (!window.google || !window.google.maps) {
            await loadJS(`https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&v=weekly`);
        }
    }
    constructor(el) {
        this.g = window.google.maps;
        this.map = new this.g.Map(el, {
            center: { lat: 23.8103, lng: 90.4125 }, zoom: 11, mapTypeControl: false, streetViewControl: false,
            fullscreenControl: true, styles: [{ featureType: "poi.business", stylers: [{ visibility: "off" }] }],
        });
        this.markers = new Map();
        this.layer = [];
        this.info = new this.g.InfoWindow();
    }
    _clear(list) { list.forEach((o) => o.setMap(null)); list.length = 0; }
    setEmployees(items, onClick) {
        const seen = new Set();
        for (const it of items) {
            seen.add(it.id);
            const pos = { lat: it.lat, lng: it.lng };
            let m = this.markers.get(it.id);
            const icon = { url: pinSvg(it.color), scaledSize: new this.g.Size(34, 44), anchor: new this.g.Point(17, 43) };
            if (!m) {
                m = new this.g.Marker({ map: this.map, position: pos, icon, title: it.title });
                m.addListener("click", () => onClick(it.id));
                this.markers.set(it.id, m);
            } else { m.setPosition(pos); m.setIcon(icon); m.setTitle(it.title); }
        }
        for (const [id, m] of this.markers) {
            if (!seen.has(id)) { m.setMap(null); this.markers.delete(id); }
        }
    }
    fit(points) {
        if (!points.length) return;
        const b = new this.g.LatLngBounds();
        points.forEach((p) => b.extend(p));
        this.map.fitBounds(b, 80);
        if (points.length === 1) this.map.setZoom(16);
    }
    focus(lat, lng) { this.map.panTo({ lat, lng }); this.map.setZoom(Math.max(this.map.getZoom(), 15)); }
    clearOverlay() { this._clear(this.layer); }
    drawRoute(points, punches, sites) {
        this.clearOverlay();
        if (points.length) {
            const line = new this.g.Polyline({
                map: this.map, strokeColor: "#4b1a7a", strokeOpacity: 0.85, strokeWeight: 4,
                path: points.map((p) => ({ lat: p.lat, lng: p.lng })),
            });
            this.layer.push(line);
            points.forEach((p) => {
                const c = new this.g.Circle({
                    map: this.map, center: { lat: p.lat, lng: p.lng }, radius: 6,
                    strokeColor: p.genuine ? "#0b5fb8" : "#dc2626", fillColor: p.genuine ? "#0b5fb8" : "#dc2626",
                    fillOpacity: 0.9, strokeWeight: 1, clickable: true,
                });
                c.addListener("click", () => {
                    this.info.setContent(p.html); this.info.setPosition({ lat: p.lat, lng: p.lng }); this.info.open(this.map);
                });
                this.layer.push(c);
            });
        }
        punches.forEach((p) => {
            const m = new this.g.Marker({
                map: this.map, position: { lat: p.lat, lng: p.lng },
                icon: { url: pinSvg(p.type === "in" ? STATUS_COLOR.in : STATUS_COLOR.out), scaledSize: new this.g.Size(34, 44), anchor: new this.g.Point(17, 43) },
                zIndex: 999,
            });
            m.addListener("click", () => { this.info.setContent(p.html); this.info.open(this.map, m); });
            this.layer.push(m);
        });
        sites.forEach((s) => {
            this.layer.push(new this.g.Circle({
                map: this.map, center: { lat: s.lat, lng: s.lng }, radius: s.radius,
                strokeColor: "#7c3aed", strokeOpacity: 0.7, strokeWeight: 1, fillColor: "#7c3aed", fillOpacity: 0.08, clickable: false,
            }));
        });
    }
    popupFor(id, html) { const m = this.markers.get(id); if (m) { this.info.setContent(html); this.info.open(this.map, m); } }
    destroy() { this.markers.clear(); }
}

/** Leaflet + OpenStreetMap fallback when no Google key is configured */
export class LeafletAdapter {
    static async load() {
        if (!window.L) {
            await loadCSS(LEAFLET + "leaflet.css");
            await loadJS(LEAFLET + "leaflet.js");
        }
    }
    constructor(el) {
        const L = (this.L = window.L);
        this.map = L.map(el, { zoomControl: true }).setView([23.8103, 90.4125], 11);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 19, attribution: "&copy; OpenStreetMap contributors",
        }).addTo(this.map);
        this.markers = new Map();
        this.layer = L.layerGroup().addTo(this.map);
    }
    _icon(color) {
        return this.L.divIcon({ html: pinHtml(color), className: "", iconSize: [34, 34], iconAnchor: [17, 34] });
    }
    setEmployees(items, onClick) {
        const seen = new Set();
        for (const it of items) {
            seen.add(it.id);
            let m = this.markers.get(it.id);
            if (!m) {
                m = this.L.marker([it.lat, it.lng], { icon: this._icon(it.color), title: it.title }).addTo(this.map);
                m.on("click", () => onClick(it.id));
                this.markers.set(it.id, m);
            } else { m.setLatLng([it.lat, it.lng]); m.setIcon(this._icon(it.color)); }
        }
        for (const [id, m] of this.markers) {
            if (!seen.has(id)) { m.remove(); this.markers.delete(id); }
        }
    }
    fit(points) {
        if (!points.length) return;
        if (points.length === 1) { this.map.setView([points[0].lat, points[0].lng], 16); return; }
        this.map.fitBounds(points.map((p) => [p.lat, p.lng]), { padding: [60, 60] });
    }
    focus(lat, lng) { this.map.setView([lat, lng], Math.max(this.map.getZoom(), 15)); }
    clearOverlay() { this.layer.clearLayers(); }
    drawRoute(points, punches, sites) {
        const L = this.L;
        this.clearOverlay();
        if (points.length) {
            L.polyline(points.map((p) => [p.lat, p.lng]), { color: "#4b1a7a", weight: 4, opacity: 0.85 }).addTo(this.layer);
            points.forEach((p) => {
                const c = p.genuine ? "#0b5fb8" : "#dc2626";
                L.circleMarker([p.lat, p.lng], { radius: 4, color: c, fillColor: c, fillOpacity: 0.9, weight: 1 })
                    .bindPopup(p.html).addTo(this.layer);
            });
        }
        punches.forEach((p) => {
            L.marker([p.lat, p.lng], { icon: this._icon(p.type === "in" ? STATUS_COLOR.in : STATUS_COLOR.out), zIndexOffset: 1000 })
                .bindPopup(p.html).addTo(this.layer);
        });
        sites.forEach((s) => L.circle([s.lat, s.lng], { radius: s.radius, color: "#7c3aed", weight: 1, fillOpacity: 0.08 }).addTo(this.layer));
    }
    popupFor(id, html) { const m = this.markers.get(id); if (m) m.bindPopup(html).openPopup(); }
    destroy() { this.map.remove(); }
}

export async function createMap(el, googleKey) {
    if (googleKey) {
        try {
            await GoogleAdapter.load(googleKey);
            return { adapter: new GoogleAdapter(el), provider: "Google Maps" };
        } catch (e) {
            console.warn("Google Maps failed to load, falling back to OpenStreetMap", e);
        }
    }
    await LeafletAdapter.load();
    return { adapter: new LeafletAdapter(el), provider: "OpenStreetMap" };
}
