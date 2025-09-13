class LuAlertCard extends HTMLElement {
  constructor() {
    super();
    this._leafletPromise = null;
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    if (!this.content) {
      this.shadowRoot.innerHTML = `
        <style>
          /* ... all the styles from before ... */
          .no-alerts { display: flex; align-items: center; padding: 16px; }
          .no-alerts ha-icon { margin-right: 8px; color: var(--success-color); }
          .alert-container { padding: 12px; margin-bottom: 8px; border-radius: 4px; border-left-width: 5px; border-left-style: solid; }
          .headline { font-weight: bold; font-size: 1.1em; }
          details { cursor: pointer; }
          .details-summary { display: flex; justify-content: space-between; align-items: center; }
          .details-summary .headline { flex-grow: 1; }
          .details-content { padding-top: 12px; cursor: default; }
          .details { font-size: 0.9em; margin-bottom: 8px; opacity: 0.8; }
          .description { font-size: 1em; line-height: 1.4; }
          .severity-information { border-color: #607d8b; }
          .severity-minor { border-color: #ffc107; }
          .severity-moderate { border-color: #ff9800; }
          .severity-severe { border-color: #f44336; }
          .severity-extreme { border-color: #b71c1c; }
          .severity-unknown, .severity-none { border-color: var(--disabled-text-color); }
          .structured-data { margin-top: 12px; margin-bottom: 12px; }
          .structured-data table { width: 100%; border-collapse: collapse; }
          .structured-data th, .structured-data td { text-align: left; padding: 6px; border-bottom: 1px solid var(--divider-color); }
          .structured-data th { font-weight: bold; width: 30%; }
          .map-container { height: 200px; margin-top: 12px; border-radius: 4px; z-index: 0; }
          .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.6); }
          .modal-content { background-color: var(--card-background-color, #fefefe); margin: 5% auto; padding: 20px; border: 1px solid #888; width: 80%; height: 80%; }
          .modal-map { width: 100%; height: 95%; }
          .close-button { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
          .view-map-btn { margin-left: 10px; }
        </style>
        <ha-card>
          <div class="card-content"></div>
          <div id="map-modal" class="modal">
            <div class="modal-content">
              <span class="close-button">&times;</span>
              <div id="modal-map-container" class="modal-map"></div>
            </div>
          </div>
        </ha-card>
      `;
      this.content = this.shadowRoot.querySelector('.card-content');
      this.modal = this.shadowRoot.querySelector('#map-modal');
      this.modalMapContainer = this.shadowRoot.querySelector('#modal-map-container');
      this.shadowRoot.querySelector('.close-button').onclick = () => this.modal.style.display = 'none';
    }

    const entityId = this.config.entity || 'sensor.lu_alert';
    const state = hass.states[entityId];

    if (!state) {
      this.content.innerHTML = `<div class="no-alerts"><span>Entity not found: ${entityId}</span></div>`;
      return;
    }

    const alerts = state.attributes.alerts || [];

    if (alerts.length === 0) {
      this.content.innerHTML = `<div class="no-alerts"><ha-icon icon="mdi:shield-check"></ha-icon><span>No active alerts.</span></div>`;
    } else {
      this.content.innerHTML = alerts.map(alert => this._renderAlert(alert)).join('');

      this._loadLeaflet().then(() => {
        alerts.forEach(alert => {
          if (alert.area && alert.area.some(a => a.polygon)) {
            const detailsElement = this.shadowRoot.querySelector(`#details-${alert.identifier}`);
            if (detailsElement) {
              detailsElement.ontoggle = () => {
                if (detailsElement.open) {
                  this._initMap(alert, `#map-${alert.identifier}`);
                }
              };
            }

            const viewMapBtn = this.shadowRoot.querySelector(`#view-map-btn-${alert.identifier}`);
            if (viewMapBtn) {
              viewMapBtn.onclick = (e) => {
                e.stopPropagation(); // prevent details from toggling
                this._showMapModal(alert);
              };
            }
          }
        });
      });
    }
  }

  _loadLeaflet() {
    if (!this._leafletPromise) {
        this._leafletPromise = new Promise(resolve => {
            if (window.L) {
                resolve();
                return;
            }
            const leafletCss = document.createElement('link');
            leafletCss.rel = 'stylesheet';
            leafletCss.href = 'https://unpkg.com/leaflet@1.9.3/dist/leaflet.css';
            this.shadowRoot.appendChild(leafletCss);

            const leafletJs = document.createElement('script');
            leafletJs.src = 'https://unpkg.com/leaflet@1.9.3/dist/leaflet.js';
            leafletJs.onload = () => resolve();
            this.shadowRoot.appendChild(leafletJs);
        });
    }
    return this._leafletPromise;
  }

  _initMap(alert, mapSelector) {
    if (!window.L) return;
    const mapElement = this.shadowRoot.querySelector(mapSelector);
    if (!mapElement || mapElement._leaflet_id) {
        if(mapElement && mapElement._leaflet_id) {
             // If map is already initialized, just ensure it's sized correctly
             const map = mapElement._leaflet_map;
             map.invalidateSize();
        }
        return;
    }

    const map = window.L.map(mapElement);
    mapElement._leaflet_map = map; // Store reference to map instance

    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);

    const polygons = alert.area.map(a => a.polygon).filter(p => p).map(pStr => {
      const coords = pStr.split(' ').map(c => c.split(',').map(Number));
      return window.L.polygon(coords);
    });

    if (polygons.length > 0) {
      const featureGroup = window.L.featureGroup(polygons).addTo(map);
      setTimeout(() => map.fitBounds(featureGroup.getBounds()), 100);
    }
  }

  _showMapModal(alert) {
    this.modal.style.display = 'block';
    this.modalMapContainer.innerHTML = ''; // Clear previous map
    const newMapDiv = document.createElement('div');
    newMapDiv.style.height = '100%';
    this.modalMapContainer.appendChild(newMapDiv);

    setTimeout(() => this._initMap(alert, newMapDiv), 50);
  }

  _renderStructuredDataTable(data) {
    if (!data || Object.keys(data).length === 0) return '';
    let tableHtml = '<div class="structured-data"><table>';
    for (const [key, value] of Object.entries(data)) {
      const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      tableHtml += `<tr><th>${formattedKey}</th><td>${value}</td></tr>`;
    }
    tableHtml += '</table></div>';
    return tableHtml;
  }

  _renderAlert(alert) {
    const hasPolygon = alert.area && alert.area.some(a => a.polygon);
    return `
      <details id="details-${alert.identifier}" class="alert-container severity-${alert.severity.toLowerCase()}">
        <summary class="details-summary">
          <div class="headline">${alert.headline}</div>
          ${hasPolygon ? `<button id="view-map-btn-${alert.identifier}" class="view-map-btn">View Map</button>` : ''}
        </summary>
        <div class="details-content">
          <div class="details">
            <strong>Severity:</strong> ${alert.severity} | <strong>Event:</strong> ${alert.event}
          </div>
          ${this._renderStructuredDataTable(alert.structured_description)}
          <div class="description">${alert.description}</div>
          ${hasPolygon ? `<div id="map-${alert.identifier}" class="map-container"></div>` : ''}
        </div>
      </details>
    `;
  }

  setConfig(config) {
    this.config = config;
  }

  getCardSize() {
    return 3;
  }
}

customElements.define('lu-alert-card', LuAlertCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'lu-alert-card',
  name: 'LU-Alert Card',
  description: 'A card to display LU-Alert (Luxembourg) alerts.',
  preview: true,
});
