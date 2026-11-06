/*
 * LU-Alert dashboard card.
 *
 * Served by the integration (the www folder is available under /lu_alert_static/) and loaded by Home Assistant as an
 * extra module, so no Lovelace resource is needed. Shows the alerts of sensor.lu_alert, with a map of the area.
 *
 *   type: custom:lu-alert-card
 *   entity: sensor.lu_alert                              # optional
 *   feed_entity: binary_sensor.lu_alert_feed_connection  # optional
 *   title: LU-Alert                                      # optional
 *   show_map: true                                       # optional
 */
const BASE = new URL(".", import.meta.url).href;            // the folder of this file: leaflet.js is next to it

const COLORS = {
  extreme: "#b71c1c", severe: "#f44336", moderate: "#ff9800", minor: "#fbc02d", information: "#43a047",
  unknown: "#9e9e9e", test: "#9e9e9e",
};

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
// Everything that comes from the feed goes through this: the text of an alert is never markup.
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]);
const safeUrl = (value) => (/^https?:\/\//i.test(String(value ?? "")) ? String(value) : "");

let leafletPromise = null;
function loadLeaflet() {
  if (window.L) return Promise.resolve(window.L);
  if (!leafletPromise) {
    leafletPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = `${BASE}leaflet.js`;
      script.onload = () => resolve(window.L);
      script.onerror = () => { leafletPromise = null; reject(new Error("leaflet.js could not be loaded")); };
      document.head.appendChild(script);
    });
  }
  return leafletPromise;
}

/** "lat,lon lat,lon ..." -> [[lat, lon], ...] (pairs that are not numbers are skipped) */
function parsePolygon(text) {
  return String(text).trim().split(/\s+/).map((pair) => pair.split(",").map(Number))
    .filter((p) => p.length === 2 && p.every(Number.isFinite));
}

/** "lat,lon radius_km" -> {center, radius} or null */
function parseCircle(text) {
  const [center, radius] = String(text).trim().split(/\s+/);
  const point = String(center ?? "").split(",").map(Number);
  const km = Number(radius);
  return point.length === 2 && point.every(Number.isFinite) && Number.isFinite(km) ? { center: point, radius: km } : null;
}

const hasGeometry = (alert) => (alert.area || []).some((a) => (a.polygons || []).length || (a.circles || []).length);

class LuAlertCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._maps = new Map();           // alert identifier -> Leaflet map
    this._open = new Set();           // identifiers of the alerts that are expanded: kept over re-renders
    this._shown = null;               // what the card shows now, to render only when something changed
  }

  setConfig(config) {
    this._config = { entity: "sensor.lu_alert", feed_entity: "binary_sensor.lu_alert_feed_connection", show_map: true, ...config };
    this.shadowRoot.innerHTML = `
      <link rel="stylesheet" href="${BASE}leaflet.css">
      <style>
        .empty, .notice { display: flex; align-items: center; gap: 8px; padding: 16px; }
        .empty ha-icon { color: var(--success-color, #43a047); }
        .notice { background: var(--warning-color, #ff9800); color: var(--text-primary-color, #fff); padding: 8px 16px; }
        .alerts { padding: 8px 12px 12px; }
        details.alert { border-left: 5px solid var(--sev); border-radius: 4px; margin-top: 8px; padding: 8px 12px;
                        background: var(--secondary-background-color, rgba(127,127,127,.08)); }
        summary { cursor: pointer; display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }
        .headline { font-weight: 600; flex: 1; overflow-wrap: anywhere; }
        .sev { font-size: .8em; color: var(--sev); font-weight: 600; white-space: nowrap; }
        .body { padding-top: 8px; font-size: .95em; line-height: 1.4; }
        .meta { opacity: .75; font-size: .9em; margin-bottom: 6px; }
        .body p { margin: 6px 0; overflow-wrap: anywhere; }
        .tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
        .tag { font-size: .75em; padding: 1px 8px; border-radius: 10px; border: 1px solid var(--divider-color, #888); }
        .map { height: 240px; margin-top: 10px; border-radius: 4px; z-index: 0; }
        a { color: var(--primary-color); }
      </style>
      <ha-card>
        <div class="notice" hidden></div>
        <div class="content"></div>
      </ha-card>`;
    this._card = this.shadowRoot.querySelector("ha-card");
    this._notice = this.shadowRoot.querySelector(".notice");
    this._content = this.shadowRoot.querySelector(".content");
    if (this._config.title) this._card.setAttribute("header", this._config.title);
    // "toggle" does not bubble: listen in the capture phase
    this._content.addEventListener("toggle", (event) => this._toggled(event), true);
    this._shown = null;
    if (this._hass) this._update();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._content) this._update();
  }

  getCardSize() {
    return 1 + Math.min(this._count || 0, 5) * 2;
  }

  static getStubConfig() {
    return { entity: "sensor.lu_alert" };
  }

  // -- rendering ------------------------------------------------------------------------------------------
  _update() {
    const state = this._hass.states[this._config.entity];
    const feed = this._config.feed_entity ? this._hass.states[this._config.feed_entity] : undefined;
    // Home Assistant calls this on every state change of every entity: the state objects only change when this
    // entity changes, so the card is drawn again only then.
    if (this._shown && this._shown.state === state && this._shown.feed === feed) return;
    this._shown = { state, feed };

    const feedDown = feed && feed.state === "off";
    this._notice.hidden = !feedDown;
    this._notice.textContent = feedDown ? "The LU-Alert feed cannot be reached: these are the last known alerts." : "";

    this._destroyMaps();
    if (!state) {
      this._count = 0;
      this._content.innerHTML = `<div class="empty">Entity not found: ${esc(this._config.entity)}</div>`;
    } else if (state.state === "unavailable" || state.state === "unknown") {
      this._count = 0;
      this._content.innerHTML = `<div class="empty">LU-Alert is ${esc(state.state)}.</div>`;
    } else {
      const alerts = Array.isArray(state.attributes.alerts) ? state.attributes.alerts : [];
      this._alerts = alerts;
      this._count = alerts.length;
      this._content.innerHTML = alerts.length
        ? `<div class="alerts">${alerts.map((a, i) => this._renderAlert(a, i)).join("")}</div>`
        : `<div class="empty"><ha-icon icon="mdi:shield-check"></ha-icon><span>No active alerts.</span></div>`;
      // an alert that was expanded stays expanded
      this._content.querySelectorAll("details.alert").forEach((el) => {
        if (this._open.has(el.dataset.id)) { el.open = true; }
      });
    }
  }

  _time(iso) {
    if (!iso) return "";
    const moment = new Date(iso);
    if (Number.isNaN(moment.getTime())) return esc(iso);
    try {
      return moment.toLocaleString(this._hass?.locale?.language, { dateStyle: "medium", timeStyle: "short" });
    } catch (_) {
      return moment.toLocaleString();
    }
  }

  _renderAlert(alert, index) {
    const severity = String(alert.severity || "Unknown");
    const color = COLORS[severity.toLowerCase()] || COLORS.unknown;
    const url = safeUrl(alert.web);
    const meta = [alert.event && `Event: ${esc(alert.event)}`, alert.expires && `Until: ${esc(this._time(alert.expires))}`,
      alert.sent && `Sent: ${esc(this._time(alert.sent))}`].filter(Boolean).join(" · ");
    const tags = [...(alert.category || []), alert.is_local === true && "Local", alert.watch_match && "Watchlist",
      alert.allergen_match && "Allergen"].filter(Boolean).map((t) => `<span class="tag">${esc(t)}</span>`).join("");
    return `
      <details class="alert" data-id="${esc(alert.identifier)}" data-index="${index}" style="--sev:${color}">
        <summary><span class="headline">${esc(alert.headline)}</span><span class="sev">${esc(severity)}</span></summary>
        <div class="body">
          ${meta ? `<div class="meta">${meta}</div>` : ""}
          ${alert.description ? `<p>${esc(alert.description)}</p>` : ""}
          ${alert.instruction ? `<p><strong>Instruction:</strong> ${esc(alert.instruction)}</p>` : ""}
          ${(alert.area_desc || []).length ? `<p><strong>Area:</strong> ${esc(alert.area_desc.join(", "))}</p>` : ""}
          ${url ? `<p><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">More information</a></p>` : ""}
          ${tags ? `<div class="tags">${tags}</div>` : ""}
          ${this._config.show_map && hasGeometry(alert) ? `<div class="map"></div>` : ""}
        </div>
      </details>`;
  }

  // -- expanding and the map ------------------------------------------------------------------------------
  _toggled(event) {
    const el = event.target;
    if (!(el instanceof HTMLDetailsElement) || !el.dataset.id) return;
    if (el.open) {
      this._open.add(el.dataset.id);
      this._showMap(el);
    } else {
      this._open.delete(el.dataset.id);
    }
  }

  async _showMap(el) {
    const mapEl = el.querySelector(".map");
    const alert = (this._alerts || [])[Number(el.dataset.index)];
    if (!mapEl || !alert) return;
    const existing = this._maps.get(el.dataset.id);
    if (existing) { existing.invalidateSize(); return; }
    let L;
    try {
      L = await loadLeaflet();
    } catch (_) {
      mapEl.textContent = "The map could not be loaded.";
      return;
    }
    if (!mapEl.isConnected || this._maps.has(el.dataset.id)) return;      // drawn again while the script loaded
    const map = L.map(mapEl, { attributionControl: true });
    this._maps.set(el.dataset.id, map);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
    const style = { color: COLORS[String(alert.severity).toLowerCase()] || COLORS.unknown, weight: 2 };
    // The bounds are worked out from the numbers: a circle can only tell its bounds once it is on a map that has a view.
    const bounds = L.latLngBounds([]);
    const shapes = [];
    for (const area of alert.area || []) {
      for (const text of area.polygons || []) {
        const points = parsePolygon(text);
        if (points.length >= 3) {
          points.forEach((point) => bounds.extend(point));
          shapes.push(L.polygon(points, style));
        }
      }
      for (const text of area.circles || []) {
        const circle = parseCircle(text);
        if (circle) {
          const [lat, lon] = circle.center;
          const dLat = circle.radius / 111.32;
          const dLon = circle.radius / (111.32 * Math.max(0.01, Math.cos((lat * Math.PI) / 180)));
          bounds.extend([lat - dLat, lon - dLon]);
          bounds.extend([lat + dLat, lon + dLon]);
          shapes.push(L.circle(circle.center, { ...style, radius: circle.radius * 1000 }));
        }
      }
    }
    if (shapes.length) {
      map.fitBounds(bounds, { padding: [10, 10], animate: false });
      shapes.forEach((shape) => shape.addTo(map));
    } else {
      map.setView([49.8153, 6.1296], 9);                                  // Luxembourg
    }
    const id = el.dataset.id;
    // the size of the container is known only once the details are open; the map may be gone by then
    setTimeout(() => { if (this._maps.get(id) === map) map.invalidateSize(); }, 50);
  }

  _destroyMaps() {
    for (const map of this._maps.values()) map.remove();
    this._maps.clear();
  }

  disconnectedCallback() {
    this._destroyMaps();
    this._shown = null;                                                    // drawn again when the card comes back
  }
}

if (!customElements.get("lu-alert-card")) customElements.define("lu-alert-card", LuAlertCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "lu-alert-card")) {
  window.customCards.push({
    type: "lu-alert-card",
    name: "LU-Alert Card",
    description: "The alerts of the Luxembourg LU-Alert system, with a map of the area.",
    preview: false,
  });
}
